"""
Abstract base class for all document loaders.
Each loader converts a file on disk → RawDocument.
"""

from __future__ import annotations

import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path

from app.domain.enums import FileType
from app.domain.models import RawDocument


def detect_file_type(path: Path) -> FileType:
    suffix = path.suffix.lower().lstrip(".")
    _MAP: dict[str, FileType] = {
        "pdf":  FileType.PDF,
        "docx": FileType.DOCX,
        "doc":  FileType.DOCX,
        "txt":  FileType.TXT,
        "md":   FileType.MARKDOWN,
        "html": FileType.HTML,
        "htm":  FileType.HTML,
        "png":  FileType.IMAGE,
        "jpg":  FileType.IMAGE,
        "jpeg": FileType.IMAGE,
        "tiff": FileType.IMAGE,
        "webp": FileType.IMAGE,
    }
    return _MAP.get(suffix, FileType.UNKNOWN)


class BaseLoader(ABC):
    """All loaders must implement `load`."""

    @abstractmethod
    def load(self, file_path: Path) -> RawDocument:
        """Load a file and return a RawDocument."""

    def _base_metadata(self, file_path: Path) -> dict:
        return {
            "file_name": file_path.name,
            "source": str(file_path.resolve()),
            "file_size_bytes": file_path.stat().st_size,
            "mime_type": mimetypes.guess_type(str(file_path))[0] or "application/octet-stream",
        }
