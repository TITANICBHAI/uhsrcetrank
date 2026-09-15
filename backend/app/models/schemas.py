from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    roll_number: str
    name: str | None = None
    cet_score: float | None = None
    percentile: float | None = None
    dob: date | None = None
    category: str | None = None
    cet_exam: str


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cet_exam: str
    academic_year: str
    version: str
    candidate_count: int
    is_published: bool


class ActiveDatasetOut(BaseModel):
    cet_exam: str
    label: str
    academic_year: str
    dataset_version: str


class RankedCandidateOut(BaseModel):
    candidate: CandidateOut
    merit_position: int
    total_candidates: int
    candidates_ahead: int
    tie_break_used: str | None = None
    dataset_version: str
    ranking_method: str
    criteria: list[str] = []
    ranking_disclaimer: str | None = None
    calculated_at: str


class SearchResult(BaseModel):
    status: Literal["found", "not_found", "unavailable", "ambiguous", "invalid", "error"]
    data: RankedCandidateOut | None = None
    message: str | None = None