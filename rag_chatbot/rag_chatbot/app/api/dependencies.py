"""
FastAPI dependency injection.

All heavy objects (Weaviate connection, Ollama clients, pipeline) are created
once at startup and injected via FastAPI's Depends() system.
"""

from __future__ import annotations

from functools import lru_cache

from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.loaders.loader_router import LoaderRouter
from app.ingestion.chunking.semantic_chunker import Chunker
from app.llm.embeddings import OllamaEmbeddings
from app.llm.ollama_client import OllamaClient
from app.vectorstore.weaviate_store import WeaviateStore


@lru_cache(maxsize=1)
def get_store() -> WeaviateStore:
    store = WeaviateStore()
    store.connect()
    return store


@lru_cache(maxsize=1)
def get_embedder() -> OllamaEmbeddings:
    return OllamaEmbeddings()


@lru_cache(maxsize=1)
def get_llm() -> OllamaClient:
    return OllamaClient()


@lru_cache(maxsize=1)
def get_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        store=get_store(),
        embedder=get_embedder(),
        loader_router=LoaderRouter(),
        chunker=Chunker(),
    )
