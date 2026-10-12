#!/usr/bin/env python3
"""Independently compare the M.Sc. Nursing JSON with the source PDF via pdfplumber."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber


HEADER_KEYS = [
    "srno",
    "cet2026rollno",
    "cet2026score",
    "qualexampercentage",
    "dob",
    "candidatename",
    "allottedcategory",
    "allottedcourse",
    "allottedinstitute",
    "remark",
]
FIELD_INDEX = {
    "serialNo": 0,
    "rollNo": 1,
    "cetScore": 2,
    "qualifyingPercent": 3,
    "dateOfBirth": 4,
    "candidateName": 5,
    "category": 6,
    "course": 7,
    "college": 8,
    "remark": 9,
}


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def header_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", clean(value).casefold())


def is_header(row: list[str]) -> bool:
    return [header_key(cell) for cell in row] == HEADER_KEYS


def independent_rows(pdf_path: Path) -> tuple[list[dict[str, object]], dict[int, int]]:
    records: list[dict[str, object]] = []
    page_by_serial: dict[int, int] = {}
    with pdfplumber.open(pdf_path) as document:
        for page_number, page in enumerate(document.pages, start=1):
            matching_tables = [
                table
                for table in page.extract_tables()
                if table and is_header([clean(cell) for cell in table[0]])
            ]
            if len(matching_tables) != 1:
                raise ValueError(
                    f"Page {page_number}: expected one 10-column candidate table; "
                    f"found {len(matching_tables)}."
                )
            for raw_row in matching_tables[0][1:]:
                cells = [clean(cell) for cell in raw_row]
                if not any(cells):
                    continue
                if is_header(cells):
                    continue
                if len(cells) != len(FIELD_INDEX):
                    raise ValueError(
                        f"Page {page_number}: expected 10 cells, found {len(cells)}."
                    )
                if not cells[0].isdigit():
                    raise ValueError(
                        f"Page {page_number}: non-empty table row has no numeric serial."
                    )
                serial = int(cells[0])
                if serial in page_by_serial:
                    raise ValueError(f"Duplicate source serial {serial}.")
                page_by_serial[serial] = page_number
                records.append(
                    {
                        "serialNo": serial,
                        "rollNo": cells[1],
                        "cetScore": cells[2],
                        "qualifyingPercent": cells[3],
                        "dateOfBirth": cells[4],
                        "candidateName": cells[5],
                        "category": cells[6],
                        "course": cells[7],
                        "college": cells[8],
                        "remark": cells[9],
                    }
                )
    return records, page_by_serial


def normalized_value(field: str, value: object) -> object:
    if field == "serialNo":
        return int(value)
    if field == "cetScore":
        return int(Decimal(clean(value)))
    if field == "qualifyingPercent":
        try:
            return Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError("Invalid qualifying percentage in compared data.") from error
    return clean(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("json_data", type=Path)
    args = parser.parse_args()
    data = json.loads(args.json_data.read_text(encoding="utf-8"))
    source_records, page_by_serial = independent_rows(args.pdf)

    source_serials = [int(record["serialNo"]) for record in source_records]
    if source_serials != list(range(1, len(source_serials) + 1)):
        raise ValueError("Independent PDF extraction found missing or out-of-order serials.")
    filtered = [
        record
        for record in source_records
        if "nursing" in clean(record["course"]).casefold()
    ]
    actual_records = data.get("records")
    if not isinstance(actual_records, list):
        raise ValueError("JSON does not contain a records array.")
    if data.get("sourceRecordCount") != len(source_records):
        raise ValueError("JSON sourceRecordCount does not match the independent PDF row count.")
    if len(filtered) != len(actual_records):
        raise ValueError(
            f"Independent filter produced {len(filtered)} records, "
            f"but JSON contains {len(actual_records)}."
        )

    mismatches: list[tuple[int, int, str]] = []
    for source, actual in zip(filtered, actual_records):
        serial = int(source["serialNo"])
        for field in FIELD_INDEX:
            try:
                expected = normalized_value(field, source[field])
                found = normalized_value(field, actual.get(field))
            except (TypeError, ValueError):
                mismatches.append((page_by_serial[serial], serial, field))
                continue
            if expected != found:
                mismatches.append((page_by_serial[serial], serial, field))

    if mismatches:
        examples = ", ".join(
            f"page {page}, serial {serial}, field {field}"
            for page, serial, field in mismatches[:20]
        )
        raise ValueError(
            f"{len(mismatches)} PDF/JSON field mismatches (values omitted): {examples}"
        )

    print(
        f"PASS: independent pdfplumber extraction found {len(source_records)} source rows "
        f"with continuous serials and matched all {len(actual_records)} selected records "
        f"across all 10 fields."
    )
    print("DOB and qualifying-exam percentage were included in the comparison.")


if __name__ == "__main__":
    main()
