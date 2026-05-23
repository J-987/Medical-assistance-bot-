from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from .enums import FileType, IngestStatus, LoaderType


# ─────────────────────────── Document primitive ───────────────────────────

@dataclass
class RawDocument:
    """Represents a freshly loaded file before chunking."""
    doc_id: str = field(default_factory=lambda: str(uuid4()))
    file_name: str = ""
    file_type: FileType = FileType.UNKNOWN
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    loader_used: LoaderType = LoaderType.AUTO
    loaded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Chunk:
    """A single embeddable text chunk derived from a RawDocument."""
    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    doc_id: str = ""
    text: str = ""
    page_number: int | None = None
    chunk_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_weaviate_object(self, embedding: list[float]) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "file_name": self.metadata.get("file_name", ""),
            "source": self.metadata.get("source", ""),
            "embedding": embedding,
        }


# ─────────────────────────── Ingestion tracking ───────────────────────────

@dataclass
class IngestJob:
    job_id: str = field(default_factory=lambda: str(uuid4()))
    file_name: str = ""
    status: IngestStatus = IngestStatus.PENDING
    total_chunks: int = 0
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


# ─────────────────────────── Chat / RAG primitives ────────────────────────

@dataclass
class RetrievedChunk:
    """A chunk returned from the vector store with its relevance score."""
    chunk: Chunk
    score: float


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RAGResponse:
    answer: str
    sources: list[RetrievedChunk]
    model_used: str
    latency_ms: float
    query: str
