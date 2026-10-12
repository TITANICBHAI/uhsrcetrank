#!/usr/bin/env python3
"""Extract B.Sc. Nursing Round 2 allotments from the supplied source PDF."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

FIELDS = (
    "serialNo", "rollNo", "cetScore", "qualifyingPercent", "dateOfBirth",
    "candidateName", "previousInstitute", "previousCourse", "previousCategory",
    "previousRemark", "allottedInstitute", "allottedCourse", "allottedCategory", "remark",
)
MARKDOWN_HEADERS = (
    "Source Sr. No.", "CET Roll No.", "CET Score", "Qualifying Exam Percentage",
    "Date of Birth", "Candidate Name", "Previous Round Institute",
    "Previous Round Course", "Previous Round Category", "Previous Round Remark",
    "Round 2 Allotted Institute", "Allotted Course", "Allotted Category", "Remark",
)
SERIAL_CELL_Y0 = 809.34
SERIAL_CELL_Y1 = 838.98
ROUND_DATE_PATTERN = re.compile(r"ROUND\s*-\s*2\s+as\s+on\s+(\d{2}\.\d{2}\.\d{4})", re.I)
DATE_PATTERN = re.compile(r"\d{2}/\d{2}/\d{4}")
NUMERIC_PATTERN = re.compile(r"\d+(?:\.\d+)?")
NURSING_COURSE = "B.Sc. Nursing"


def render_samples(pdf_path: Path, output_dir: Path) -> None:
    """Render representative pages to inspect table layout and text alignment."""
    document = pymupdf.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    page_numbers = sorted({0, min(1, len(document) - 1), len(document) // 2, len(document) - 1})
    for page_index in page_numbers:
        page = document[page_index]
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        pixmap.save(output_dir / f"round2-page-{page_index + 1:03d}.png")
        text_path = output_dir / f"round2-page-{page_index + 1:03d}.txt"
        text_path.write_text(page.get_text("text"), encoding="utf-8")
        print(f"Rendered page {page_index + 1}/{len(document)}: {text_path}")


def normalize_cell_text(words: list[tuple[float, float, str]]) -> str:
    """Join words in visual reading order from the rotated PDF cell."""
    words.sort(key=lambda word: (round(word[0], 1), -word[1]))
    return " ".join(word[2] for word in words).strip()


def extract_cell_text(words: list[tuple], cell: pymupdf.Rect) -> str:
    """Read words whose centers fall inside a detected table cell."""
    selected = []
    for word in words:
        x0, y0, x1, y1, text = word[:5]
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2
        if (
            cell.x0 - 0.5 <= center_x <= cell.x1 + 0.5
            and cell.y0 - 0.5 <= center_y <= cell.y1 + 0.5
        ):
            selected.append((x0, y0, text))
    return normalize_cell_text(selected)


def extract_page_records(page: pymupdf.Page, page_number: int) -> list[dict]:
    """Use the PDF's ruled cell geometry to extract all candidate rows."""
    cell_rects_by_bounds = {}
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.width > 15 and rect.height > 15 and rect.x0 >= 25 and rect.x1 <= 860:
            bounds = tuple(round(value, 2) for value in (rect.x0, rect.x1, rect.y0, rect.y1))
            cell_rects_by_bounds[bounds] = rect
    cell_rects = list(cell_rects_by_bounds.values())

    row_bands = set()
    for rect in cell_rects:
        if abs(rect.y0 - SERIAL_CELL_Y0) <= 0.6 and abs(rect.y1 - SERIAL_CELL_Y1) <= 0.6:
            row_bands.add((round(rect.x0, 2), round(rect.x1, 2)))

    words = page.get_text("words")
    records = []
    for row_start, row_end in sorted(row_bands):
        cells = [
            rect for rect in cell_rects
            if abs(rect.x0 - row_start) <= 0.15 and abs(rect.x1 - row_end) <= 0.15
        ]
        cells.sort(key=lambda rect: rect.y0, reverse=True)
        if len(cells) != len(FIELDS):
            raise ValueError(
                f"Page {page_number}, row band {row_start:g}–{row_end:g}: "
                f"expected {len(FIELDS)} ruled cells, found {len(cells)}."
            )

        values = [extract_cell_text(words, cell) for cell in cells]
        if not values[0].isdigit():
            continue
        record = dict(zip(FIELDS, values, strict=True))
        record["serialNo"] = int(record["serialNo"])
        if record["cetScore"].isdigit():
            record["cetScore"] = int(record["cetScore"])
        records.append(record)
    return records


def read_round_date(document: pymupdf.Document) -> str:
    match = ROUND_DATE_PATTERN.search(document[0].get_text("text"))
    if not match:
        raise ValueError("The first PDF page does not identify its Round 2 as-of date.")
    return match.group(1)


