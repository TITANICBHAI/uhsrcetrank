from __future__ import annotations

import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.importer.markdown_importer import MarkdownImporter
from app.models.db_models import Candidate, Dataset
from app.models.schemas import DatasetOut
from app.ranking.ranking_config import PLACEHOLDER_CONFIG, RankingConfig, RankingCriterion
from app.ranking.ranking_engine import RankingEngine

router = APIRouter()
KNOWN_EXAMS = {
    "bsc-nursing": "UG",
    "bpt": "UG",
    "paramedical": "UG",
    "pb-bsc-nursing": "OTHER",
    "msc-nursing": "OTHER",
    "mpt": "OTHER",
    "npcc": "OTHER",
}


async def require_admin(
    x_admin_secret: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail={"error": "Unauthorized", "code": "UNAUTHORIZED"})


def no_store(response: JSONResponse) -> JSONResponse:
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/datasets", response_model=list[DatasetOut], dependencies=[Depends(require_admin)])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).order_by(Dataset.imported_at.desc()))
    content = [DatasetOut.model_validate(item).model_dump(mode="json") for item in result.scalars()]
    return no_store(JSONResponse(content=content))


@router.post("/datasets/import", dependencies=[Depends(require_admin)])
async def import_dataset(
    cet_exam: str = Form(...),
    markdown_file: UploadFile = File(...),
    notes: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if cet_exam not in KNOWN_EXAMS:
        raise HTTPException(status_code=400, detail={"error": "Unknown CET examination", "code": "INVALID_EXAM"})
    if not markdown_file.filename or not markdown_file.filename.lower().endswith((".md", ".markdown")):
        raise HTTPException(status_code=415, detail={"error": "Markdown file required", "code": "INVALID_FILE_TYPE"})
    content = await markdown_file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail={"error": "File is too large", "code": "FILE_TOO_LARGE"})
    try:
        markdown = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail={"error": "File must be UTF-8 Markdown", "code": "INVALID_ENCODING"})

    importer = MarkdownImporter(cet_exam, KNOWN_EXAMS[cet_exam])
    imported = importer.import_markdown(markdown)
    ranking_config = PLACEHOLDER_CONFIG
    if imported.candidates and all(item.published_order is not None for item in imported.candidates):
        ranking_config = RankingConfig(
            criteria=[RankingCriterion.PUBLISHED_ORDER],
            version=settings.ranking_algorithm_version,
            position_policy="sequential",
        )
    ranking = RankingEngine(ranking_config).rank(imported.candidates)
    ranked_by_roll = {
        str(getattr(item.candidate, "normalized_roll_number")): item
        for item in ranking.ranked_candidates
    }
    for candidate in imported.candidates:
        result = ranked_by_roll[candidate.normalized_roll_number]
        if result.merit_position is None:
            imported.report.setdefault("warnings", []).append({
                "source_row": candidate.source_row_number,
                "reason": "Unresolved tie; no merit position generated",
            })
        candidate.merit_position = result.merit_position
        candidate.tie_break_used = result.tie_break_used
    imported.report["ranking"] = {
        "version": ranking.config_version,
        "criteria": [criterion.value for criterion in ranking_config.criteria],
        "unresolved_ties": ranking.unresolved_ties,
        "disclaimer": ranking.ranking_disclaimer,
    }

    dataset = Dataset(
        cet_group=KNOWN_EXAMS[cet_exam],
        cet_exam=cet_exam,
        version=f"2026-{cet_exam}-unpublished",
        source_type="MARKDOWN",
        source_sha256=hashlib.sha256(content).hexdigest(),
        candidate_count=len(imported.candidates),
        ranking_algorithm_version=ranking_config.version,
        validation_report=json.dumps(imported.report, default=str),
        notes=notes.strip() or f"Uploaded source: {markdown_file.filename}",
    )
    db.add(dataset)
    await db.flush()
    db.add_all([
        Candidate(
            dataset_id=dataset.id,
            roll_number=item.roll_number,
            normalized_roll_number=item.normalized_roll_number,
            cet_exam=item.cet_exam,
            cet_group=item.cet_group,
            source_row_number=item.source_row_number,
            published_order=item.published_order,
            name=item.name,
            cet_score=item.cet_score,
            percentile=item.percentile,
            dob_raw=item.dob_raw,
            dob=item.dob,
            category=item.category,
            extra_fields_json=json.dumps(item.extra_fields or {}),
            merit_position=item.merit_position,
            tie_break_used=item.tie_break_used,
        )
        for item in imported.candidates
    ])
    await db.commit()
    await db.refresh(dataset)
    response = {
        "id": dataset.id,
        "status": "unpublished",
        "candidate_count": dataset.candidate_count,
        "validation": imported.report,
    }
    return no_store(JSONResponse(content=response))


@router.get("/datasets/{dataset_id}/validation", dependencies=[Depends(require_admin)])
async def validation(dataset_id: int, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail={"error": "Dataset not found", "code": "NOT_FOUND"})
    payload = json.loads(dataset.validation_report or "{}")
    return no_store(JSONResponse(content=payload))


@router.post("/datasets/{dataset_id}/publish", dependencies=[Depends(require_admin)])
async def publish(dataset_id: int, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail={"error": "Dataset not found", "code": "NOT_FOUND"})
    report = json.loads(dataset.validation_report or "{}")
    if report.get("is_passed") is not True:
        raise HTTPException(
            status_code=422,
            detail={"error": "Validation must pass before publication", "code": "VALIDATION_REQUIRED"},
        )
    try:
        await db.execute(
            Dataset.__table__.update()
            .where(Dataset.cet_exam == dataset.cet_exam, Dataset.id != dataset.id)
            .values(is_published=False, published_at=None)
        )
        dataset.is_published = True
        dataset.published_at = datetime.utcnow()
        dataset.version = f"2026-{dataset.cet_exam}-v{dataset.id}"
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return no_store(JSONResponse(content={"status": "published", "id": dataset.id}))


@router.post("/datasets/{dataset_id}/unpublish", dependencies=[Depends(require_admin)])
async def unpublish(dataset_id: int, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail={"error": "Dataset not found", "code": "NOT_FOUND"})
    dataset.is_published = False
    dataset.published_at = None
    await db.commit()
    return no_store(JSONResponse(content={"status": "unpublished", "id": dataset_id}))


@router.delete("/datasets/{dataset_id}", dependencies=[Depends(require_admin)])
async def delete_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail={"error": "Dataset not found", "code": "NOT_FOUND"})
    if dataset.is_published:
        raise HTTPException(status_code=422, detail={"error": "Published datasets cannot be deleted", "code": "PUBLISHED_DATASET"})
    await db.execute(delete(Candidate).where(Candidate.dataset_id == dataset.id))
    await db.delete(dataset)
    await db.commit()
    return no_store(JSONResponse(content={"status": "deleted", "id": dataset_id}))