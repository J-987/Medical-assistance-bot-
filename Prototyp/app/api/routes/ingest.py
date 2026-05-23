"""
POST /ingest
  Upload a file (PDF / DOCX / HTML / TXT / image).
  Runs the full ingest pipeline and returns an IngestResponse.

DELETE /ingest/{doc_id}
  Remove all chunks for a given doc_id from the vector store.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.schemas import DeleteResponse, IngestResponse, StatsResponse
from app.config import get_settings
from app.domain.enums import LoaderType
from app.ingestion.pipeline import IngestionPipeline
from app.api.dependencies import get_pipeline, get_store

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/ingest", tags=["ingestion"])

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".htm",
                      ".png", ".jpg", ".jpeg", ".tiff", ".webp"}


@router.post("", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_file(
    file: UploadFile = File(...),
    loader: LoaderType = Query(LoaderType.AUTO, description="Force a specific loader"),
    pipeline: IngestionPipeline = Depends(get_pipeline),
):
    """Upload and ingest a document into the vector store."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Save upload to disk
    dest = UPLOAD_DIR / file.filename
    t0 = time.perf_counter()
    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        await file.close()

    logger.info("Received file: %s (%.1f KB)", file.filename, dest.stat().st_size / 1024)

    # Run pipeline
    job = await pipeline.ingest(dest, loader_override=loader)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return IngestResponse(
        job_id=job.job_id,
        file_name=job.file_name,
        status=job.status.value,
        total_chunks=job.total_chunks,
        error=job.error,
        duration_ms=round(elapsed_ms, 1),
    )


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    store=Depends(get_store),
):
    """Delete all vector chunks associated with a document ID."""
    deleted = store.delete_document(doc_id)
    return DeleteResponse(doc_id=doc_id, deleted_chunks=deleted)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(store=Depends(get_store)):
    """Return total chunk count in the vector store."""
    return StatsResponse(
        total_chunks=store.count(),
        weaviate_class=settings.weaviate_class_name,
    )
