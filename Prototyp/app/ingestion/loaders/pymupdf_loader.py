"""
PyMuPDF (fitz) loader — fast, local PDF text extraction.

Acts as the lightweight fallback when Unstructured / Marker are unavailable
or when you just need raw text quickly.

Install:  pip install pymupdf
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.domain.enums import FileType, LoaderType
from app.domain.models import RawDocument
from .base_loader import BaseLoader, detect_file_type

logger = logging.getLogger(__name__)


class PyMuPDFLoader(BaseLoader):
    """Extract text page-by-page from a PDF using PyMuPDF (fitz)."""

    def load(self, file_path: Path) -> RawDocument:
        file_type = detect_file_type(file_path)

        if file_type != FileType.PDF:
            # For non-PDFs, just read as text
            return RawDocument(
                file_name=file_path.name,
                file_type=file_type,
                raw_text=file_path.read_text(errors="replace"),
                metadata=self._base_metadata(file_path),
                loader_used=LoaderType.PYMUPDF,
            )

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise RuntimeError("PyMuPDF not installed: pip install pymupdf") from e

        pages: list[str] = []
        with fitz.open(str(file_path)) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text.strip():
                    pages.append(f"[Page {page_num}]\n{text.strip()}")

        metadata = self._base_metadata(file_path)
        metadata["page_count"] = len(pages)

        return RawDocument(
            file_name=file_path.name,
            file_type=FileType.PDF,
            raw_text="\n\n".join(pages),
            metadata=metadata,
            loader_used=LoaderType.PYMUPDF,
        )
