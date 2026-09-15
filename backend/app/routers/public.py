from datetime import datetime
import re

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.db_models import Candidate, Dataset
from app.models.schemas import (
    AboveCandidateOut,
    ActiveDatasetOut,
    CandidateOut,
    CandidateWindowResult,
    NearbyCandidateOut,
    RankedCandidateOut,
    SearchResult,
)
from app.pdf_report import build_report

router = APIRouter()
KNOWN_EXAMS = {
    "bsc-nursing": ("B.Sc Nursing", "UG"),
    "bpt": ("BPT", "UG"),
    "paramedical": ("Paramedical", "UG"),
    "pb-bsc-nursing": ("Post Basic B.Sc Nursing", "OTHER"),
    "msc-nursing": ("M.Sc Nursing", "OTHER"),
    "mpt": ("MPT", "OTHER"),
    "npcc": ("NPCC", "OTHER"),
}
NOT_FOUND_MESSAGE = (
    "No candidate was found with this Roll Number in the selected CET 2026 dataset. "
    "Check the Roll Number and selected examination."
)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/datasets/active", response_model=list[ActiveDatasetOut])
async def active_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Dataset).where(Dataset.is_published.is_(True)).order_by(Dataset.cet_exam)
    )
    return [
        ActiveDatasetOut(
            cet_exam=item.cet_exam,
            label=KNOWN_EXAMS.get(item.cet_exam, (item.cet_exam, ""))[0],
            academic_year=item.academic_year,
            dataset_version=item.version,
        )
        for item in result.scalars()
    ]


def _valid_roll(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9-]{1,40}", value.strip()))


