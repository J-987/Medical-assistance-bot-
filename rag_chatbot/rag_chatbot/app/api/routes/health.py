from fastapi import APIRouter, Depends

from app.api.dependencies import get_embedder, get_llm, get_store
from app.api.schemas import HealthResponse
from app.config import get_settings

settings = get_settings()
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    store=Depends(get_store),
    llm=Depends(get_llm),
):
    ollama_ok = await llm.ping()
    try:
        count = store.count()
        weaviate_ok = True
    except Exception:
        count = -1
        weaviate_ok = False

    return HealthResponse(
        status="ok" if (ollama_ok and weaviate_ok) else "degraded",
        ollama_reachable=ollama_ok,
        weaviate_reachable=weaviate_ok,
        chunk_count=count,
        version=settings.app_version,
    )
