from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.enums import (
    ChatModel,
    ChunkStrategy,
    EmbeddingModel,
    LoaderType,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "Local RAG Chatbot"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── Ollama ───────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    chat_model: ChatModel = ChatModel.LLAMA3
    embedding_model: EmbeddingModel = EmbeddingModel.NOMIC
    ollama_timeout: int = 120            # seconds
    ollama_num_ctx: int = 4096           # context window

    # ── Weaviate ─────────────────────────────────────────────────────────
    weaviate_host: str = "localhost"
    weaviate_port: int = 8080
    weaviate_grpc_port: int = 50051
    weaviate_class_name: str = "RagChunk"

    # ── Ingestion ────────────────────────────────────────────────────────
    default_loader: LoaderType = LoaderType.AUTO
    chunk_strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    chunk_size: int = 512
    chunk_overlap: int = 64
    upload_dir: str = "uploads"

    # ── Datenschutz / De-Identifizierung (DSGVO Art. 9) ──────────────────
    deidentify_enabled: bool = True   # PII vor dem Einbetten entfernen

    # ── Retrieval ────────────────────────────────────────────────────────
    top_k: int = 5
    similarity_threshold: float = 0.70

    # ── Marker (optional) ────────────────────────────────────────────────
    marker_enabled: bool = True
    marker_max_pages: int | None = None   # None = all pages

    # ── Unstructured.io (optional cloud API) ─────────────────────────────
    unstructured_api_key: str | None = None
    unstructured_api_url: str = "https://api.unstructured.io/general/v0/general"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