async def lookup(roll_no: str, cet_exam: str, db: AsyncSession) -> SearchResult:
    normalized_roll = roll_no.strip().upper()
    if not _valid_roll(normalized_roll):
        return SearchResult(status="invalid", message="Please enter a valid Roll Number.")
    if cet_exam not in KNOWN_EXAMS:
        return SearchResult(status="invalid", message="Select a recognized CET examination.")

    dataset_result = await db.execute(
        select(Dataset).where(Dataset.cet_exam == cet_exam, Dataset.is_published.is_(True))
    )
    dataset = dataset_result.scalar_one_or_none()
    if dataset is None:
        return SearchResult(
            status="unavailable",
            message="Result data for this CET examination has not been processed and published yet.",
        )

    candidate_result = await db.execute(
        select(Candidate).where(
            Candidate.dataset_id == dataset.id,
            Candidate.normalized_roll_number == normalized_roll,
        )
    )
    candidate = candidate_result.scalar_one_or_none()
    if candidate is None:
        return SearchResult(status="not_found", message=NOT_FOUND_MESSAGE)
    if candidate.merit_position is None:
        return SearchResult(
            status="error",
            message="This record was found, but a reliable estimated merit position could not be generated from the available data. No position has been invented.",
        )

    disclaimer = None
    if "UNVERIFIED" in dataset.ranking_algorithm_version:
        disclaimer = (
            "This estimated merit position uses a configured calculation that has not been "
            "verified against the complete published UHSR CET 2026 ordering. Do not treat it "
            "as an official UHSR rank."
        )
    ranking_method = (
        "Published source order"
        if candidate.published_order is not None
        else "Configured percentile, score, and date criteria"
    )
    data = RankedCandidateOut(
        candidate=CandidateOut.model_validate(candidate),
        merit_position=candidate.merit_position,
        total_candidates=dataset.candidate_count,
        candidates_ahead=max(candidate.merit_position - 1, 0),
        tie_break_used=candidate.tie_break_used,
        dataset_version=dataset.version,
        ranking_method=ranking_method,
        criteria=["Published source order"] if candidate.published_order is not None else [
            "Percentile descending when available",
            "CET score descending when available",
            "Date of birth ascending when available",
        ],
        ranking_disclaimer=disclaimer,
        calculated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
    return SearchResult(status="found", data=data)


def _abbreviated_name(name: str | None) -> str | None:
    if not name:
        return None
    parts = name.strip().split()
    if len(parts) == 1:
        return f"{parts[0][:1]}."
    return f"{parts[0][:1]}. {parts[-1][:1]}."


def _public_candidate(candidate: Candidate, position: int, is_self: bool = False) -> dict:
    return {
        "position": position,
        "roll_number": candidate.roll_number,
        "name": candidate.name if is_self else _abbreviated_name(candidate.name),
        "cet_score": candidate.cet_score,
        "percentile": candidate.percentile,
        "is_self": is_self,
    }


async def _published_dataset(cet_exam: str, db: AsyncSession) -> Dataset | None:
    result = await db.execute(
        select(Dataset)
        .where(Dataset.cet_exam == cet_exam, Dataset.is_published.is_(True))
        .order_by(Dataset.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/candidates/nearby", response_model=CandidateWindowResult)
async def nearby_candidates(
    cet_exam: str = Query(...),
    position: int = Query(..., ge=1),
    window: int = Query(default=5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    if cet_exam not in KNOWN_EXAMS:
        return JSONResponse(
            status_code=400,
            content=CandidateWindowResult(status="invalid", message="Select a recognized CET examination.").model_dump(mode="json"),
        )
    dataset = await _published_dataset(cet_exam, db)
    if dataset is None:
        return CandidateWindowResult(status="unavailable", position=position, items=[])
    result = await db.execute(
        select(Candidate)
        .where(
            Candidate.dataset_id == dataset.id,
            Candidate.merit_position.between(max(1, position - window), position + window),
        )
        .order_by(Candidate.merit_position.asc())
        .limit(21)
    )
    items = [
        NearbyCandidateOut(**_public_candidate(item, item.merit_position or 0, (item.merit_position or 0) == position))
        for item in result.scalars()
        if item.merit_position is not None
    ]
    return CandidateWindowResult(status="ok", position=position, items=items)


@router.get("/candidates/above", response_model=CandidateWindowResult)
async def candidates_above(
    cet_exam: str = Query(...),
    position: int = Query(..., ge=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    if cet_exam not in KNOWN_EXAMS:
        return JSONResponse(
            status_code=400,
            content=CandidateWindowResult(status="invalid", message="Select a recognized CET examination.").model_dump(mode="json"),
        )
    dataset = await _published_dataset(cet_exam, db)
    if dataset is None:
        return CandidateWindowResult(status="unavailable", position=position, items=[], page=page, page_size=limit)
    offset = (page - 1) * limit
    rows = await db.execute(
        select(Candidate)
        .where(Candidate.dataset_id == dataset.id, Candidate.merit_position < position)
        .order_by(Candidate.merit_position.desc())
        .limit(limit)
        .offset(offset)
    )
    count_result = await db.execute(
        select(func.count(Candidate.id)).where(
            Candidate.dataset_id == dataset.id,
            Candidate.merit_position < position,
        )
    )
    total = count_result.scalar_one()
    items = [
        AboveCandidateOut(**_public_candidate(item, item.merit_position or 0))
        for item in rows.scalars()
        if item.merit_position is not None
    ]
    return CandidateWindowResult(
        status="ok",
        position=position,
        page=page,
        page_size=limit,
        total_above=total,
        has_more=offset + len(items) < total,
        items=items,
    )


@router.get("/search", response_model=SearchResult)
async def search(
    roll_no: str = Query(..., min_length=1, max_length=40),
    cet_exam: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await lookup(roll_no, cet_exam, db)
    if result.status == "invalid":
        return JSONResponse(status_code=400, content=result.model_dump(mode="json"))
    response = JSONResponse(content=result.model_dump(mode="json"))
    if result.status == "found":
        response.headers["Cache-Control"] = "public, max-age=3600"
    else:
        response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/report")
async def report(roll_no: str, cet_exam: str, db: AsyncSession = Depends(get_db)):
    result = await lookup(roll_no, cet_exam, db)
    if result.status != "found" or not result.data:
        status_code = 400 if result.status == "invalid" else 404
        return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))
    content = build_report(result.model_dump(mode="json"), get_settings().official_url)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="uhsr-cet-estimated-merit-position.pdf"',
            "Cache-Control": "no-store",
        },
    )