"""
Chunking strategies for RawDocument → list[Chunk].

Strategies:
  RECURSIVE  — LangChain RecursiveCharacterTextSplitter (best general-purpose)
  SEMANTIC   — LangChain SemanticChunker using Ollama embeddings (context-aware)
  FIXED      — Simple fixed-size windows (fastest, least smart)
"""

from __future__ import annotations

import logging
from uuid import uuid4

from app.config import get_settings
from app.domain.enums import ChunkStrategy
from app.domain.models import Chunk, RawDocument

logger = logging.getLogger(__name__)
settings = get_settings()


class Chunker:
    """
    Converts a RawDocument into a list of Chunk objects.

    Usage:
        chunker = Chunker()
        chunks = chunker.chunk(raw_doc)
    """

    def chunk(
        self,
        doc: RawDocument,
        strategy: ChunkStrategy | None = None,
    ) -> list[Chunk]:
        strat = strategy or settings.chunk_strategy
        if strat == ChunkStrategy.SEMANTIC:
            return self._semantic_chunk(doc)
        if strat == ChunkStrategy.FIXED:
            return self._fixed_chunk(doc)
        return self._recursive_chunk(doc)   # default / RECURSIVE

    # ── Recursive (recommended default) ───────────────────────────────────

    def _recursive_chunk(self, doc: RawDocument) -> list[Chunk]:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
            length_function=len,
            add_start_index=True,
        )
        lc_docs = splitter.create_documents(
            [doc.raw_text],
            metadatas=[{"file_name": doc.file_name, "source": doc.metadata.get("source", "")}],
        )

        chunks: list[Chunk] = []
        for idx, lc_doc in enumerate(lc_docs):
            page_num = self._infer_page_number(lc_doc.page_content, doc.raw_text)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid4()),
                    doc_id=doc.doc_id,
                    text=lc_doc.page_content,
                    page_number=page_num,
                    chunk_index=idx,
                    metadata={
                        **lc_doc.metadata,
                        "file_name": doc.file_name,
                        "source": doc.metadata.get("source", ""),
                    },
                )
            )
        logger.info(
            "Recursive chunking → %d chunks from '%s'", len(chunks), doc.file_name
        )
        return chunks

    # ── Semantic (context-aware, slower) ──────────────────────────────────

    def _semantic_chunk(self, doc: RawDocument) -> list[Chunk]:
        """
        Uses LangChain SemanticChunker with Ollama embeddings.
        Requires ollama-embeddings bridge via langchain-ollama.
        Falls back to recursive on error.
        """
        try:
            from langchain_experimental.text_splitter import SemanticChunker
            from langchain_ollama import OllamaEmbeddings as LCOllamaEmbeddings

            embeddings = LCOllamaEmbeddings(
                model=settings.embedding_model.value,
                base_url=settings.ollama_base_url,
            )
            splitter = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=95,
            )
            lc_docs = splitter.create_documents([doc.raw_text])

            chunks: list[Chunk] = []
            for idx, lc_doc in enumerate(lc_docs):
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid4()),
                        doc_id=doc.doc_id,
                        text=lc_doc.page_content,
                        chunk_index=idx,
                        metadata={
                            "file_name": doc.file_name,
                            "source": doc.metadata.get("source", ""),
                        },
                    )
                )
            logger.info(
                "Semantic chunking → %d chunks from '%s'", len(chunks), doc.file_name
            )
            return chunks

        except Exception as exc:
            logger.warning(
                "Semantic chunking failed (%s) — falling back to recursive.", exc
            )
            return self._recursive_chunk(doc)

    # ── Fixed (dumbest, fastest) ──────────────────────────────────────────

    def _fixed_chunk(self, doc: RawDocument) -> list[Chunk]:
        from langchain_text_splitters import CharacterTextSplitter

        splitter = CharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separator="\n",
        )
        texts = splitter.split_text(doc.raw_text)

        return [
            Chunk(
                chunk_id=str(uuid4()),
                doc_id=doc.doc_id,
                text=text,
                chunk_index=idx,
                metadata={
                    "file_name": doc.file_name,
                    "source": doc.metadata.get("source", ""),
                },
            )
            for idx, text in enumerate(texts)
        ]

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _infer_page_number(chunk_text: str, full_text: str) -> int | None:
        """
        Best-effort page number inference by counting [Page N] markers
        that appear before the chunk in the full text.
        Works with PyMuPDF output format.
        """
        import re

        pos = full_text.find(chunk_text[:50])
        if pos == -1:
            return None
        preceding = full_text[:pos]
        pages = re.findall(r"\[Page (\d+)\]", preceding)
        return int(pages[-1]) if pages else None
