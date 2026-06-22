from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    job_id: str
    doc_id: str = ''
    file_name: str
    status: str
    total_chunks: int
    error: str | None = None
    duration_ms: float | None = None


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    history: list[dict[str, str]] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False
    doc_ids: list[str] = Field(default_factory=list)


class SourceDoc(BaseModel):
    file_name: str
    page_number: int | None
    chunk_index: int
    score: float
    text_preview: str


class ChatResponse(BaseModel):
    answer: str
    model_used: str
    sources: list[SourceDoc]
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    weaviate_reachable: bool
    chunk_count: int
    version: str


class DeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int


class StatsResponse(BaseModel):
    total_chunks: int
    weaviate_class: str
