"""
Async Ollama embedding client.
Converts raw text → dense float vectors using a locally running model.
Default: nomic-embed-text (768-dim, very fast, great for RAG).
"""

from __future__ import annotations

import logging

import ollama

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaEmbeddings:
    """
    Thin async wrapper for Ollama embed endpoint.

    Usage:
        embedder = OllamaEmbeddings()
        vec = await embedder.embed("some text")
        vecs = await embedder.embed_batch(["text1", "text2"])
    """

    # Known output dimensions for validation (add more as needed)
    _DIM_MAP: dict[str, int] = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
    }

    def __init__(self) -> None:
        self._client = ollama.AsyncClient(host=settings.ollama_base_url)
        self.model = settings.embedding_model.value
        self.expected_dim = self._DIM_MAP.get(self.model)

    @property
    def dimension(self) -> int | None:
        return self.expected_dim

    async def embed(self, text: str) -> list[float]:
        """Embed a single string. Returns a float list."""
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty string.")

        response = await self._client.embed(model=self.model, input=text)
        vector: list[float] = response.embeddings[0]  # type: ignore[index]

        if self.expected_dim and len(vector) != self.expected_dim:
            logger.warning(
                "Embedding dimension mismatch: expected %d, got %d",
                self.expected_dim,
                len(vector),
            )
        return vector

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """
        Embed a list of strings in batches.
        Returns a list of float-vectors in the same order as input.
        """
        if not texts:
            return []

        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = [t.strip() for t in texts[i : i + batch_size] if t.strip()]
            if not batch:
                continue
            response = await self._client.embed(model=self.model, input=batch)
            all_vectors.extend(response.embeddings)  # type: ignore[arg-type]
            logger.debug("Embedded batch %d/%d", i + len(batch), len(texts))

        return all_vectors
