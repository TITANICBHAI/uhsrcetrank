from dataclasses import dataclass
from enum import Enum


class RankingCriterion(str, Enum):
    PERCENTILE_DESC = "percentile_desc"
    SCORE_DESC = "score_desc"
    DOB_ASC = "dob_asc"
    DOB_DESC = "dob_desc"
    PUBLISHED_ORDER = "published_order"


@dataclass(frozen=True)
class RankingConfig:
    criteria: list[RankingCriterion]
    version: str = "v1-UNVERIFIED-placeholder"
    position_policy: str = "competition"
    missing_policy: str = "last"
    tie_policy: str = "block_if_unresolved"


PLACEHOLDER_CONFIG = RankingConfig(
    criteria=[
        RankingCriterion.PERCENTILE_DESC,
        RankingCriterion.SCORE_DESC,
        RankingCriterion.DOB_ASC,
    ]
)