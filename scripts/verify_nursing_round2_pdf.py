#!/usr/bin/env python3
"""Independently compare the Round 2 Nursing JSON with the source PDF tables."""

from __future__ import annotations

import argparse
import json
import re
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
NURSING_COURSE = "B.Sc. Nursing"


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def extract_pdf_records(pdf_path: Path) -> list[dict]:
    """Read tables independently from the production PyMuPDF cell-geometry parser."""
    records = []
    with pdfplumber.open(pdf_path) as document:
        for page_number, page in enumerate(document.pages, start=1):
            tables = page.extract_tables()
            if len(tables) != 1:
                raise ValueError(
                    f"Page {page_number}: expected one ruled table, found {len(tables)}."
                )
            for row in tables[0]:
                if not row:
                    continue
                serial_text = normalize(row[0])
                if not serial_text.isdigit():
                    if not serial_text or serial_text.startswith("Sr."):
                        continue
                    raise ValueError(
                        f"Page {page_number}: unexpected non-serial table row "
                        f"{serial_text!r}."
                    )
                if len(row) != len(FIELDS):
                    raise ValueError(
                        f"Page {page_number}, serial {serial_text}: "
                        f"expected {len(FIELDS)} columns, found {len(row)}."
                    )

                record = {
                    field: normalize(row[index])
                    for index, field in enumerate(FIELDS)
                }
                record["serialNo"] = int(record["serialNo"])
                if not record["cetScore"].isdigit():
                    raise ValueError(
                        f"Page {page_number}, serial {serial_text}: "
                        f"invalid CET score {record['cetScore']!r}."
                    )
                record["cetScore"] = int(record["cetScore"])
                records.append(record)
    return records


def verify(pdf_path: Path, json_path: Path) -> None:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    pdf_records = extract_pdf_records(pdf_path)
    source_count = int(payload["sourceRecordCount"])
    serials = [record["serialNo"] for record in pdf_records]
    if len(pdf_records) != source_count or serials != list(range(1, source_count + 1)):
        raise ValueError(
            f"PDF source rows/serials do not match metadata: "
            f"{len(pdf_records)} rows, expected {source_count} contiguous serials."
        )

    expected_records = payload["records"]
    nursing_records = [
        record for record in pdf_records
        if record["allottedCourse"].casefold() == NURSING_COURSE.casefold()
    ]
    if len(nursing_records) != len(expected_records):
        raise ValueError(
            f"Filtered record count mismatch: PDF={len(nursing_records)}, "
            f"JSON={len(expected_records)}."
        )

    for pdf_record, json_record in zip(nursing_records, expected_records, strict=True):
        for field in FIELDS:
            expected = pdf_record[field]
            actual = json_record[field]
            if field in ("serialNo", "cetScore"):
                actual = int(actual)
            else:
                actual = normalize(actual)
            if expected != actual:
                raise ValueError(
                    f"Mismatch at source serial {pdf_record['serialNo']}, "
                    f"field {field}: PDF={expected!r}, JSON={actual!r}."
                )

    college_count = len({record["allottedInstitute"] for record in nursing_records})
    print(
        f"PASS: {source_count} PDF rows have contiguous serials; "
        f"all {len(nursing_records)} B.Sc. Nursing records match all "
        f"{len(FIELDS)} fields across {college_count} colleges."
    )
    print("DOB and qualifying-exam percentage were included in the comparison.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Round 2 source PDF.")
    parser.add_argument("json", type=Path, help="Generated Round 2 allotment JSON.")
    args = parser.parse_args()
    verify(args.pdf, args.json)


if __name__ == "__main__":
    main()
