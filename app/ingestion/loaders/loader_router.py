"""
Loader factory — selects the best loader for each file type.

Priority for PDFs:
  1. Marker   (if marker_enabled=True in config) — best quality for complex PDFs
  2. Unstructured — solid for most files including DOCX, HTML, images
  3. PyMuPDF  — fast fallback for simple PDFs

For non-PDFs:
  Unstructured handles DOCX / HTML / images well.
  PyMuPDF is PDF-only, so AUTO will skip it for other types.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.domain.enums import FileType, LoaderType
from app.domain.models import RawDocument

from .base_loader import detect_file_type
from .marker_loader import MarkerLoader
from .pymupdf_loader import PyMuPDFLoader
from .unstructured_loader import UnstructuredLoader

logger = logging.getLogger(__name__)
settings = get_settings()


class LoaderRouter:
    """
    Selects and runs the appropriate loader for a given file.

    Usage:
        router = LoaderRouter()
        doc = router.load(Path("my_paper.pdf"))
    """

    def __init__(self) -> None:
        self._unstructured = UnstructuredLoader()
        self._marker = MarkerLoader()
        self._pymupdf = PyMuPDFLoader()

    def load(
        self,
        file_path: Path,
        override_loader: LoaderType = LoaderType.AUTO,
    ) -> RawDocument:
        """Load file with explicit loader or auto-pick the best one."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        loader_type = override_loader or settings.default_loader
        file_type = detect_file_type(path)

        if loader_type == LoaderType.MARKER:
            return self._marker.load(path)

        if loader_type == LoaderType.UNSTRUCTURED:
            return self._unstructured.load(path)

        if loader_type == LoaderType.PYMUPDF:
            return self._pymupdf.load(path)

        # ── AUTO mode ────────────────────────────────────────────────────
        return self._auto_load(path, file_type)

    def _auto_load(self, path: Path, file_type: FileType) -> RawDocument:
        """
        Intelligent auto-routing:
        - PDF → try Marker first (if enabled), else Unstructured, else PyMuPDF
        - DOCX / HTML / Image → Unstructured
        - TXT / Markdown → Unstructured (partition_text)
        - Unknown → PyMuPDF or Unstructured
        """
        if file_type == FileType.PDF:
            if settings.marker_enabled:
                try:
                    doc = self._marker.load(path)
                    if doc.raw_text.strip():
                        logger.debug("AUTO: used Marker for %s", path.name)
                        return doc
                    logger.warning("Marker returned empty text; falling through.")
                except Exception as exc:
                    logger.warning("Marker failed: %s — trying Unstructured.", exc)

            try:
                doc = self._unstructured.load(path)
                if doc.raw_text.strip():
                    logger.debug("AUTO: used Unstructured for %s", path.name)
                    return doc
            except Exception as exc:
                logger.warning("Unstructured failed: %s — falling back to PyMuPDF.", exc)

            logger.debug("AUTO: used PyMuPDF for %s", path.name)
            return self._pymupdf.load(path)

        # Non-PDF — Unstructured handles everything else
        return self._unstructured.load(path)
