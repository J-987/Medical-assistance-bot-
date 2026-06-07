"""
Ingestion pipeline — orchestrates the full flow:

  file_path
    └─ LoaderRouter.load()        → RawDocument
         └─ Chunker.chunk()       → list[Chunk]
              └─ OllamaEmbeddings.embed_batch()  → list[list[float]]
                   └─ WeaviateStore.upsert_chunks()  → int (stored count)

Returns an IngestJob with final status and stats.
"""

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
from app.ingestion.deidentify import deidentify
from app.ingestion.loaders.loader_router import LoaderRouter
from app.llm.embeddings import OllamaEmbeddings
from app.vectorstore.weaviate_store import WeaviateStore

logger = logging.getLogger(__name__)
settings = get_settings()


class IngestionPipeline:
    """
    Stateless pipeline object — thread-safe, can be reused across requests.

    Usage (async context):
        pipeline = IngestionPipeline(store, embedder)
        job = await pipeline.ingest(Path("report.pdf"))
    """

    def __init__(
        self,
        store: WeaviateStore,
        embedder: OllamaEmbeddings,
        loader_router: LoaderRouter | None = None,
        chunker: Chunker | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.router = loader_router or LoaderRouter()
        self.chunker = chunker or Chunker()

    async def ingest(
        self,
        file_path: Path,
        loader_override: LoaderType = LoaderType.AUTO,
    ) -> IngestJob:
        """
        Full ingest flow. Returns an IngestJob describing the outcome.
        """
        job = IngestJob(file_name=file_path.name, status=IngestStatus.PROCESSING)
        t0 = time.perf_counter()

        try:
            # 1. Load
            logger.info("[%s] Loading …", file_path.name)
            raw_doc = await asyncio.to_thread(
                self.router.load, file_path, loader_override
            )
            if not raw_doc.raw_text.strip():
                raise ValueError("Loaded document is empty — check the file or loader.")

            # 1b. De-Identifizierung (PII vor dem Einbetten entfernen)
            if settings.deidentify_enabled:
                raw_doc.raw_text, redactions = await asyncio.to_thread(
                    deidentify, raw_doc.raw_text
                )
                raw_doc.metadata["deidentified"] = True
                raw_doc.metadata["redactions"] = redactions
                logger.info(
                    "[%s] De-identified — %d Ersetzungen: %s",
                    file_path.name, sum(redactions.values()), redactions,
                )

            # 2. Chunk
            logger.info("[%s] Chunking …", file_path.name)
            chunks = await asyncio.to_thread(self.chunker.chunk, raw_doc)
            if not chunks:
                raise ValueError("No chunks produced — document may be too short.")
            logger.info("[%s] Produced %d chunks.", file_path.name, len(chunks))

            # 3. Embed
            logger.info("[%s] Embedding %d chunks …", file_path.name, len(chunks))
            texts = [c.text for c in chunks]
            embeddings = await self.embedder.embed_batch(texts)

            # 4. Store
            logger.info("[%s] Storing in Weaviate …", file_path.name)
            stored = await asyncio.to_thread(
                self.store.upsert_chunks, chunks, embeddings
            )

            job.status = IngestStatus.COMPLETED
            job.total_chunks = stored
            job.finished_at = datetime.utcnow()
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info(
                "[%s] ✅ Done — %d chunks stored in %.0f ms",
                file_path.name, stored, elapsed,
            )

        except Exception as exc:
            job.status = IngestStatus.FAILED
            job.error = str(exc)
            job.finished_at = datetime.utcnow()
            logger.error("[%s] ❌ Ingestion failed: %s", file_path.name, exc)

        return job
