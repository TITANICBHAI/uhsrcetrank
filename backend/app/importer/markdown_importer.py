from dataclasses import dataclass, field

from .candidate_normalizer import CandidateNormalizer, CandidateRecord
from .table_extractor import TableExtractor
from .validation_engine import ValidationEngine


@dataclass
class ImportResult:
    candidates: list[CandidateRecord]
    report: dict
    failures: list[dict] = field(default_factory=list)


class MarkdownImporter:
    """Import one exam's Markdown source into reviewable candidate records."""

    def __init__(self, cet_exam: str, cet_group: str):
        self.cet_exam = cet_exam
        self.cet_group = cet_group
        self.extractor = TableExtractor()
        self.normalizer = CandidateNormalizer()
        self.validator = ValidationEngine()

    def import_markdown(self, markdown: str) -> ImportResult:
        if not markdown.strip():
            failure = {"source_row": 0, "reason": "Empty source"}
            return ImportResult([], self.validator.validate([], [failure]), [failure])

        candidates: list[CandidateRecord] = []
        failures: list[dict] = []
        warnings: list[dict] = []
        for table in self.extractor.extract(markdown):
            failures.extend(table.issues)
            for cells, source_row in zip(table.rows, table.source_rows):
                try:
                    row = dict(zip(table.headers, cells))
                    candidates.append(self.normalizer.normalize_row(
                        row, self.cet_exam, self.cet_group, source_row
                    ))
                except ValueError as exc:
                    failures.append({"source_row": source_row, "reason": str(exc)})

        seen: dict[str, CandidateRecord] = {}
        unique: list[CandidateRecord] = []
        for candidate in candidates:
            previous = seen.get(candidate.normalized_roll_number)
            if previous is None:
                seen[candidate.normalized_roll_number] = candidate
                unique.append(candidate)
            elif previous.fingerprint() == candidate.fingerprint():
                warnings.append({
                    "source_row": candidate.source_row_number,
                    "roll_number": candidate.roll_number,
                    "reason": "Exact duplicate row was safely deduplicated",
                })
            else:
                unique.append(candidate)

        report = self.validator.validate(unique, failures, warnings)
        report["tables_detected"] = len(self.extractor.extract(markdown))
        report["failures"] = failures
        return ImportResult(unique, report, failures)