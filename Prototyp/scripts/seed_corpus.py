"""
Seed-Skript — indexiert den verifizierten Korpus in die Vektor-Datenbank.

Lädt alle Markdown-Dateien aus ``corpus/`` über die normale Ingest-Pipeline
(inkl. De-Identifizierung, Chunking, Embedding, Speicherung in Weaviate).
Dadurch hat Medi-Interpret Grundwissen (Glossar, Diagnose-Erklärtexte,
Beispiel-Arztbriefe), bevor die Nutzerin oder der Nutzer eigene Dokumente
hochlädt.

Voraussetzungen (siehe Haupt-README):
  - Weaviate läuft (docker compose up -d)
  - Ollama läuft und die Modelle sind geladen

Ausführen aus dem Verzeichnis ``Prototyp/``:
    python scripts/seed_corpus.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Projekt-Wurzel (Prototyp/) importierbar machen, egal von wo gestartet wird.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.api.dependencies import get_pipeline, get_store  # noqa: E402
from app.domain.enums import IngestStatus  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
logger = logging.getLogger("seed_corpus")

CORPUS_DIR = PROJECT_ROOT / "corpus"


def _collect_files() -> list[Path]:
    """Alle .md-Dateien im Korpus einsammeln (README ausgenommen)."""
    files = sorted(
        p for p in CORPUS_DIR.rglob("*.md")
        if p.name.lower() != "readme.md"
    )
    return files


async def main() -> int:
    if not CORPUS_DIR.exists():
        logger.error("Korpus-Verzeichnis nicht gefunden: %s", CORPUS_DIR)
        return 1

    files = _collect_files()
    if not files:
        logger.error("Keine Korpus-Dateien (*.md) in %s gefunden.", CORPUS_DIR)
        return 1

    logger.info("Indexiere %d Korpus-Dateien aus %s …", len(files), CORPUS_DIR)

    pipeline = get_pipeline()
    store = get_store()

    ok, failed = 0, 0
    total_chunks = 0
    try:
        for path in files:
            rel = path.relative_to(CORPUS_DIR)
            job = await pipeline.ingest(path)
            if job.status == IngestStatus.COMPLETED:
                ok += 1
                total_chunks += job.total_chunks
                logger.info("  ✅ %s — %d Chunks", rel, job.total_chunks)
            else:
                failed += 1
                logger.error("  ❌ %s — %s", rel, job.error)
    finally:
        store.close()

    logger.info(
        "Fertig: %d erfolgreich, %d fehlgeschlagen, %d Chunks gesamt.",
        ok, failed, total_chunks,
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
