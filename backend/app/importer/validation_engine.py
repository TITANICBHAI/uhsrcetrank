class ValidationEngine:
    """Publication safety gate for imported datasets."""

    def validate(self, candidates: list, failed_rows: list[dict]) -> dict:
        return {
            "is_passed": False,
            "status": "SKELETON",
            "successful_candidates": len(candidates),
            "failed_rows": len(failed_rows),
            "errors": ["Validation must be implemented and reviewed before publication."],
        }