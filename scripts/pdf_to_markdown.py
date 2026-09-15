#!/usr/bin/env python3
"""Convert the UHSR CET PDF's roll-number list into reviewable Markdown."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import fitz


HEADER = """# UHSR CET 2026 Combined UG Result

## Source

- Document: PT. B.D. Sharma University of Health Sciences, Rohtak — Common Entrance Test 2026
- Exam date: 13 September 2026
- Coverage: B.Sc. Nursing, BPT, and Paramedical courses
- Source file: `150926cetugresult_1789490898176.pdf`
- Records: 18,967

The source list is preserved in roll-number order. `ABSENT` is retained exactly
as printed in the source result. The source serial number is not a merit rank.

## Candidates

| Source List Number | Roll Number | Candidate Name | Father's Name | Date of Birth | Marks | Percentage |
| ---: | --- | --- | --- | --- | ---: | ---: |
"""


def row_from_block(block: dict) -> list[str] | None:
    lines = block.get("lines", [])
    values = ["".join(span["text"] for span in line["spans"]).strip() for line in lines]
    if (
        block["bbox"][0] >= 40
        or block["bbox"][1] <= 105
        or len(values) != 7
        or not re.fullmatch(r"\d+", values[0])
        or not re.fullmatch(r"\d{6}", values[1])
    ):
        return None
    return values


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def convert(pdf_path: Path) -> str:
    document = fitz.open(pdf_path)
    rows: list[list[str]] = []
    for page in document:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            row = row_from_block(block)
            if row:
                rows.append(row)

    expected = list(range(1, len(rows) + 1))
    serials = [int(row[0]) for row in rows]
    if serials != expected:
        raise ValueError(
            f"PDF row validation failed: expected serials 1..{len(rows)}, "
            f"found {serials[:3]}...{serials[-3:]}"
        )

    output = [HEADER.rstrip()]
    output.extend(
        "| "
        + " | ".join(markdown_cell(value) for value in row)
        + " |"
        for row in rows
    )
    output.append("")
    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--public-output",
        type=Path,
        help="Optional second copy to ship inside the static frontend.",
    )
    args = parser.parse_args()
    markdown = convert(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    if args.public_output:
        args.public_output.parent.mkdir(parents=True, exist_ok=True)
        args.public_output.write_text(markdown, encoding="utf-8")
    record_count = sum(1 for line in markdown.splitlines() if line.startswith("| ") and not line.startswith("| ---"))
    print(f"Wrote {markdown.count(chr(10))} lines and {record_count} candidate rows to {args.output}")


if __name__ == "__main__":
    main()