from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.dependencies import get_store, get_llm
from app.api.routes import chat, health, ingest
from app.config import get_settings
settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    store = get_store()
    logger.info("Weaviate connected - %d chunks in store.", store.count())
    llm = get_llm()
    ok = await llm.ping()
    if not ok:
        logger.warning("Ollama not reachable at %s", settings.ollama_base_url)
    yield
    store.close()
def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(chat.router)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    @app.get("/")
    async def serve_ui():
        return FileResponse("static/index.html")
    return app
