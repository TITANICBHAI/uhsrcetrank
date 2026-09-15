class CandidateNormalizer:
    """Placeholder interface for source-field normalization."""

    def normalize_row(self, row: dict, cet_exam: str, cet_group: str):
        raise NotImplementedError("Candidate normalization is implemented during data-engine phase.")