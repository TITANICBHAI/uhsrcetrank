from __future__ import annotations

import json
import re
from pathlib import Path

import fitz


PDF_PATH = Path("attached_assets/150926cetugresult_1789488607089.pdf")
MARKDOWN_PATH = Path("activation/converted/uhsr-cet-ug-result-2026.md")
REPORT_PATH = Path("activation/reports/uhsr-cet-ug-extraction.json")


def clean(value: str) -> str:
    value = re.sub(r"\s+", " ", value.replace("|", "/")).strip()
    return value


def group_rows(words: list[tuple]) -> list[list[tuple]]:
    candidates = [
        word
        for word in words
        if 105 <= float(word[1]) <= 570
    ]
    candidates.sort(key=lambda word: (float(word[1]), float(word[0])))
    rows: list[list[tuple]] = []
    for word in candidates:
        y = float(word[1])
        if not rows or y - float(rows[-1][0][1]) > 3:
            rows.append([word])
        else:
            rows[-1].append(word)
    return rows


def column_text(row: list[tuple], lower: float, upper: float | None = None) -> str:
    words = [
        word
        for word in row
        if float(word[0]) >= lower and (upper is None or float(word[0]) < upper)
    ]
    words.sort(key=lambda word: float(word[0]))
    return clean(" ".join(str(word[4]) for word in words))


def number_or_blank(value: str) -> str:
    return value if re.fullmatch(r"\d+(?:\.\d+)?", value) else ""


def main() -> None:
    MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    document = fitz.open(PDF_PATH)
    records: list[dict[str, str]] = []
    page_stats: list[dict[str, int]] = []
    malformed_rows: list[dict[str, object]] = []

    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        rows = group_rows(page.get_text("words"))
        page_record_count = 0
        for row in rows:
            source_list_number = column_text(row, 0, 40)
            roll_number = column_text(row, 40, 94)
            if not re.fullmatch(r"\d+", source_list_number) or not re.fullmatch(
                r"[A-Za-z0-9-]{1,40}", roll_number
            ):
                continue

            name = column_text(row, 94, 243)
            father_name = column_text(row, 243, 396)
            dob = column_text(row, 396, 476)
            category = column_text(row, 476, 643)
            marks_raw = column_text(row, 643, 739)
            percentage_raw = column_text(row, 739, None)

            marks = number_or_blank(marks_raw)
            percentage = number_or_blank(percentage_raw)
            if marks_raw.upper() == "ABSENT":
                marks = ""
            if percentage_raw.upper() == "ABSENT":
                percentage = ""

            record = {
                "source_list_number": source_list_number,
                "roll_number": roll_number,
                "name": name,
                "father_name": father_name,
                "dob": dob,
                "category": category,
                "score": marks,
                "percentage": percentage,
            }
            if not name or not dob:
                malformed_rows.append(
                    {
                        "page": page_index + 1,
                        "source_list_number": source_list_number,
                        "roll_number": roll_number,
                        "reason": "Missing candidate name or date of birth",
                        "record": record,
                    }
                )
            records.append(record)
            page_record_count += 1
        page_stats.append({"page": page_index + 1, "records": page_record_count})

    roll_numbers = [record["roll_number"] for record in records]
    source_numbers = [int(record["source_list_number"]) for record in records]
    duplicate_roll_numbers = sorted(
        {roll for roll in roll_numbers if roll_numbers.count(roll) > 1}
    )
    expected_source_numbers = list(range(1, len(records) + 1))
    missing_source_numbers = sorted(
        set(expected_source_numbers) - set(source_numbers)
    )
    unexpected_source_numbers = sorted(
        set(source_numbers) - set(expected_source_numbers)
    )

    with MARKDOWN_PATH.open("w", encoding="utf-8") as output:
        output.write("# UHSR CET 2026 UG Result — Extracted Source List\n\n")
        output.write(
            "> Extracted from the supplied PDF. This is a roll-number-wise "
            "source list for UG Courses (B.Sc. Nursing / BPT / Paramedical). "
            "The source list number is not treated as a merit rank.\n\n"
        )
        output.write(
            "> Review this file against the original PDF before importing. "
            "Blank score and percentage values represent `ABSENT` in the source.\n\n"
        )
        output.write(
            "| Source List Number | Roll Number | Name | Father's Name | "
            "Date of Birth | Category | Score | Percentage |\n"
        )
        output.write(
            "|---:|---|---|---|---|---|---:|---:|\n"
        )
        for record in records:
            output.write(
                "| {source_list_number} | {roll_number} | {name} | "
                "{father_name} | {dob} | {category} | {score} | "
                "{percentage} |\n".format(**record)
            )

    report = {
        "source": str(PDF_PATH),
        "pages": document.page_count,
        "records": len(records),
        "first_source_list_number": min(source_numbers) if source_numbers else None,
        "last_source_list_number": max(source_numbers) if source_numbers else None,
        "first_roll_number": roll_numbers[0] if roll_numbers else None,
        "last_roll_number": roll_numbers[-1] if roll_numbers else None,
        "duplicate_roll_numbers": duplicate_roll_numbers,
        "missing_source_numbers": missing_source_numbers,
        "unexpected_source_numbers": unexpected_source_numbers,
        "malformed_rows": malformed_rows,
        "pages_with_no_records": [
            item["page"] for item in page_stats if item["records"] == 0
        ],
        "absent_score_rows": sum(1 for record in records if not record["score"]),
        "rows_with_score": sum(1 for record in records if record["score"]),
        "rows_with_category": sum(1 for record in records if record["category"]),
        "note": (
            "The PDF is a combined UG roll-number-wise result list. "
            "It does not provide a merit rank or a separate course assignment."
        ),
    }
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Wrote Markdown: {MARKDOWN_PATH}")
    print(f"Wrote report: {REPORT_PATH}")


if __name__ == "__main__":
    main()