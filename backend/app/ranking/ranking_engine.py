from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import cmp_to_key
from typing import Any

from app.ranking.ranking_config import RankingConfig, RankingCriterion


@dataclass
class RankedCandidate:
    candidate: object
    merit_position: int | None
    total_candidates: int
    candidates_ahead: int | None
    tie_break_used: str | None = None


@dataclass
class RankingResult:
    ranked_candidates: list[RankedCandidate]
    unresolved_ties: list[tuple[str, str]]
    config_version: str
    ranking_disclaimer: str | None


def _get(candidate: object, field: str) -> Any:
    if isinstance(candidate, dict):
        return candidate.get(field)
    return getattr(candidate, field, None)


def _roll(candidate: object) -> str:
    return str(_get(candidate, "normalized_roll_number") or _get(candidate, "roll_number") or "")


class RankingEngine:
    def __init__(self, config: RankingConfig):
        self.config = config

    def _compare(self, left: object, right: object) -> int:
        for criterion in self.config.criteria:
            if criterion == RankingCriterion.PUBLISHED_ORDER:
                field, descending = "published_order", False
            elif criterion == RankingCriterion.PERCENTILE_DESC:
                field, descending = "percentile", True
            elif criterion == RankingCriterion.SCORE_DESC:
                field, descending = "cet_score", True
            elif criterion == RankingCriterion.DOB_ASC:
                field, descending = "dob", False
            else:
                field, descending = "dob", True
            left_value, right_value = _get(left, field), _get(right, field)
            left_missing, right_missing = left_value is None, right_value is None
            if left_missing or right_missing:
                if left_missing and right_missing:
                    continue
                return 1 if left_missing else -1
            if left_value == right_value:
                continue
            result = -1 if left_value < right_value else 1
            return -result if descending else result
        return 0

    def rank(self, candidates: list[object]) -> RankingResult:
        ordered = sorted(candidates, key=cmp_to_key(self._compare))
        ties: list[tuple[str, str]] = []
        for left, right in zip(ordered, ordered[1:]):
            if self._compare(left, right) == 0:
                ties.append((_roll(left), _roll(right)))

        ranked: list[RankedCandidate] = []
        previous_base_position = 0
        group_position = 0
        for index, candidate in enumerate(ordered):
            same_as_previous = index > 0 and self._compare(ordered[index - 1], candidate) == 0
            if self.config.position_policy == "sequential":
                base_position = index + 1
            else:
                if not same_as_previous:
                    group_position += 1
                    base_position = index + 1 if self.config.position_policy == "competition" else group_position
                else:
                    base_position = previous_base_position
            previous_base_position = base_position
            position = base_position
            if same_as_previous and self.config.tie_policy == "block_if_unresolved":
                position = None
            ranked.append(RankedCandidate(
                candidate=candidate,
                merit_position=position,
                total_candidates=len(ordered),
                candidates_ahead=(position - 1 if position is not None else None),
                tie_break_used=None if not same_as_previous else "unresolved tie",
            ))

        disclaimer = None
        if "UNVERIFIED" in self.config.version:
            disclaimer = (
                "This estimated merit position uses a configured calculation that has not "
                "been verified against the complete published UHSR CET 2026 ordering. "
                "Do not treat it as an official UHSR rank."
            )
        return RankingResult(ranked, ties, self.config.version, disclaimer)