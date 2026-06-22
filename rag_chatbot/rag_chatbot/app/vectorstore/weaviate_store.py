"""
Weaviate v4 vector store adapter.

Manages:
  - Schema creation / tear-down
  - Upserting Chunk objects with pre-computed embeddings
  - Hybrid (vector + BM25) similarity search
  - Document-level deletion
"""

from __future__ import annotations

import logging
from typing import Any

import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import MetadataQuery

from app.config import get_settings
from app.domain.models import Chunk, RetrievedChunk

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Schema definition ──────────────────────────────────────────────────────

_PROPERTIES: list[Property] = [
    Property(name="chunk_id",    data_type=DataType.TEXT),
    Property(name="doc_id",      data_type=DataType.TEXT),
    Property(name="text",        data_type=DataType.TEXT),
    Property(name="file_name",   data_type=DataType.TEXT),
    Property(name="source",      data_type=DataType.TEXT),
    Property(name="page_number", data_type=DataType.INT),
    Property(name="chunk_index", data_type=DataType.INT),
]


class WeaviateStore:
    """
    Local Weaviate vector store (runs inside Docker via docker-compose.yml).

    Usage:
        store = WeaviateStore()
        store.connect()
        await store.upsert_chunks(chunks, embeddings)
        results = await store.search("query text", query_vector)
        store.close()
    """

    def __init__(self) -> None:
        self._client: weaviate.WeaviateClient | None = None
        self.class_name = settings.weaviate_class_name

    # ── Connection lifecycle ───────────────────────────────────────────────

    def connect(self) -> None:
        self._client = weaviate.connect_to_local(
            host=settings.weaviate_host,
            port=settings.weaviate_port,
            grpc_port=settings.weaviate_grpc_port,
        )
        logger.info(
            "Connected to Weaviate at %s:%d",
            settings.weaviate_host,
            settings.weaviate_port,
        )
        self._ensure_schema()

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("Weaviate connection closed.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    # ── Schema management ─────────────────────────────────────────────────

    def _ensure_schema(self) -> None:
        assert self._client, "Call connect() first."
        if not self._client.collections.exists(self.class_name):
            self._client.collections.create(
                name=self.class_name,
                vectorizer_config=Configure.Vectorizer.none(),  # we supply our own
                properties=_PROPERTIES,
            )
            logger.info("Created Weaviate collection '%s'.", self.class_name)
        else:
            logger.debug("Weaviate collection '%s' already exists.", self.class_name)

    def drop_schema(self) -> None:
        """Delete the entire collection. Useful for testing."""
        assert self._client
        if self._client.collections.exists(self.class_name):
            self._client.collections.delete(self.class_name)
            logger.warning("Dropped Weaviate collection '%s'.", self.class_name)

    # ── Write ─────────────────────────────────────────────────────────────

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        """
        Insert/update chunks. Returns number of objects upserted.
        embeddings must be aligned with chunks (same index).
        """
        assert self._client
        assert len(chunks) == len(embeddings), "chunks and embeddings must be same length."

        collection = self._client.collections.get(self.class_name)
        objects: list[wvc.data.DataObject] = []

        for chunk, vec in zip(chunks, embeddings):
            obj = wvc.data.DataObject(
                properties={
                    "chunk_id":    chunk.chunk_id,
                    "doc_id":      chunk.doc_id,
                    "text":        chunk.text,
                    "file_name":   chunk.metadata.get("file_name", ""),
                    "source":      chunk.metadata.get("source", ""),
                    "page_number": chunk.page_number or 0,
                    "chunk_index": chunk.chunk_index,
                },
                vector=vec,
            )
            objects.append(obj)

        result = collection.data.insert_many(objects)
        failed = len(result.errors) if result.errors else 0
        inserted = len(objects) - failed

        if failed:
            logger.warning("%d chunks failed to upsert.", failed)
        logger.info("Upserted %d/%d chunks.", inserted, len(objects))
        return inserted

    # ── Read ──────────────────────────────────────────────────────────────

    def search(
        self,
        query_vector: list[float],
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Pure vector similarity search.
        Returns RetrievedChunk list sorted by descending similarity.
        """
        assert self._client
        k = top_k or settings.top_k
        collection = self._client.collections.get(self.class_name)

        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=k,
            return_metadata=MetadataQuery(certainty=True, distance=True),
        )

        results: list[RetrievedChunk] = []
        for obj in response.objects:
            p = obj.properties
            chunk = Chunk(
                chunk_id=str(p.get("chunk_id", "")),
                doc_id=str(p.get("doc_id", "")),
                text=str(p.get("text", "")),
                page_number=int(p.get("page_number", 0)) or None,
                chunk_index=int(p.get("chunk_index", 0)),
                metadata={
                    "file_name": p.get("file_name", ""),
                    "source": p.get("source", ""),
                },
            )
            score = obj.metadata.certainty or (1 - (obj.metadata.distance or 1))
            results.append(RetrievedChunk(chunk=chunk, score=score))

        return results

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_document(self, doc_id: str) -> int:
        """Remove all chunks belonging to a doc_id. Returns deleted count."""
        assert self._client
        collection = self._client.collections.get(self.class_name)
        result = collection.data.delete_many(
            where=wvc.query.Filter.by_property("doc_id").equal(doc_id)
        )
        deleted = result.successful if result else 0
        logger.info("Deleted %d chunks for doc_id=%s", deleted, doc_id)
        return deleted

    # ── Stats ─────────────────────────────────────────────────────────────

    def count(self) -> int:
        assert self._client
        collection = self._client.collections.get(self.class_name)
        agg = collection.aggregate.over_all(total_count=True)
        return agg.total_count or 0
