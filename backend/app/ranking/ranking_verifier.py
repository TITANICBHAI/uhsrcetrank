from dataclasses import dataclass


@dataclass
class VerificationReport:
    total_candidates: int
    exact_matches: int
    disagreements: list[dict]
    maximum_position_delta: int
    agreement_percentage: float
    missing_roll_numbers: list[str]
    extra_roll_numbers: list[str]


class RankingVerifier:
    def compare_against_published(self, our_ranking: list, published_order: list[str]) -> VerificationReport:
        raise NotImplementedError("Ranking verification requires an actual published source.")