from __future__ import annotations
import logging
import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import MetadataQuery
from app.config import get_settings
from app.domain.models import Chunk, RetrievedChunk

logger = logging.getLogger(__name__)
settings = get_settings()

_PROPERTIES = [
    Property(name="chunk_id", data_type=DataType.TEXT),
    Property(name="doc_id", data_type=DataType.TEXT),
    Property(name="text", data_type=DataType.TEXT),
    Property(name="file_name", data_type=DataType.TEXT),
    Property(name="source", data_type=DataType.TEXT),
    Property(name="page_number", data_type=DataType.INT),
    Property(name="chunk_index", data_type=DataType.INT),
]

class WeaviateStore:
    def __init__(self):
        self._client = None
        self.class_name = settings.weaviate_class_name

    def connect(self):
        self._client = weaviate.connect_to_local(
            host=settings.weaviate_host,
            port=settings.weaviate_port,
            grpc_port=settings.weaviate_grpc_port,
        )
        logger.info("Connected to Weaviate at %s:%d", settings.weaviate_host, settings.weaviate_port)
        self._ensure_schema()

    def close(self):
        if self._client:
            self._client.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    def _ensure_schema(self):
        if not self._client.collections.exists(self.class_name):
            self._client.collections.create(
                name=self.class_name,
                vectorizer_config=Configure.Vectorizer.none(),
                properties=_PROPERTIES,
            )
            logger.info("Created collection '%s'.", self.class_name)

    def drop_schema(self):
        if self._client.collections.exists(self.class_name):
            self._client.collections.delete(self.class_name)

    def upsert_chunks(self, chunks, embeddings):
        assert len(chunks) == len(embeddings)
        collection = self._client.collections.get(self.class_name)
        objects = []
        for chunk, vec in zip(chunks, embeddings):
            objects.append(wvc.data.DataObject(
                properties={
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "text": chunk.text,
                    "file_name": chunk.metadata.get("file_name", ""),
                    "source": chunk.metadata.get("source", ""),
                    "page_number": chunk.page_number or 0,
                    "chunk_index": chunk.chunk_index,
                },
                vector=vec,
            ))
        result = collection.data.insert_many(objects)
        failed = len(result.errors) if result.errors else 0
        inserted = len(objects) - failed
        logger.info("Upserted %d/%d chunks.", inserted, len(objects))
        return inserted

    def search(self, query_vector, top_k=None, doc_ids=None):
        k = top_k or settings.top_k
        collection = self._client.collections.get(self.class_name)
        filters = None
        if doc_ids:
            if len(doc_ids) == 1:
                filters = wvc.query.Filter.by_property("doc_id").equal(doc_ids[0])
            else:
                filters = wvc.query.Filter.any_of([
                    wvc.query.Filter.by_property("doc_id").equal(d) for d in doc_ids
                ])
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=k,
            filters=filters,
            return_metadata=MetadataQuery(certainty=True, distance=True),
        )
        results = []
        for obj in response.objects:
            p = obj.properties
            chunk = Chunk(
                chunk_id=str(p.get("chunk_id", "")),
                doc_id=str(p.get("doc_id", "")),
                text=str(p.get("text", "")),
                page_number=int(p.get("page_number", 0)) or None,
                chunk_index=int(p.get("chunk_index", 0)),
                metadata={"file_name": p.get("file_name", ""), "source": p.get("source", "")},
            )
            score = obj.metadata.certainty or (1 - (obj.metadata.distance or 1))
            results.append(RetrievedChunk(chunk=chunk, score=score))
        return results

    def delete_document(self, doc_id):
        collection = self._client.collections.get(self.class_name)
        result = collection.data.delete_many(
            where=wvc.query.Filter.by_property("doc_id").equal(doc_id)
        )
        return result.successful if result else 0

    def count(self):
        collection = self._client.collections.get(self.class_name)
        agg = collection.aggregate.over_all(total_count=True)
        return agg.total_count or 0