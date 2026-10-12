#!/usr/bin/env python3
"""Extract M.Sc. Nursing Round 2 allotments from the supplied PDF."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pymupdf


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
HEADERS = (
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
MARKDOWN_HEADERS = (
    "Source serial no.",
    "CET roll no.",
    "CET score",
    "Qualifying exam percentage",
    "Date of birth",
    "Candidate name",
    "Previous institute",
    "Previous course",
    "Previous category",
    "Previous remark",
    "Round 2 allotted institute",
    "Allotted course",
    "Allotted category",
    "Round 2 remark",
)
ROUND_DATE_PATTERN = re.compile(
    r"ROUND\s*[- ]?\s*2\s+as\s+on\s+(\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)
DATE_FORMAT = "%d/%m/%Y"


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
        datetime.strptime(value, DATE_FORMAT)
    except ValueError as error:
        raise ValueError(
            f"Page {page_number}, serial {serial}: invalid date-of-birth format."
        ) from error
    return value


def extract_source_records(pdf_path: Path) -> tuple[list[dict[str, object]], str]:
    records: list[dict[str, object]] = []
    as_of_match: re.Match[str] | None = None

    with pymupdf.open(pdf_path) as document:
        if not len(document):
            raise ValueError("The source PDF contains no pages.")

        as_of_match = ROUND_DATE_PATTERN.search(document[0].get_text("text"))
        for page_number, page in enumerate(document, start=1):
            matching_tables = []
            for table in page.find_tables().tables:
                extracted = table.extract()
                if extracted and tuple(header_key(cell) for cell in extracted[0]) == HEADERS:
                    matching_tables.append(extracted)
            if len(matching_tables) != 1:
                raise ValueError(
                    f"Page {page_number}: expected one {len(FIELDS)}-column "
                    f"candidate table; found {len(matching_tables)}."
                )

            for raw_row in matching_tables[0][1:]:
                cells = [clean(cell) for cell in raw_row]
                if not any(cells):
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

                serial = int(cells[0])
                score = parse_decimal(cells[2], "CET score", page_number, cells[0])
                percentage = parse_decimal(
                    cells[3], "qualifying-exam percentage", page_number, cells[0]
                )
                if score != score.to_integral_value():
                    raise ValueError(
                        f"Page {page_number}, serial {cells[0]}: "
                        "CET score is not an integer."
                    )
                if not Decimal(0) <= percentage <= Decimal(100):
                    raise ValueError(
                        f"Page {page_number}, serial {cells[0]}: "
                        "percentage is out of range."
                    )

                record: dict[str, object] = dict(zip(FIELDS, cells, strict=True))
                record["serialNo"] = serial
                record["cetScore"] = int(score)
                record["qualifyingPercent"] = float(percentage)
                record["dateOfBirth"] = parse_date(cells[4], page_number, cells[0])
                records.append(record)

    if not as_of_match:
        raise ValueError("Could not read the Round 2 publication date from page 1.")
    date = datetime.strptime(as_of_match.group(1), "%d.%m.%Y")
    return records, date.strftime("%d.%m.%Y")


def is_allotted_nursing_course(record: dict[str, object]) -> bool:
    return "nursing" in clean(record["allottedCourse"]).casefold()


def markdown_cell(value: object) -> str:
    return clean(value).replace("|", r"\|")


def build_outputs(
    source_records: list[dict[str, object]], as_of: str
) -> tuple[dict[str, object], str]:
    serials = [int(record["serialNo"]) for record in source_records]
    if serials != list(range(1, len(source_records) + 1)):
        raise ValueError("Source serials are duplicated, missing, or out of sequence.")
    rolls = [str(record["rollNo"]) for record in source_records]
    if len(set(rolls)) != len(rolls):
        raise ValueError("Duplicate CET roll numbers found in the source.")
    if not source_records:
        raise ValueError("No source candidate records were extracted.")

    for record in source_records:
        if not record["rollNo"] or not record["candidateName"]:
            raise ValueError(
                f"Source serial {record['serialNo']}: missing candidate identity field."
            )
        if not record["remark"]:
            raise ValueError(f"Source serial {record['serialNo']}: missing Round 2 remark.")

    selected = [
        record for record in source_records if is_allotted_nursing_course(record)
    ]
    if not selected:
        raise ValueError("No final Round 2 allotted Nursing courses matched.")
    if any(str(record["remark"]).casefold() != "allotted" for record in selected):
        raise ValueError(
            "A record matched the final Nursing-course filter but is not marked Allotted."
        )
    if any(not record["allottedInstitute"] for record in selected):
        raise ValueError("A selected Round 2 Nursing record has no allotted institute.")

    data: dict[str, object] = {
        "title": "M.Sc. Nursing Candidate Allotments — Round 2",
        "department": "Department of Medical Education and Research, Haryana",
        "exam": "CET-2026",
        "round": 2,
        "asOf": as_of,
        "course": "M.Sc. Nursing",
        "sourceRecordCount": len(source_records),
        "filter": 'Final Round 2 Allotted Course contains "Nursing" (case-insensitive)',
        "records": selected,
    }

    lines = [
        "# M.Sc. Nursing Candidate Allotments — CET-2026 Round 2",
        "",
        f"**Department:** {data['department']}",
        "",
        f"**Examination:** {data['exam']} · Round 2 · as of {as_of}",
        "",
        "**Filter:** Final Round 2 “Allotted Course” contains “Nursing” "
        "(case-insensitive); previous-round course was not used for selection.",
        "",
        f"**Source rows:** {len(source_records)}",
        f"**Matching records:** {len(selected)}",
        "",
        "All source fields are retained, including date of birth and "
        "qualifying-exam percentage. The website omits those two fields.",
        "Source serial numbers are preserved as printed and are not recalculated "
        "as merit ranks.",
        "",
        "## Candidate records",
        "",
        "| " + " | ".join(MARKDOWN_HEADERS) + " |",
        "| " + " | ".join("---" for _ in MARKDOWN_HEADERS) + " |",
    ]
    for record in selected:
        values = [record[field] for field in FIELDS]
        values[3] = f"{float(values[3]):.3f}"
        lines.append("| " + " | ".join(markdown_cell(value) for value in values) + " |")

    return data, "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Source Round 2 PDF")
    parser.add_argument("--json", type=Path, required=True, help="Website JSON output")
    parser.add_argument(
        "--markdown", type=Path, required=True, help="Auditable source Markdown output"
    )
    args = parser.parse_args()
    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")

    source_records, as_of = extract_source_records(args.pdf)
    data, markdown = build_outputs(source_records, as_of)
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    json.loads(json_text)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json_text, encoding="utf-8")
    args.markdown.write_text(markdown, encoding="utf-8")

    course_counts = Counter(
        str(record["allottedCourse"]) for record in data["records"]
    )
    college_count = len({str(record["allottedInstitute"]) for record in data["records"]})
    scores = [int(record["cetScore"]) for record in data["records"]]
    print(
        f"Validated {len(source_records)} source rows (serials 1–{len(source_records)}); "
        f"wrote {len(data['records'])} allotted M.Sc. Nursing records "
        f"across {college_count} colleges."
    )
    print(f"Final allotted-course counts: {dict(sorted(course_counts.items()))}")
    print(f"CET score range: {min(scores)}–{max(scores)}; as of {as_of}.")
    print(f"JSON: {args.json}")
    print(f"Markdown: {args.markdown}")


if __name__ == "__main__":
    main()
