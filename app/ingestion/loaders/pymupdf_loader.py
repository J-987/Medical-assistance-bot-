from __future__ import annotations
import logging
from pathlib import Path
from app.domain.enums import FileType, LoaderType
from app.domain.models import RawDocument
from .base_loader import BaseLoader, detect_file_type

logger = logging.getLogger(__name__)

class PyMuPDFLoader(BaseLoader):
    def load(self, file_path: Path) -> RawDocument:
        file_type = detect_file_type(file_path)
        if file_type != FileType.PDF:
            return RawDocument(
                file_name=file_path.name, file_type=file_type,
                raw_text=file_path.read_text(errors="replace"),
                metadata=self._base_metadata(file_path),
                loader_used=LoaderType.PYMUPDF,
            )
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(str(file_path)) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    parts = []
                    text = page.extract_text()
                    if text:
                        parts.append(text.strip())
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            clean = [str(c).strip() if c else "" for c in row]
                            parts.append(" | ".join(clean))
                    if parts:
                        pages.append(f"[Page {i}]\n" + "\n".join(parts))
            metadata = self._base_metadata(file_path)
            metadata["page_count"] = len(pages)
            return RawDocument(
                file_name=file_path.name, file_type=FileType.PDF,
                raw_text="\n\n".join(pages),
                metadata=metadata, loader_used=LoaderType.PYMUPDF,
            )
        except Exception as e:
            logger.error("pdfplumber failed: %s", e)
            return RawDocument(
                file_name=file_path.name, file_type=FileType.PDF,
                raw_text="", metadata=self._base_metadata(file_path),
                loader_used=LoaderType.PYMUPDF,
            )
