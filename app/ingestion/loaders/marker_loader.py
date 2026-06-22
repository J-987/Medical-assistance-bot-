"""
Marker loader — wraps the `marker` library (by VikParuchuri).

Marker converts PDFs → clean Markdown, handling:
  - Multi-column layouts
  - Tables
  - Equations (LaTeX)
  - Scanned pages (via Surya OCR, bundled with marker)

Install:  pip install marker-pdf
Model downloads happen automatically on first run (~1 GB).
Set MARKER_ENABLED=false in .env to skip if you don't need it.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.config import get_settings
from app.domain.enums import FileType, LoaderType
from app.domain.models import RawDocument

from .base_loader import BaseLoader, detect_file_type

logger = logging.getLogger(__name__)
settings = get_settings()


class MarkerLoader(BaseLoader):
    """
    Uses Marker to convert a PDF → Markdown text.
    Only supports PDFs; non-PDF files fall back to a plain text read.
    """

    def load(self, file_path: Path) -> RawDocument:
        file_type = detect_file_type(file_path)
        logger.info("MarkerLoader: loading %s", file_path.name)

        if file_type != FileType.PDF:
            logger.warning(
                "MarkerLoader only supports PDF; got %s — falling back to text read.",
                file_type,
            )
            raw_text = file_path.read_text(errors="replace")
        else:
            raw_text = self._convert_with_marker(file_path)

        return RawDocument(
            file_name=file_path.name,
            file_type=file_type,
            raw_text=raw_text,
            metadata=self._base_metadata(file_path),
            loader_used=LoaderType.MARKER,
        )

    # ── Marker conversion ─────────────────────────────────────────────────

    def _convert_with_marker(self, pdf_path: Path) -> str:
        try:
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models

            logger.info("Loading Marker models (first run may take ~60s) …")
            model_list = load_all_models()

            full_text, _images, _metadata = convert_single_pdf(
                str(pdf_path),
                model_list,
                max_pages=settings.marker_max_pages,
                langs=["English"],      # add more language codes as needed
                batch_multiplier=2,
            )
            return full_text or ""

        except ImportError:
            logger.error(
                "marker-pdf is not installed. Run: pip install marker-pdf\n"
                "Falling back to empty string."
            )
            return ""
        except Exception as exc:
            logger.error("Marker conversion failed: %s", exc)
            return ""
