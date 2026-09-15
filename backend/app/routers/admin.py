import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models.db_models import Dataset
from app.models.schemas import DatasetOut

router = APIRouter()


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
    response = JSONResponse(content=[DatasetOut.model_validate(item).model_dump(mode="json") for item in result.scalars()])
    return no_store(response)


@router.post("/datasets/import", dependencies=[Depends(require_admin)])
async def import_dataset(
    cet_exam: str = Query(...),
    markdown_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not markdown_file.filename or not markdown_file.filename.lower().endswith((".md", ".markdown")):
        raise HTTPException(status_code=415, detail={"error": "Markdown file required", "code": "INVALID_FILE_TYPE"})
    content = await markdown_file.read(2_000_001)
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail={"error": "File is too large", "code": "FILE_TOO_LARGE"})
    dataset = Dataset(
        cet_group="UG" if cet_exam in {"bsc-nursing", "bpt", "paramedical"} else "OTHER",
        cet_exam=cet_exam,
        version="2026-unpublished",
        candidate_count=0,
        validation_report=json.dumps({
            "is_passed": False,
            "status": "SKELETON",
            "message": "Importer and human review are required before publication.",
        }),
        notes=f"Uploaded source: {markdown_file.filename}",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    response = JSONResponse(content={"id": dataset.id, "status": "unpublished", "bytes_received": len(content)})
    return no_store(response)


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
        raise HTTPException(status_code=422, detail={"error": "Validation must pass before publication", "code": "VALIDATION_REQUIRED"})
    await db.execute(
        Dataset.__table__.update().where(Dataset.cet_exam == dataset.cet_exam).values(is_published=False)
    )
    dataset.is_published = True
    dataset.published_at = datetime.utcnow()
    await db.commit()
    return no_store(JSONResponse(content={"status": "published", "id": dataset.id}))


@router.post("/datasets/{dataset_id}/unpublish", dependencies=[Depends(require_admin)])
async def unpublish(dataset_id: int, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail={"error": "Dataset not found", "code": "NOT_FOUND"})
    dataset.is_published = False
    dataset.published_at = None
    await db.commit()
    return no_store(JSONResponse(content={"status": "unpublished", "id": dataset.id}))


@router.delete("/datasets/{dataset_id}", dependencies=[Depends(require_admin)])
async def delete_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail={"error": "Dataset not found", "code": "NOT_FOUND"})
    if dataset.is_published:
        raise HTTPException(status_code=422, detail={"error": "Published datasets cannot be deleted", "code": "PUBLISHED_DATASET"})
    await db.delete(dataset)
    await db.commit()
    return no_store(JSONResponse(content={"status": "deleted", "id": dataset_id}))