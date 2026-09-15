"""Convert a reviewed Markdown dataset into a Cloudflare D1 SQL import.

This is intentionally local-only. The public Worker never receives raw Markdown
and never calculates positions during a candidate lookup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from app.importer.markdown_importer import MarkdownImporter
from app.ranking.ranking_config import PLACEHOLDER_CONFIG, RankingConfig, RankingCriterion
from app.ranking.ranking_engine import RankingEngine


EXAMS = {
    "bsc-nursing": ("B.Sc Nursing", "UG"),
    "bpt": ("BPT", "UG"),
    "paramedical": ("Paramedical", "UG"),
    "pb-bsc-nursing": ("Post Basic B.Sc Nursing", "OTHER"),
    "msc-nursing": ("M.Sc Nursing", "OTHER"),
    "mpt": ("MPT", "OTHER"),
    "npcc": ("NPCC", "OTHER"),
}


def sql(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def build_dataset(args: argparse.Namespace, content: bytes) -> tuple[dict, dict]:
    label, group = EXAMS[args.exam]
    imported = MarkdownImporter(args.exam, group).import_markdown(content.decode("utf-8"))
    config = PLACEHOLDER_CONFIG
    ranking_mode = args.ranking_mode
    if imported.candidates and all(item.published_order is not None for item in imported.candidates):
        ranking_mode = "PRECOMPUTED"
        config = RankingConfig(
            criteria=[RankingCriterion.PUBLISHED_ORDER],
            version=args.ranking_version,
            position_policy="sequential",
            tie_policy="allow",
        )
    elif ranking_mode == "PRECOMPUTED":
        imported.report.setdefault("blocking_errors", []).append({
            "reason": "PRECOMPUTED datasets require a published order for every candidate",
        })
        imported.report["is_passed"] = False
    ranking = RankingEngine(config).rank(imported.candidates)
    by_roll = {item.candidate.normalized_roll_number: item for item in ranking.ranked_candidates}
    candidates = []
    for candidate in imported.candidates:
        result = by_roll[candidate.normalized_roll_number]
        candidate.merit_position = result.merit_position
        candidate.tie_break_used = result.tie_break_used
        candidates.append({
            "roll_number": candidate.roll_number,
            "normalized_roll_number": candidate.normalized_roll_number,
            "cet_exam": candidate.cet_exam,
            "name": candidate.name,
            "cet_score": candidate.cet_score,
            "percentile": candidate.percentile,
            "dob": candidate.dob.isoformat() if candidate.dob else None,
            "category": candidate.category,
            "course": candidate.extra_fields.get("course") if candidate.extra_fields else None,
            "published_order": candidate.published_order,
            "merit_position": candidate.merit_position,
            "tie_break_used": candidate.tie_break_used,
            "extra_fields_json": json.dumps(candidate.extra_fields or {}, ensure_ascii=False),
        })
    unresolved = [
        candidate["roll_number"]
        for candidate in candidates
        if candidate["merit_position"] is None
    ]
    if unresolved:
        imported.report.setdefault("blocking_errors", []).append({
            "reason": "Every candidate must have a resolved merit position before publication",
            "roll_numbers": unresolved,
        })
        imported.report["is_passed"] = False
        imported.report["status"] = "FAIL"
    imported.report["ranking"] = {
        "version": args.ranking_version if args.ranking_mode == "PRECOMPUTED" else config.version,
        "mode": ranking_mode,
        "criteria": [criterion.value for criterion in config.criteria],
        "unresolved_ties": ranking.unresolved_ties,
        "disclaimer": ranking.ranking_disclaimer,
    }
    dataset = {
        "cet_exam": args.exam,
        "academic_year": args.year,
        "display_name": label,
        "version": args.version or f"{args.year}-{args.exam}-v1",
        "ranking_mode": ranking_mode,
        "ranking_algorithm_version": args.ranking_version if ranking_mode == "ENGINE" else config.version,
        "ranking_criteria_json": json.dumps([criterion.value for criterion in config.criteria]),
        "candidate_count": len(candidates),
        "source_type": "MARKDOWN",
        "source_reference": args.source_reference,
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "validation_status": "PASS_WITH_WARNINGS" if imported.report.get("warnings") and imported.report.get("is_passed") else ("PASS" if imported.report.get("is_passed") else "FAIL"),
        "validation_report_json": json.dumps(imported.report, ensure_ascii=False, default=str),
        "notes": args.notes,
    }
    return dataset, {"dataset": dataset, "candidates": candidates, "validation": imported.report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exam", choices=sorted(EXAMS), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Output SQL file")
    parser.add_argument("--json-output", type=Path, help="Optional JSON export for inspection/archival")
    parser.add_argument("--year", default="2026")
    parser.add_argument("--version")
    parser.add_argument("--ranking-mode", choices=("PRECOMPUTED", "ENGINE"), default="ENGINE")
    parser.add_argument("--ranking-version", default="UNVERIFIED-local-config")
    parser.add_argument("--source-reference", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    content = args.input.read_bytes()
    try:
        dataset, export = build_dataset(args, content)
    except UnicodeDecodeError:
        print("Input must be UTF-8 Markdown.", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")
    if dataset["validation_status"] == "FAIL":
        print(json.dumps(export["validation"], indent=2, default=str), file=sys.stderr)
        print("Validation failed; no SQL import was written.", file=sys.stderr)
        return 2
    statements = [
        "PRAGMA foreign_keys = ON;",
        "BEGIN TRANSACTION;",
        "INSERT INTO datasets (cet_exam, academic_year, display_name, version, ranking_mode, ranking_algorithm_version, ranking_criteria_json, candidate_count, source_type, source_reference, source_sha256, validation_status, validation_report_json, is_published, notes) VALUES ("
        + ", ".join(sql(dataset[key]) for key in (
            "cet_exam", "academic_year", "display_name", "version", "ranking_mode",
            "ranking_algorithm_version", "ranking_criteria_json", "candidate_count",
            "source_type", "source_reference", "source_sha256", "validation_status",
            "validation_report_json",
        ))
        + ", 0, " + sql(dataset["notes"]) + ");",
        "INSERT INTO candidates (dataset_id, merit_position, roll_number, normalized_roll_number, cet_exam, name, cet_score, percentile, dob, category, course, published_order, tie_break_used, extra_fields_json) VALUES",
    ]
    rows = []
    dataset_id_expr = (
        "(SELECT id FROM datasets WHERE source_sha256 = "
        + sql(dataset["source_sha256"])
        + " ORDER BY id DESC LIMIT 1)"
    )
    for candidate in export["candidates"]:
        row_values = [
            dataset_id_expr,
            candidate["merit_position"],
            candidate["roll_number"],
            candidate["normalized_roll_number"],
            candidate["cet_exam"],
            candidate["name"],
            candidate["cet_score"],
            candidate["percentile"],
            candidate["dob"],
            candidate["category"],
            candidate["course"],
            candidate["published_order"],
            candidate["tie_break_used"],
            candidate["extra_fields_json"],
        ]
        rows.append("(" + ", ".join(
            value if isinstance(value, str) and value.startswith("(SELECT") else sql(value)
            for value in row_values
        ) + ")")
    statements[-1] += "\n" + ",\n".join(rows) + ";"
    statements.extend(["COMMIT;", ""])
    args.output.write_text("\n".join(statements), encoding="utf-8")
    print(f"Wrote {len(rows)} candidates to {args.output}")
    print(f"Validation: {dataset['validation_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())