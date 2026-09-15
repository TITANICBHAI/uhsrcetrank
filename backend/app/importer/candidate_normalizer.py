from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from dateutil import parser as date_parser


NULL_VALUES = {"", "-", "--", "—", "n/a", "na", "null", "nil", "not available"}


@dataclass
class CandidateRecord:
    roll_number: str
    normalized_roll_number: str
    source_row_number: int
    cet_exam: str
    cet_group: str
    name: str | None = None
    cet_score: float | None = None
    percentile: float | None = None
    dob_raw: str | None = None
    dob: date | None = None
    category: str | None = None
    published_order: int | None = None
    extra_fields: dict[str, str] | None = None
    merit_position: int | None = None
    tie_break_used: str | None = None

    def fingerprint(self) -> str:
        values = {
            key: value
            for key, value in self.__dict__.items()
            if key != "source_row_number"
        }
        return json.dumps(values, default=str, sort_keys=True)


def clean(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).replace("\u200b", "").strip()
    return re.sub(r"\s+", " ", text)


def normalize_roll_number(value: object) -> str:
    return clean(value).upper()


def _is_null(value: str | None) -> bool:
    return value is None or clean(value).lower() in NULL_VALUES


def _simplify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _find(row: dict[str, str], names: set[str]) -> str | None:
    for header, value in row.items():
        simplified = _simplify(header)
        if simplified in names or any(name in simplified for name in names):
            return value
    return None


def _number(value: str | None) -> float | None:
    if _is_null(value):
        return None
    try:
        return float(Decimal(clean(value).replace("%", "").replace(",", "")))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid numeric value: {value}")


def _integer(value: str | None) -> int | None:
    number = _number(value)
    if number is None:
        return None
    if int(number) != number:
        raise ValueError(f"Expected a whole-number order, found: {value}")
    return int(number)


def _date(value: str | None) -> tuple[str | None, date | None]:
    if _is_null(value):
        return None, None
    raw = clean(value)
    try:
        return raw, date_parser.parse(raw, dayfirst=True, fuzzy=False).date()
    except (ValueError, OverflowError):
        return raw, None


class CandidateNormalizer:
    """Map common published result columns to the stored candidate shape."""

    def normalize_row(self, row: dict, cet_exam: str, cet_group: str, source_row_number: int = 0) -> CandidateRecord:
        roll = _find(row, {"roll number", "roll no", "roll", "registration number", "registration no"})
        normalized = normalize_roll_number(roll)
        if not normalized or not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{0,39}", normalized):
            raise ValueError("Missing or invalid roll number")
        dob_raw, dob = _date(_find(row, {"dob", "date of birth", "birth date"}))
        known = {
            "roll number", "roll no", "roll", "registration number", "registration no",
            "name", "candidate name", "student name", "score", "cet score", "marks",
            "percentile", "percentile score", "dob", "date of birth", "birth date",
            "category", "rank", "position", "merit position", "serial no", "serial number",
            "sr no", "s no", "sr no",
        }
        extras = {
            key: clean(value)
            for key, value in row.items()
            if _simplify(key) not in known and clean(value)
        }
        return CandidateRecord(
            roll_number=clean(roll),
            normalized_roll_number=normalized,
            source_row_number=source_row_number,
            cet_exam=cet_exam,
            cet_group=cet_group,
            name=clean(_find(row, {"name", "candidate name", "student name"})) or None,
            cet_score=_number(_find(row, {"cet score", "score", "marks"})),
            percentile=_number(_find(row, {"percentile", "percentile score"})),
            dob_raw=dob_raw,
            dob=dob,
            category=clean(_find(row, {"category"})) or None,
            published_order=_integer(_find(row, {"rank", "position", "merit position", "serial no", "serial number", "sr no", "s no"})),
            extra_fields=extras,
        )