def validate_records(records: list[dict], round_date: str) -> None:
    """Fail closed if any source row is lost, malformed, or misordered."""
    if not records:
        raise ValueError("No candidate rows were extracted from the PDF.")

    serials = [record["serialNo"] for record in records]
    expected = list(range(1, len(records) + 1))
    if serials != expected:
        mismatch = next(
            (
                index
                for index, (found, wanted) in enumerate(zip(serials, expected), start=1)
                if found != wanted
            ),
            min(len(serials), len(expected)) + 1,
        )
        found = serials[mismatch - 1] if mismatch <= len(serials) else "missing"
        wanted = expected[mismatch - 1] if mismatch <= len(expected) else "end of list"
        raise ValueError(
            f"Source serial validation failed near record {mismatch}: "
            f"expected {wanted}, found {found}; extracted {len(records)} rows."
        )

    if not ROUND_DATE_PATTERN.fullmatch(f"ROUND-2 as on {round_date}"):
        raise ValueError(f"Could not validate Round 2 publication date {round_date!r}.")

    for record in records:
        label = f"source serial {record['serialNo']}"
        if not re.fullmatch(r"\d{6}", record["rollNo"]):
            raise ValueError(f"{label}: invalid CET roll number {record['rollNo']!r}.")
        if not isinstance(record["cetScore"], int):
            raise ValueError(f"{label}: invalid CET score {record['cetScore']!r}.")
        if not NUMERIC_PATTERN.fullmatch(record["qualifyingPercent"]):
            raise ValueError(
                f"{label}: invalid qualifying percentage {record['qualifyingPercent']!r}."
            )
        if not DATE_PATTERN.fullmatch(record["dateOfBirth"]):
            raise ValueError(f"{label}: invalid DOB {record['dateOfBirth']!r}.")
        for field in ("candidateName", "allottedInstitute", "allottedCourse", "remark"):
            if not record[field]:
                raise ValueError(f"{label}: missing required {field}.")


def markdown_cell(value: object) -> str:
    return str(value).replace("|", r"\|").replace("\n", " ").strip()


def filtered_records(records: list[dict]) -> list[dict]:
    return [
        record for record in records
        if " ".join(record["allottedCourse"].split()).casefold()
        == NURSING_COURSE.casefold()
    ]


def build_markdown(records: list[dict], round_date: str) -> str:
    nursing_rows = filtered_records(records)
    lines = [
        "# B.Sc. Nursing Candidate Allotments — CET-2026 Round 2",
        "",
        "**Department:** Department of Medical Education and Research, Haryana",
        "",
        f"**Examination:** CET-2026 · Round 2 · as of {round_date}",
        "",
        "**Source:** Provisional UG seat-allotment list after grievance redressal.",
        "",
        f"**Source rows:** {len(records)} across all UG courses.",
        f"**B.Sc. Nursing rows:** {len(nursing_rows)}; filtered by the final Round 2 “Allotted Course” field.",
        "",
        "All source fields are retained, including date of birth and qualifying-exam percentage. "
        "The website table intentionally omits those two fields.",
        "",
        "The source serial number is preserved as printed; it is not recalculated as a merit rank.",
        "",
        "## Candidate records",
        "",
        "| " + " | ".join(MARKDOWN_HEADERS) + " |",
        "| " + " | ".join("---" for _ in MARKDOWN_HEADERS) + " |",
    ]
    for record in nursing_rows:
        lines.append("| " + " | ".join(markdown_cell(record[field]) for field in FIELDS) + " |")
    return "\n".join(lines) + "\n"


def build_json(records: list[dict], round_date: str) -> str:
    payload = {
        "title": "Provisional Allotment of Seats — UG Courses, 2026–27",
        "department": "Department of Medical Education and Research, Haryana",
        "exam": "CET-2026",
        "round": 2,
        "asOf": round_date,
        "course": NURSING_COURSE,
        "sourceRecordCount": len(records),
        "records": filtered_records(records),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--markdown", type=Path, help="Filtered Markdown output path.")
    parser.add_argument("--json", type=Path, help="Filtered JSON output path.")
    parser.add_argument(
        "--render-samples",
        type=Path,
        metavar="DIR",
        help="Render beginning, middle, and end pages for visual inspection.",
    )
    args = parser.parse_args()
    if bool(args.markdown) != bool(args.json):
        parser.error("Supply both --markdown and --json, or neither.")
    if args.render_samples:
        render_samples(args.pdf, args.render_samples)
    if args.markdown and args.json:
        document = pymupdf.open(args.pdf)
        round_date = read_round_date(document)
        records = []
        for page_number, page in enumerate(document, start=1):
            records.extend(extract_page_records(page, page_number))

        validate_records(records, round_date)
        nursing_rows = filtered_records(records)
        if not nursing_rows:
            raise ValueError(f"No records have Round 2 allotted course {NURSING_COURSE!r}.")

        # Build and check both outputs before writing either one.
        markdown = build_markdown(records, round_date)
        json_text = build_json(records, round_date)
        payload = json.loads(json_text)
        if len(payload["records"]) != len(nursing_rows):
            raise ValueError("Internal validation failed: Markdown and JSON filters disagree.")

        for output_path, content in ((args.markdown, markdown), (args.json, json_text)):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

        print(
            f"Validated {len(records)} complete source rows "
            f"(serials 1–{records[-1]['serialNo']}); wrote {len(nursing_rows)} "
            f"B.Sc. Nursing records across "
            f"{len(Counter(row['allottedInstitute'] for row in nursing_rows))} colleges."
        )
        print(f"Markdown: {args.markdown}")
        print(f"JSON: {args.json}")
    if not args.render_samples and not args.markdown:
        parser.error("Choose --render-samples DIR or supply both --markdown and --json.")


if __name__ == "__main__":
    main()
