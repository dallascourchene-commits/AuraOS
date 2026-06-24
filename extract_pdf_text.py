"""Compatibility CLI for Aura paper PDF text extraction."""

from __future__ import annotations

from pathlib import Path
import sys

from aura_paper_memory import extract_pdf_text_from_path


def extract_with_pypdf2(pdf_path):
    return extract_pdf_text_from_path(pdf_path, max_pages=10)


def extract_with_pdfplumber(pdf_path):
    return extract_pdf_text_from_path(pdf_path, max_pages=10)


def main(paths: list[str] | None = None) -> int:
    pdfs = paths or [
        "Second_Paper.pdf",
        "Third_Paper.pdf",
        "AuraOS__A_Polysynthetic_Cognitive_Substrate_for_High-Dimensional_Edge_Orchestration_and_Visual_Code_Topology.pdf",
    ]
    for pdf_path in pdfs:
        try:
            text = extract_pdf_text_from_path(pdf_path)
            if not text:
                print(f"ERROR extracting {pdf_path}: no PDF parser available or no text found")
                continue
            output_path = Path(pdf_path).with_suffix("").as_posix() + "_extracted.txt"
            Path(output_path).write_text(text, encoding="utf-8")
            print(f"SUCCESS: Extracted {len(text)} chars to {output_path}")
        except Exception as exc:
            print(f"ERROR extracting {pdf_path}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or None))
