from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from app.domain.enums import ExplainMode


# ── Ingest ────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    job_id: str
    file_name: str
    status: str
    total_chunks: int
    error: str | None = None
    duration_ms: float | None = None


# ── Chat ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    history: list[dict[str, str]] = Field(
        default_factory=list,
        description='List of {"role": "user"|"assistant", "content": "..."}',
    )
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False
    mode: ExplainMode = Field(
        default=ExplainMode.STANDARD,
        description="Erklär-Modus (Scaffolding): einfach | standard | detailliert",
    )


class SourceDoc(BaseModel):
    file_name: str
    page_number: int | None
    chunk_index: int
    score: float
    text_preview: str   # first 200 chars of the chunk


class ChatResponse(BaseModel):
    answer: str
    model_used: str
    sources: list[SourceDoc]
    latency_ms: float


# ── Fragen-Checkliste (Säule "Preparing", DP11) ─────────────────────────────

class ChecklistRequest(BaseModel):
    """Erzeugt aus dem indexierten Befund eine Fragen-Checkliste fürs Arztgespräch."""
    query: str = Field(
        default="Erstelle eine Fragen-Checkliste für mein nächstes Arztgespräch.",
        max_length=4096,
    )
    top_k: int = Field(default=8, ge=1, le=20)


class ChecklistResponse(BaseModel):
    questions: list[str]
    model_used: str
    sources: list[SourceDoc]
    latency_ms: float


# ── Health ────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    weaviate_reachable: bool
    chunk_count: int
    version: str


# ── Documents ─────────────────────────────────────────────────────────────

class DeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int


class StatsResponse(BaseModel):
    total_chunks: int
    weaviate_class: str
