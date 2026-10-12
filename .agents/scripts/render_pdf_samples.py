#!/usr/bin/env python3
"""Render representative pages from a PDF and print their text-layer samples."""

from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".agents/outputs/pdf-samples"),
    )
    parser.add_argument("--zoom", type=float, default=1.6)
    args = parser.parse_args()

    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(args.pdf) as document:
        page_numbers = sorted({0, document.page_count // 2, document.page_count - 1})
        print(f"Pages: {document.page_count}")
        for page_number in page_numbers:
            page = document.load_page(page_number)
            image_path = args.output_dir / f"page-{page_number + 1:03d}.png"
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(args.zoom, args.zoom),
                alpha=False,
            )
            pixmap.save(image_path)
            text = page.get_text("text").strip()
            print(
                f"\nPage {page_number + 1}: rotation={page.rotation}, "
                f"size={page.rect.width:.1f}x{page.rect.height:.1f}, "
                f"text_chars={len(text)}, image={image_path}"
            )
            print(text[:1600] if text else "[No text layer]")


if __name__ == "__main__":
    main()
