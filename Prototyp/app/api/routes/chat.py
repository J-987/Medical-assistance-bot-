"""
POST /chat
  Standard RAG response: retrieves relevant chunks, calls Ollama, returns JSON.

POST /chat/stream
  Same but streams tokens as Server-Sent Events (SSE).
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_embedder, get_llm, get_store
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChecklistRequest,
    ChecklistResponse,
    SourceDoc,
)
from app.config import get_settings
from app.domain.models import ChatMessage

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/chat", tags=["chat"])


def _build_history(request: ChatRequest) -> list[ChatMessage]:
    history = [ChatMessage(role=m["role"], content=m["content"]) for m in request.history]
    history.append(ChatMessage(role="user", content=request.query))
    return history


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store=Depends(get_store),
    embedder=Depends(get_embedder),
    llm=Depends(get_llm),
):
    """RAG chat — retrieve context then answer with Ollama."""
    t0 = time.perf_counter()

    # 1. Embed query
    query_vec = await embedder.embed(request.query)

    # 2. Retrieve
    hits = store.search(query_vector=query_vec, top_k=request.top_k)
    if not hits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant documents found. Please ingest some files first.",
        )

    # 3. Build system prompt from retrieved chunks (modusabhängig)
    context_texts = [h.chunk.text for h in hits]
    system_prompt = llm.build_rag_system_prompt(context_texts, request.mode)

    # 4. LLM generation
    history = _build_history(request)
    answer = await llm.chat(history, system_prompt=system_prompt)

    elapsed_ms = (time.perf_counter() - t0) * 1000

    sources = [
        SourceDoc(
            file_name=h.chunk.metadata.get("file_name", ""),
            page_number=h.chunk.page_number,
            chunk_index=h.chunk.chunk_index,
            score=round(h.score, 4),
            text_preview=h.chunk.text[:200],
        )
        for h in hits
    ]

    return ChatResponse(
        answer=answer,
        model_used=settings.chat_model.value,
        sources=sources,
        latency_ms=round(elapsed_ms, 1),
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    store=Depends(get_store),
    embedder=Depends(get_embedder),
    llm=Depends(get_llm),
):
    """Streaming RAG — returns SSE token stream."""
    query_vec = await embedder.embed(request.query)
    hits = store.search(query_vector=query_vec, top_k=request.top_k)
    if not hits:
        raise HTTPException(status_code=404, detail="No relevant documents found.")

    context_texts = [h.chunk.text for h in hits]
    system_prompt = llm.build_rag_system_prompt(context_texts, request.mode)
    history = _build_history(request)

    async def token_generator():
        # Send sources as first SSE event
        import json
        sources = [
            {
                "file_name": h.chunk.metadata.get("file_name", ""),
                "page": h.chunk.page_number,
                "score": round(h.score, 4),
            }
            for h in hits
        ]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        # Stream answer tokens
        async for token in llm.stream_chat(history, system_prompt=system_prompt):
            payload = json.dumps({"type": "token", "content": token})
            yield f"data: {payload}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@router.post("/checklist", response_model=ChecklistResponse)
async def chat_checklist(
    request: ChecklistRequest,
    store=Depends(get_store),
    embedder=Depends(get_embedder),
    llm=Depends(get_llm),
):
    """Generiert aus dem indexierten Befund eine Fragen-Checkliste fürs Arztgespräch."""
    t0 = time.perf_counter()

    query_vec = await embedder.embed(request.query)
    hits = store.search(query_vector=query_vec, top_k=request.top_k)
    if not hits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keine relevanten Dokumente gefunden. Bitte zuerst einen Befund hochladen.",
        )

    context_texts = [h.chunk.text for h in hits]
    system_prompt = llm.build_checklist_system_prompt(context_texts)

    history = [ChatMessage(role="user", content=request.query)]
    raw = await llm.chat(history, system_prompt=system_prompt)

    # Antwort in einzelne Fragen zerlegen
    questions = [
        line.lstrip("-•*0123456789. ").strip()
        for line in raw.splitlines()
        if line.strip()
    ]
    questions = [q for q in questions if q.endswith("?") or len(q) > 15]

    elapsed_ms = (time.perf_counter() - t0) * 1000

    sources = [
        SourceDoc(
            file_name=h.chunk.metadata.get("file_name", ""),
            page_number=h.chunk.page_number,
            chunk_index=h.chunk.chunk_index,
            score=round(h.score, 4),
            text_preview=h.chunk.text[:200],
        )
        for h in hits
    ]

    return ChecklistResponse(
        questions=questions,
        model_used=settings.chat_model.value,
        sources=sources,
        latency_ms=round(elapsed_ms, 1),
    )
