from __future__ import annotations
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from app.config import get_settings
from app.domain.enums import IngestStatus, LoaderType
from app.domain.models import IngestJob
from app.ingestion.chunking.semantic_chunker import Chunker
from app.ingestion.loaders.loader_router import LoaderRouter
from app.llm.embeddings import OllamaEmbeddings
from app.vectorstore.weaviate_store import WeaviateStore

logger = logging.getLogger(__name__)
settings = get_settings()

class IngestionPipeline:
    def __init__(self, store, embedder, loader_router=None, chunker=None):
        self.store = store
        self.embedder = embedder
        self.router = loader_router or LoaderRouter()
        self.chunker = chunker or Chunker()

    async def ingest(self, file_path: Path, loader_override: LoaderType = LoaderType.AUTO) -> IngestJob:
        job = IngestJob(file_name=file_path.name, status=IngestStatus.PROCESSING)
        t0 = time.perf_counter()
        try:
            logger.info("[%s] Loading ...", file_path.name)
            raw_doc = await asyncio.to_thread(self.router.load, file_path, loader_override)
            if not raw_doc.raw_text.strip():
                raise ValueError("Loaded document is empty.")
            job.doc_id = raw_doc.doc_id
            logger.info("[%s] Chunking ...", file_path.name)
            chunks = await asyncio.to_thread(self.chunker.chunk, raw_doc)
            if not chunks:
                raise ValueError("No chunks produced.")
            logger.info("[%s] Produced %d chunks.", file_path.name, len(chunks))
            logger.info("[%s] Embedding %d chunks ...", file_path.name, len(chunks))
            texts = [c.text for c in chunks]
            embeddings = await self.embedder.embed_batch(texts)
            logger.info("[%s] Storing in Weaviate ...", file_path.name)
            stored = await asyncio.to_thread(self.store.upsert_chunks, chunks, embeddings)
            job.status = IngestStatus.COMPLETED
            job.total_chunks = stored
            job.finished_at = datetime.utcnow()
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info("[%s] Done - %d chunks stored in %.0f ms", file_path.name, stored, elapsed)
        except Exception as exc:
            job.status = IngestStatus.FAILED
            job.error = str(exc)
            job.finished_at = datetime.utcnow()
            logger.error("[%s] Ingestion failed: %s", file_path.name, exc)
        return job