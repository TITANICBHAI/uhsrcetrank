from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RawTable:
    headers: list[str]
    rows: list[list[str]]
    source_rows: list[int]
    issues: list[dict[str, object]]


_SEPARATOR = re.compile(r"^\s*:?-{2,}:?\s*$")
_PAGE_ARTIFACT = re.compile(r"^\s*(?:page\s*)?\d+\s*(?:of\s*\d+)?\s*$", re.I)


def _cells(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [cell.strip().replace("\u00a0", " ") for cell in value.split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(not cell or _SEPARATOR.fullmatch(cell) for cell in cells)


class TableExtractor:
    """Extract pipe tables from PDF-converted Markdown without shifting columns."""

    def extract(self, markdown: str) -> list[RawTable]:
        lines = markdown.splitlines()
        tables: list[RawTable] = []
        index = 0
        while index < len(lines):
            if "|" not in lines[index]:
                index += 1
                continue
            headers = _cells(lines[index])
            if len(headers) < 2 or index + 1 >= len(lines) or "|" not in lines[index + 1]:
                index += 1
                continue
            if not _is_separator(_cells(lines[index + 1])):
                index += 1
                continue

            table = RawTable(headers, [], [], [])
            index += 2
            normalized_headers = [re.sub(r"\s+", " ", value.lower()).strip() for value in headers]
            while index < len(lines) and "|" in lines[index]:
                source_row = index + 1
                cells = _cells(lines[index])
                index += 1
                if not cells or not any(cells) or _is_separator(cells):
                    continue
                if _PAGE_ARTIFACT.fullmatch(" ".join(cells)):
                    continue
                normalized_cells = [re.sub(r"\s+", " ", value.lower()).strip() for value in cells]
                if normalized_cells == normalized_headers:
                    continue
                if len(cells) != len(headers):
                    table.issues.append({
                        "source_row": source_row,
                        "reason": f"Expected {len(headers)} columns, found {len(cells)}",
                    })
                    continue
                table.rows.append(cells)
                table.source_rows.append(source_row)
            if table.rows or table.issues:
                tables.append(table)
        return tables