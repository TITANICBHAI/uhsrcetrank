#!/usr/bin/env python3
"""Rank a CET Markdown table and generate the self-contained frontend dataset."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


def split_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [cell.strip().replace("\\|", "|") for cell in value.split("|")]


def number(value: str) -> float | None:
    if not value or value.upper() == "ABSENT":
        return None
    try:
        return float(value.replace(",", "").replace("%", ""))
    except ValueError:
        return None


def dob(value: str) -> date | None:
    if not value or value.upper() == "ABSENT":
        return None
    day, month, year = value.split("/")
    return date(int(year), int(month), int(day))


def csv_cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|")


def load_source(path: Path) -> list[dict[str, object]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.startswith("|") or line.startswith("| ---") or "Source List Number" in line:
            continue
        cells = split_row(line)
        if len(cells) != 7:
            continue
        rows.append(
            {
                "source_serial": int(cells[0]),
                "roll_number": cells[1],
                "name": cells[2],
                "father_name": cells[3],
                "dob_raw": cells[4],
                "dob": dob(cells[4]),
                "marks": number(cells[5]),
                "marks_raw": cells[5],
                "percentage": number(cells[6]),
                "percentage_raw": cells[6],
                "source_line": line_number,
            }
        )
    if len(rows) != 18_967:
        raise ValueError(f"Expected 18,967 source rows, found {len(rows)} in {path}")
    rolls = [row["roll_number"] for row in rows]
    if len(set(rolls)) != len(rolls):
        raise ValueError("Duplicate roll numbers found in source Markdown")
    return rows


def sort_key(row: dict[str, object]) -> tuple:
    # None values sort after valid results. A later DOB is a younger candidate.
    percentage = row["percentage"]
    marks = row["marks"]
    birth_date = row["dob"]
    return (
        percentage is None,
        -(percentage or 0),
        marks is None,
        -(marks or 0),
        birth_date is None,
        -(birth_date.toordinal() if birth_date else 0),
        str(row["roll_number"]),
    )


def rank_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(rows, key=sort_key)
    previous_key: tuple | None = None
    previous_rank = 0
    for index, row in enumerate(ordered, start=1):
        tie_key = (
            row["percentage"],
            row["marks"],
            row["dob"],
        )
        if tie_key != previous_key:
            previous_rank = index
            previous_key = tie_key
        row["rank"] = previous_rank
    return ordered


def write_ranked_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    header = """# UHSR CET 2026 Combined UG Result — Ranked Dataset

## Ranking rule

Rows are ordered by **Percentage descending**, then **Marks descending**, then
**Date of Birth descending** so the younger candidate receives priority. Exact
ties share the same competition rank; the next rank skips the tied positions.
`ABSENT` values sort after candidates with numeric results.

This is an independent estimated merit position, not an official UHSR rank.

## Ranked candidates

| Rank | Percentage | Marks | Date of Birth | Roll Number | Candidate Name | Father's Name | Source List Number |
| ---: | ---: | ---: | --- | --- | --- | --- | ---: |
"""
    lines = [header.rstrip()]
    lines.extend(
        "| "
        + " | ".join(
            csv_cell(value)
            for value in (
                row["rank"],
                row["percentage_raw"],
                row["marks_raw"],
                row["dob_raw"],
                row["roll_number"],
                row["name"],
                row["father_name"],
                row["source_serial"],
            )
        )
        + " |"
        for row in rows
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def frontend_payload(rows: list[dict[str, object]]) -> dict:
    candidates = []
    for index, row in enumerate(rows):
        shared = index > 0 and row["rank"] == rows[index - 1]["rank"]
        candidate = {
            "r": row["roll_number"],
            "n": row["name"],
            "s": row["marks"],
            "p": row["percentage"],
            "d": row["dob"].isoformat() if row["dob"] else None,
            "m": row["rank"],
        }
        if shared:
            candidate["t"] = "shared position"
        candidates.append(candidate)

    return {
        "dataset": {
            "academic_year": "2026",
            "display_name": "Combined UG Result — B.Sc Nursing / BPT / Paramedical",
            "version": "2026-ug-ranking-proxy-v2",
            "ranking_mode": "ENGINE",
            "ranking_algorithm_version": "UNVERIFIED-percentage-marks-younger-dob-2026",
            "criteria": ["percentage_desc", "marks_desc", "dob_desc"],
            "candidate_count": len(rows),
            "notes": (
                "Percentage descending, marks descending, younger DOB priority; "
                "exact ties share competition positions."
            ),
            "ranking_disclaimer": (
                "This estimated merit position is independently calculated from "
                "the supplied result PDF. It is not an official UHSR rank."
            ),
        },
        "available_exams": ["bsc-nursing", "bpt", "paramedical"],
        "candidates": candidates,
    }


def write_frontend(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text("window.UHSR_STATIC_DATA = " + serialized + ";\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--ranked-output", type=Path, required=True)
    parser.add_argument("--frontend-output", type=Path, required=True)
    parser.add_argument(
        "--public-output",
        type=Path,
        help="Optional ranked Markdown copy to ship inside the static frontend.",
    )
    args = parser.parse_args()

    rows = rank_rows(load_source(args.source))
    write_ranked_markdown(args.ranked_output, rows)
    if args.public_output:
        write_ranked_markdown(args.public_output, rows)
    write_frontend(args.frontend_output, frontend_payload(rows))
    print(f"Ranked {len(rows)} candidates")
    print(f"Top rank: {rows[0]['rank']} ({rows[0]['name']}, {rows[0]['percentage_raw']}%)")
    print(f"Ranked Markdown: {args.ranked_output}")
    print(f"Frontend dataset: {args.frontend_output}")


if __name__ == "__main__":
    main()