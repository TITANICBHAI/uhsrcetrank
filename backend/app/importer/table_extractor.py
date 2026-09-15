from dataclasses import dataclass


@dataclass
class RawTable:
    headers: list[str]
    rows: list[list[str]]


class TableExtractor:
    """Placeholder interface for pipe-table extraction from PDF-converted Markdown."""

    def extract(self, markdown: str) -> list[RawTable]:
        raise NotImplementedError("Table extraction is implemented during data-engine phase.")