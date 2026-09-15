"""PDF report boundary.

Reports must be generated only from a found public result and must carry the
unofficial disclaimer on every page.
"""


def build_report(*_args, **_kwargs) -> bytes:
    raise NotImplementedError("PDF reporting is enabled after dataset publication.")