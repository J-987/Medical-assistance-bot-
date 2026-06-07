"""
Thin async wrapper around the Ollama Python SDK for chat completions.
Supports streaming and non-streaming modes with conversation history.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import ollama

from app.config import get_settings
from app.domain.enums import ExplainMode
from app.domain.models import ChatMessage

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Erklär-Modi (Scaffolding, DP4–7) ───────────────────────────────────────
# Jede Stufe regelt das Hilfe-Level analog zur Zone of Proximal Development.

_MODE_INSTRUCTIONS: dict[ExplainMode, str] = {
    ExplainMode.EINFACH: (
        "MODUS: EINFACH ERKLÄRT (maximale Unterstützung).\n"
        "- Schreibe auf Sprachniveau A2: sehr kurze Sätze, nur Alltagswörter.\n"
        "- Übersetze JEDEN Fachbegriff sofort in einfache Sprache; nutze viele "
        "Analogien aus dem Alltag.\n"
        "- Erkläre lieber etwas mehr und langsamer. Keine Abkürzungen ohne Erklärung."
    ),
    ExplainMode.STANDARD: (
        "MODUS: STANDARD (Default).\n"
        "- Schreibe auf Sprachniveau B1: klare, mittellange Sätze.\n"
        "- Nenne den Fachbegriff und erkläre ihn direkt dahinter in Klammern.\n"
        "- Strukturiere jede Aussage als: Was steht da? · Was bedeutet das? · "
        "Was kann ich tun / fragen?"
    ),
    ExplainMode.DETAILLIERT: (
        "MODUS: DETAILLIERT (geringe Unterstützung, mehr Tiefe).\n"
        "- Behalte die medizinischen Originalbegriffe bei und ergänze eine "
        "präzise Erklärung.\n"
        "- Gib mehr Hintergrund und Zusammenhänge.\n"
        "- Mache Quellenangaben (Dateiname/Abschnitt) im Text sichtbar."
    ),
}

# Gemeinsame Leitplanken für ALLE Modi (DP1–3, DP9, DP10, „kein Diagnosetool").
_BASE_RULES = (
    "Du bist „Medi-Interpret“, eine verständliche Lesehilfe für medizinische "
    "Dokumente (z. B. Arztbriefe, Befunde). Du bist KEIN Diagnose-Werkzeug und "
    "gibst KEINE Therapieempfehlung. Du übersetzt und erklärst, damit die Person "
    "ihr eigenes Dokument versteht und sich aufs Arztgespräch vorbereiten kann.\n\n"
    "FESTE REGELN:\n"
    "1. Antworte immer auf Deutsch.\n"
    "2. Nutze AUSSCHLIESSLICH den unten stehenden KONTEXT. Erfinde nichts.\n"
    "3. Wenn der Kontext etwas nicht hergibt, sage klar: „Dazu steht in deinem "
    "Dokument nichts Eindeutiges.“ Spekuliere nicht.\n"
    "4. Mache Unsicherheiten transparent und weise bei Bedeutung-für-mich-Fragen "
    "darauf hin, das mit der Ärztin/dem Arzt zu klären.\n"
    "5. Stelle keine Diagnose und sprich keine Behandlung aus.\n"
)


def build_rag_system_prompt(
    context_chunks: list[str],
    mode: ExplainMode = ExplainMode.STANDARD,
) -> str:
    """Baut den modusabhängigen, deutschen RAG-System-Prompt."""
    context = "\n\n---\n\n".join(context_chunks)
    mode_block = _MODE_INSTRUCTIONS.get(mode, _MODE_INSTRUCTIONS[ExplainMode.STANDARD])
    return (
        f"{_BASE_RULES}\n{mode_block}\n\n"
        f"KONTEXT (Auszüge aus dem Dokument der Person):\n{context}"
    )


def build_checklist_system_prompt(context_chunks: list[str]) -> str:
    """Prompt für die Fragen-Checkliste fürs Arztgespräch (DP11, „Apply“)."""
    context = "\n\n---\n\n".join(context_chunks)
    return (
        f"{_BASE_RULES}\n"
        "AUFGABE: Erstelle aus dem KONTEXT eine personalisierte Fragen-Checkliste "
        "für das nächste Arztgespräch. Formuliere 5–8 konkrete Fragen, die die "
        "Person ihrer Ärztin/ihrem Arzt stellen kann, um Unklarheiten zu klären "
        "und ihre Behandlung zu verstehen.\n"
        "FORMAT: Gib NUR die Fragen aus, eine pro Zeile, jeweils mit „- “ "
        "beginnend, ohne Einleitung und ohne Schlusssatz. Verständliche Sprache.\n\n"
        f"KONTEXT:\n{context}"
    )


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
    def build_rag_system_prompt(
        context_chunks: list[str],
        mode: ExplainMode = ExplainMode.STANDARD,
    ) -> str:
        """Modusabhängiger deutscher RAG-Prompt (siehe Modulfunktion)."""
        return build_rag_system_prompt(context_chunks, mode)

    @staticmethod
    def build_checklist_system_prompt(context_chunks: list[str]) -> str:
        """Prompt für die Fragen-Checkliste fürs Arztgespräch."""
        return build_checklist_system_prompt(context_chunks)
