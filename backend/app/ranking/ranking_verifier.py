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
        def roll(value: object) -> str:
            candidate = getattr(value, "candidate", value)
            if isinstance(candidate, dict):
                return str(candidate.get("normalized_roll_number") or candidate.get("roll_number") or "")
            return str(getattr(candidate, "normalized_roll_number", None) or getattr(candidate, "roll_number", ""))

        ours = [roll(item) for item in our_ranking]
        published = [str(value).strip().upper() for value in published_order]
        our_positions = {value: position for position, value in enumerate(ours, start=1)}
        published_positions = {value: position for position, value in enumerate(published, start=1)}
        missing = [value for value in published if value not in our_positions]
        extra = [value for value in ours if value not in published_positions]
        disagreements: list[dict] = []
        exact = 0
        maximum_delta = 0
        for value, expected in published_positions.items():
            actual = our_positions.get(value)
            if actual == expected:
                exact += 1
            elif actual is not None:
                delta = abs(actual - expected)
                maximum_delta = max(maximum_delta, delta)
                disagreements.append({
                    "roll_number": value,
                    "expected_position": expected,
                    "actual_position": actual,
                    "delta": delta,
                })
        total = len(published)
        return VerificationReport(
            total_candidates=total,
            exact_matches=exact,
            disagreements=disagreements,
            maximum_position_delta=maximum_delta,
            agreement_percentage=round((exact / total * 100) if total else 0.0, 2),
            missing_roll_numbers=missing,
            extra_roll_numbers=extra,
        )