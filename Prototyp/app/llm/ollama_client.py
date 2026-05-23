"""
Thin async wrapper around the Ollama Python SDK for chat completions.
Supports streaming and non-streaming modes with conversation history.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import ollama

from app.config import get_settings
from app.domain.models import ChatMessage

logger = logging.getLogger(__name__)
settings = get_settings()


def _to_ollama_messages(history: list[ChatMessage]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in history]


class OllamaClient:
    """Async Ollama chat client."""

    def __init__(self) -> None:
        self._client = ollama.AsyncClient(host=settings.ollama_base_url)
        self.model = settings.chat_model.value

    # ── Health ────────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Return True if Ollama is reachable and the model is available."""
        try:
            models = await self._client.list()
            available = [m.model for m in models.models]
            if self.model not in available and not any(
                self.model in m for m in available
            ):
                logger.warning(
                    "Model '%s' not found locally. Pull it with: ollama pull %s",
                    self.model,
                    self.model,
                )
            return True
        except Exception as exc:
            logger.error("Ollama unreachable: %s", exc)
            return False

    # ── Completion ────────────────────────────────────────────────────────

    async def chat(
        self,
        history: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> str:
        """Single-shot completion. Returns the full assistant reply."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(_to_ollama_messages(history))

        response = await self._client.chat(
            model=self.model,
            messages=messages,
            options={
                "num_ctx": settings.ollama_num_ctx,
                "temperature": 0.2,
            },
        )
        return response.message.content  # type: ignore[union-attr]

    async def stream_chat(
        self,
        history: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens as they arrive. Yields delta strings."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(_to_ollama_messages(history))

        async for chunk in await self._client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options={
                "num_ctx": settings.ollama_num_ctx,
                "temperature": 0.2,
            },
        ):
            delta = chunk.message.content  # type: ignore[union-attr]
            if delta:
                yield delta

    # ── RAG system prompt ─────────────────────────────────────────────────

    @staticmethod
    def build_rag_system_prompt(context_chunks: list[str]) -> str:
        context = "\n\n---\n\n".join(context_chunks)
        return (
            "You are a helpful assistant. Answer the user's question using ONLY "
            "the provided context below. If the context does not contain enough "
            "information, say so clearly. Do not make up facts.\n\n"
            f"CONTEXT:\n{context}"
        )
