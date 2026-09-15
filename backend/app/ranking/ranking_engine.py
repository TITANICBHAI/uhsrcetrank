from dataclasses import dataclass

from app.ranking.ranking_config import RankingConfig


@dataclass
class RankedCandidate:
    candidate: object
    merit_position: int
    total_candidates: int
    candidates_ahead: int
    tie_break_used: str | None = None


@dataclass
class RankingResult:
    ranked_candidates: list[RankedCandidate]
    unresolved_ties: list[tuple[str, str]]
    config_version: str
    ranking_disclaimer: str | None


class RankingEngine:
    def __init__(self, config: RankingConfig):
        self.config = config

    def rank(self, candidates: list[object]) -> RankingResult:
        raise NotImplementedError(
            "Ranking remains unavailable until the published 2026 ordering is verified."
        )