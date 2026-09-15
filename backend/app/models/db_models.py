from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cet_group: Mapped[str] = mapped_column(String(20))
    cet_exam: Mapped[str] = mapped_column(String(40), index=True)
    academic_year: Mapped[str] = mapped_column(String(4), default="2026")
    version: Mapped[str] = mapped_column(String(80), default="2026-unpublished")
    source_type: Mapped[str] = mapped_column(String(20), default="MARKDOWN")
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    ranking_algorithm_version: Mapped[str] = mapped_column(String(80), default="v1-UNVERIFIED-placeholder")
    validation_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    roll_number: Mapped[str] = mapped_column(String(40))
    normalized_roll_number: Mapped[str] = mapped_column(String(40))
    cet_exam: Mapped[str] = mapped_column(String(40))
    cet_group: Mapped[str] = mapped_column(String(20))
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cet_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    dob_raw: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    course: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extra_fields_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    merit_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tie_break_used: Mapped[str | None] = mapped_column(String(80), nullable=True)

    __table_args__ = (
        Index("ix_candidates_dataset_roll", "dataset_id", "normalized_roll_number"),
    )