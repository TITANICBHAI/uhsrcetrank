from datetime import datetime
import io
import re

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.db_models import Candidate, Dataset
from app.models.schemas import DatasetOut, RankedCandidateOut, SearchResult

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


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/datasets/active", response_model=list[DatasetOut])
async def active_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Dataset).where(Dataset.is_published.is_(True)).order_by(Dataset.cet_exam)
    )
    return result.scalars().all()


def invalid_roll(roll_no: str) -> bool:
    return not bool(re.fullmatch(r"[A-Za-z0-9-]{1,40}", roll_no.strip()))


@router.get("/search", response_model=SearchResult)
async def search(
    roll_no: str = Query(..., min_length=1, max_length=40),
    cet_exam: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    normalized_roll = roll_no.strip().upper()
    if invalid_roll(normalized_roll):
        return JSONResponse(
            status_code=400,
            content={"status": "invalid", "message": "Please enter a valid Roll Number."},
        )
    if cet_exam not in KNOWN_EXAMS:
        return JSONResponse(
            status_code=400,
            content={"status": "invalid", "message": "Select a recognized CET examination."},
        )
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
        return SearchResult(
            status="not_found",
            message="No candidate was found with this Roll Number in the selected CET 2026 dataset. Check the Roll Number and selected examination.",
        )
    position = candidate.merit_position
    if position is None:
        return SearchResult(
            status="error",
            message="This record was found, but a reliable estimated merit position could not be generated from the available data.",
        )
    settings = get_settings()
    disclaimer = None
    if "UNVERIFIED" in dataset.ranking_algorithm_version:
        disclaimer = "This estimated merit position uses a configured calculation that has not been verified against the complete published UHSR CET 2026 ordering. Do not treat it as an official UHSR rank."
    data = RankedCandidateOut(
        candidate=candidate,
        merit_position=position,
        total_candidates=dataset.candidate_count,
        candidates_ahead=max(position - 1, 0),
        tie_break_used=candidate.tie_break_used,
        dataset_version=dataset.version,
        ranking_method="Published source order or configured dataset method",
        criteria=["Dataset-specific ranking configuration"],
        ranking_disclaimer=disclaimer,
        calculated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )
    response = JSONResponse(content=SearchResult(status="found", data=data).model_dump(mode="json"))
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@router.get("/report")
async def report(roll_no: str, cet_exam: str, db: AsyncSession = Depends(get_db)):
    """Small skeleton endpoint; report generation stays disabled until a dataset is published."""
    found = await search(roll_no=roll_no, cet_exam=cet_exam, db=db)
    if isinstance(found, SearchResult) and found.status != "found":
        return JSONResponse(status_code=404, content=found.model_dump())
    return Response(
        content=io.BytesIO(b"UNOFFICIAL - ESTIMATED MERIT POSITION\n").getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="uhsr-cet-report.pdf"'},
    )