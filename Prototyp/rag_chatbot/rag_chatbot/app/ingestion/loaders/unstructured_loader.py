"""
Unstructured.io loader.

Uses the local `partition` function (no API key needed) to parse:
  PDF, DOCX, DOC, HTML, TXT, Markdown, and image files (via OCR).

Install:  pip install "unstructured[pdf,docx,image]" tesseract-ocr poppler-utils
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.domain.enums import FileType, LoaderType
from app.domain.models import RawDocument

from .base_loader import BaseLoader, detect_file_type

logger = logging.getLogger(__name__)


class UnstructuredLoader(BaseLoader):
    """
    Routes each file type to the appropriate Unstructured partition function.
    Falls back to raw text read for plain .txt files.
    """

    def load(self, file_path: Path) -> RawDocument:
        file_type = detect_file_type(file_path)
        logger.info("UnstructuredLoader: loading %s (%s)", file_path.name, file_type)

        try:
            elements = self._partition(file_path, file_type)
            raw_text = self._elements_to_text(elements)
        except Exception as exc:
            logger.warning(
                "Unstructured partition failed for %s: %s — falling back to raw read.",
                file_path.name, exc,
            )
            raw_text = file_path.read_text(errors="replace")

        metadata = self._base_metadata(file_path)
        metadata["element_count"] = len(elements) if "elements" in dir() else 0

        return RawDocument(
            file_name=file_path.name,
            file_type=file_type,
            raw_text=raw_text,
            metadata=metadata,
            loader_used=LoaderType.UNSTRUCTURED,
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    def _partition(self, path: Path, file_type: FileType) -> list:
        """Dispatch to the right Unstructured partition function."""
        suffix = path.suffix.lower()

        if file_type == FileType.PDF:
            from unstructured.partition.pdf import partition_pdf
            return partition_pdf(
                filename=str(path),
                strategy="hi_res",           # OCR-aware; use "fast" if no GPU
                include_page_breaks=True,
                extract_images_in_pdf=False,
            )

        if file_type == FileType.DOCX:
            from unstructured.partition.docx import partition_docx
            return partition_docx(filename=str(path))

        if file_type == FileType.HTML:
            from unstructured.partition.html import partition_html
            return partition_html(filename=str(path))

        if file_type == FileType.IMAGE:
            from unstructured.partition.image import partition_image
            return partition_image(filename=str(path), strategy="hi_res")

        # TXT / Markdown / fallback
        from unstructured.partition.text import partition_text
        return partition_text(filename=str(path))

    @staticmethod
    def _elements_to_text(elements: list) -> str:
        """
        Concatenate Unstructured elements, preserving page structure.
        Inserts a newline for PageBreak elements.
        """
        parts: list[str] = []
        for el in elements:
            class_name = type(el).__name__
            if class_name == "PageBreak":
                parts.append("\n\n--- PAGE BREAK ---\n\n")
            else:
                text = str(el).strip()
                if text:
                    parts.append(text)
        return "\n\n".join(parts)
