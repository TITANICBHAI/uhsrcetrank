#!/usr/bin/env python3
"""Independently compare the M.Sc. Nursing Round 2 JSON with the source PDF."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path

import pdfplumber


FIELDS = (
    "serialNo",
    "rollNo",
    "cetScore",
    "qualifyingPercent",
    "dateOfBirth",
    "candidateName",
    "previousInstitute",
    "previousCourse",
    "previousCategory",
    "previousRemark",
    "allottedInstitute",
    "allottedCourse",
    "allottedCategory",
    "remark",
)
HEADER_KEYS = (
    "srno",
    "cet2026rollno",
    "cet2026score",
    "qualexampercentage",
    "dob",
    "candidatename",
    "allottedinstitutepreviousround",
    "allottedcoursepreviousround",
    "allottedcatprevround",
    "remarkprevround",
    "allottedinstituteround2",
    "allottedcourse",
    "allottedcategory",
    "remark",
)


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def header_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", clean(value).casefold())


def is_header(row: list[object]) -> bool:
    return tuple(header_key(cell) for cell in row) == HEADER_KEYS


def independent_source_rows(pdf_path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with pdfplumber.open(pdf_path) as document:
        for page_number, page in enumerate(document.pages, start=1):
            matching_tables = [
                table
                for table in page.extract_tables()
                if table and is_header(table[0])
            ]
            if len(matching_tables) != 1:
                raise ValueError(
                    f"Page {page_number}: expected one 14-column candidate table; "
                    f"found {len(matching_tables)}."
                )

            for raw_row in matching_tables[0][1:]:
                cells = [clean(cell) for cell in raw_row]
                if not any(cells):
                    continue
                if is_header(cells):
                    continue
                if len(cells) != len(FIELDS):
                    raise ValueError(
                        f"Page {page_number}: expected {len(FIELDS)} cells, "
                        f"found {len(cells)}."
                    )
                if not cells[0].isdigit():
                    raise ValueError(
                        f"Page {page_number}: non-empty row has no numeric serial."
                    )
                records.append(dict(zip(FIELDS, cells, strict=True)))
    return records


def normalized(field: str, value: object) -> object:
    if field in ("serialNo", "cetScore"):
        return int(Decimal(clean(value)))
    if field == "qualifyingPercent":
        return Decimal(clean(value))
    return clean(value)


def verify(pdf_path: Path, json_path: Path) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    source_records = independent_source_rows(pdf_path)
    source_serials = [int(record["serialNo"]) for record in source_records]
    if source_serials != list(range(1, len(source_records) + 1)):
        raise ValueError("Independent PDF extraction found missing or out-of-order serials.")
    if data.get("sourceRecordCount") != len(source_records):
        raise ValueError("JSON sourceRecordCount does not match independent PDF extraction.")
    if data.get("course") != "M.Sc. Nursing" or int(data.get("round", 0)) != 2:
        raise ValueError("JSON metadata does not identify M.Sc. Nursing Round 2.")

    selected = [
        record
        for record in source_records
        if "nursing" in clean(record["allottedCourse"]).casefold()
    ]
    actual_records = data.get("records")
    if not isinstance(actual_records, list) or len(actual_records) != len(selected):
        raise ValueError(
            f"Final-course filter produced {len(selected)} records, but JSON contains "
            f"{len(actual_records) if isinstance(actual_records, list) else 'no records'}."
        )

    mismatches: list[tuple[int, str]] = []
    for source, actual in zip(selected, actual_records, strict=True):
        serial = int(source["serialNo"])
        for field in FIELDS:
            try:
                expected = normalized(field, source[field])
                found = normalized(field, actual.get(field))
            except (TypeError, ValueError, ArithmeticError):
                mismatches.append((serial, field))
                continue
            if expected != found:
                mismatches.append((serial, field))

    if mismatches:
        examples = ", ".join(
            f"serial {serial}, field {field}" for serial, field in mismatches[:20]
        )
        raise ValueError(
            f"{len(mismatches)} source/JSON field mismatches (values omitted): {examples}"
        )

    print(
        f"PASS: independent pdfplumber extraction found {len(source_records)} source rows "
        f"with continuous serials and matched all {len(selected)} selected records "
        f"across all {len(FIELDS)} fields."
    )
    print("DOB and qualifying-exam percentage were included in the comparison.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Source Round 2 PDF")
    parser.add_argument("json_data", type=Path, help="Generated Round 2 JSON")
    args = parser.parse_args()
    verify(args.pdf, args.json_data)


if __name__ == "__main__":
    main()
