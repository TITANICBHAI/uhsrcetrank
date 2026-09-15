from dataclasses import dataclass


@dataclass
class ImportResult:
    candidates: list[object]
    report: dict


class MarkdownImporter:
    """Backend skeleton for the reviewed Markdown import pipeline.

    Real source activation must add extraction, normalization, validation, and
    provenance review before a dataset can be published.
    """

    def __init__(self, cet_exam: str, cet_group: str):
        self.cet_exam = cet_exam
        self.cet_group = cet_group

    def import_markdown(self, markdown: str) -> ImportResult:
        if not markdown.strip():
            return ImportResult([], {"is_passed": False, "errors": ["Empty source"]})
        return ImportResult(
            [],
            {
                "is_passed": False,
                "status": "SKELETON",
                "errors": ["Importer review is not implemented in this foundation build."],
            },
        )