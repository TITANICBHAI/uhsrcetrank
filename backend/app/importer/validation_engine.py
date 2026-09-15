from __future__ import annotations

from collections import Counter

from .candidate_normalizer import CandidateRecord


class ValidationEngine:
    """Publication safety gate for imported datasets."""

    def validate(
        self,
        candidates: list[CandidateRecord],
        failed_rows: list[dict],
        warnings: list[dict] | None = None,
    ) -> dict:
        warnings = warnings or []
        counts = Counter(candidate.normalized_roll_number for candidate in candidates)
        duplicates = [
            {"roll_number": roll, "occurrences": count}
            for roll, count in counts.items()
            if count > 1
        ]
        blocking = list(failed_rows)
        if not candidates:
            blocking.append({"reason": "No usable candidate rows were imported"})
        if duplicates:
            blocking.append({
                "reason": "Conflicting duplicate roll numbers require review",
                "roll_numbers": duplicates,
            })
        missing_inputs = sum(
            candidate.published_order is None
            and candidate.cet_score is None
            and candidate.percentile is None
            for candidate in candidates
        )
        if candidates and missing_inputs == len(candidates):
            blocking.append({"reason": "No candidate has a published order, score, or percentile"})
        return {
            "status": "FAIL" if blocking else ("PASS_WITH_WARNINGS" if warnings else "PASS"),
            "is_passed": not blocking,
            "total_rows": len(candidates) + len(failed_rows),
            "successful_candidates": len(candidates),
            "failed_rows": len(failed_rows),
            "warning_count": len(warnings),
            "blocking_errors": blocking,
            "warnings": warnings,
            "duplicate_roll_numbers": duplicates,
            "missing_ranking_inputs": missing_inputs,
        }