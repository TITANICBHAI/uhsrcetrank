#!/usr/bin/env python3
"""Extract the allotted M.Sc. Nursing Round 1 records from a ruled PDF table."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pymupdf


FIELDS = [
    "serialNo",
    "rollNo",
    "cetScore",
    "qualifyingPercent",
    "dateOfBirth",
    "candidateName",
    "category",
    "course",
    "college",
    "remark",
]
HEADERS = [
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
MARKDOWN_HEADERS = [
    "Serial no.",
    "CET roll no.",
    "CET score",
    "Qualifying exam percentage",
    "Date of birth",
    "Candidate name",
    "Allotted category",
    "Allotted course",
    "Allotted institute",
    "Remark",
]


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def header_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", clean(value).casefold())


def parse_decimal(value: str, label: str, page_number: int, serial: str) -> Decimal:
    try:
        number = Decimal(value.replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(
            f"Page {page_number}, serial {serial}: invalid {label}."
        ) from error
    if not number.is_finite():
        raise ValueError(f"Page {page_number}, serial {serial}: invalid {label}.")
    return number


def parse_date(value: str, page_number: int, serial: str) -> str:
    try:
        datetime.strptime(value, "%d/%m/%Y")
    except ValueError as error:
        raise ValueError(
            f"Page {page_number}, serial {serial}: invalid date-of-birth format."
        ) from error
    return value


def page_rows(pdf_path: Path) -> tuple[list[dict[str, object]], str]:
    records: list[dict[str, object]] = []
    as_of_match: re.Match[str] | None = None

    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document, start=1):
            if page_index == 1:
                as_of_match = re.search(
                    r"ROUND\s*[- ]?\s*1\s+as\s+on\s+(\d{2}\.\d{2}\.\d{4})",
                    page.get_text("text"),
                    re.IGNORECASE,
                )

            matching_tables = []
            for table in page.find_tables().tables:
                extracted = table.extract()
                if extracted and [header_key(cell) for cell in extracted[0]] == HEADERS:
                    matching_tables.append(extracted)
            if len(matching_tables) != 1:
                raise ValueError(
                    f"Page {page_index}: expected one 10-column candidate table; "
                    f"found {len(matching_tables)}."
                )

            table_rows = matching_tables[0]
            for raw_row in table_rows[1:]:
                cells = [clean(cell) for cell in raw_row]
                if not any(cells):
                    continue
                if len(cells) != len(FIELDS):
                    raise ValueError(
                        f"Page {page_index}: expected 10 cells, found {len(cells)}."
                    )
                if not cells[0].isdigit():
                    raise ValueError(
                        f"Page {page_index}: non-empty table row has no numeric serial."
                    )

                serial = int(cells[0])
                score = parse_decimal(cells[2], "CET score", page_index, cells[0])
                percentage = parse_decimal(
                    cells[3], "qualifying-exam percentage", page_index, cells[0]
                )
                if score != score.to_integral_value():
                    raise ValueError(
                        f"Page {page_index}, serial {cells[0]}: CET score is not an integer."
                    )
                if not Decimal(0) <= percentage <= Decimal(100):
                    raise ValueError(
                        f"Page {page_index}, serial {cells[0]}: percentage is out of range."
                    )

                record: dict[str, object] = {
                    "serialNo": serial,
                    "rollNo": cells[1],
                    "cetScore": int(score),
                    "qualifyingPercent": float(percentage),
                    "dateOfBirth": parse_date(cells[4], page_index, cells[0]),
                    "candidateName": cells[5],
                    "category": cells[6],
                    "course": cells[7],
                    "college": cells[8],
                    "remark": cells[9],
                }
                if not record["rollNo"] or not record["candidateName"]:
                    raise ValueError(
                        f"Page {page_index}, serial {cells[0]}: missing required identity field."
                    )
                records.append(record)

    if not as_of_match:
        raise ValueError("Could not read the Round 1 publication date from page 1.")
    date = datetime.strptime(as_of_match.group(1), "%d.%m.%Y")
    as_of = date.strftime("%-d %B %Y")
    return records, as_of


def is_allotted_nursing_course(record: dict[str, object]) -> bool:
    course = clean(record["course"])
    return "nursing" in course.casefold()


def markdown_cell(value: object) -> str:
    return str(value).replace("|", r"\|").replace("\n", "<br>")


def format_percent(value: object) -> str:
    return f"{float(value):.3f}"


def build_markdown(data: dict[str, object]) -> str:
    records = data["records"]
    lines = [
        "# M.Sc. Nursing Candidate Allotments — 2026–27",
        "",
        f"**Department:** {data['department']}",
        "",
        f"**Examination:** {data['exam']} · {data['round']} · {data['asOf']}",
        "",
        '**Filter:** Allotted Course contains “Nursing” (case-insensitive). No separate remark/status filter was applied.',
        "",
        f"**Source rows:** {data['sourceRecordCount']}",
        "",
        f"**Matching records:** {len(records)}",
        "",
        "## Candidate records",
        "",
        "| " + " | ".join(MARKDOWN_HEADERS) + " |",
        "| " + " | ".join("---" for _ in MARKDOWN_HEADERS) + " |",
    ]
    for record in records:
        values = [record[field] for field in FIELDS]
        values[3] = format_percent(values[3])
        lines.append("| " + " | ".join(markdown_cell(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Source Round 1 PDF")
    parser.add_argument("--json", type=Path, required=True, help="Website JSON output")
    parser.add_argument("--markdown", type=Path, required=True, help="Audit Markdown output")
    args = parser.parse_args()
    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")

    source_records, as_of = page_rows(args.pdf)
    source_serials = [int(record["serialNo"]) for record in source_records]
    if source_serials != list(range(1, len(source_serials) + 1)):
        raise ValueError("Source serials are duplicated, missing, or out of sequence.")
    roll_numbers = [str(record["rollNo"]) for record in source_records]
    if len(set(roll_numbers)) != len(roll_numbers):
        raise ValueError("Duplicate CET roll numbers found in the source.")

    records = [record for record in source_records if is_allotted_nursing_course(record)]
    if not records:
        raise ValueError("No allotted Nursing-course records matched the filter.")
    if any(record["remark"].casefold() != "allotted" for record in records):
        raise ValueError("A record matched the allotted-course filter but is not marked Allotted.")
    colleges = {str(record["college"]) for record in records}
    scores = [int(record["cetScore"]) for record in records]
    course_counts = Counter(str(record["course"]) for record in records)

    data: dict[str, object] = {
        "title": "M.Sc. Nursing Candidate Allotments",
        "department": "Department of Medical Education and Research, Haryana",
        "exam": "CET-2026",
        "round": "Round 1",
        "asOf": as_of,
        "course": "M.Sc. Nursing",
        "sourceRecordCount": len(source_records),
        "filter": 'Allotted Course contains "Nursing" (case-insensitive)',
        "records": records,
    }
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    markdown_text = build_markdown(data)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json_text, encoding="utf-8")
    args.markdown.write_text(markdown_text, encoding="utf-8")

    print(
        f"Validated {len(source_records)} source rows (serials 1–{len(source_records)}); "
        f"wrote {len(records)} allotted M.Sc. Nursing records across {len(colleges)} colleges."
    )
    print(f"Allotted-course counts: {dict(sorted(course_counts.items()))}")
    print(f"CET score range: {min(scores)}–{max(scores)}; as of {as_of}.")
    print(f"JSON: {args.json}")
    print(f"Markdown: {args.markdown}")


if __name__ == "__main__":
    main()
