# 🧠 Local RAG Chatbot

A fully **local, privacy-first** RAG (Retrieval-Augmented Generation) chatbot.
No cloud services required. All inference and storage run on your machine.

## Stack

| Layer | Tool | Why |
|---|---|---|
| **LLM** | [Ollama](https://ollama.com) | Local inference, any model |
| **Embeddings** | Ollama `nomic-embed-text` | 768-dim, fast, free |
| **PDF parsing** | Unstructured.io (local) + Marker + PyMuPDF | Multi-strategy, best quality |
| **Chunking** | LangChain RecursiveCharacterTextSplitter / SemanticChunker | Configurable |
| **Vector DB** | [Weaviate](https://weaviate.io) (Docker) | Local, fast, production-grade |
| **API** | FastAPI | Async, typed, OpenAPI docs |

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Docker (for Weaviate)
docker --version   # ≥ 24

# Ollama
curl -fsSL https://ollama.com/install.sh | sh

# System deps (Ubuntu/Debian)
sudo apt-get install -y poppler-utils tesseract-ocr libmagic1

# System deps (macOS)
brew install poppler tesseract libmagic
```

### 2. Pull Ollama models

```bash
ollama pull llama3.2           # chat model (~2 GB)
ollama pull nomic-embed-text   # embedding model (~270 MB)
```

### 3. Start Weaviate

```bash
docker compose up -d
# Verify: curl http://localhost:8080/v1/.well-known/ready
```

### 4. Install Python deps

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** `marker-pdf` downloads ~1 GB of models on first run.
> Set `MARKER_ENABLED=false` in `.env` to skip until you need it.

### 5. Configure

```bash
cp .env.example .env
# Edit .env if needed (defaults work out of the box)
```

### 6. Run the server

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## 📖 API Usage

### Ingest a PDF

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@my_document.pdf"
```

Response:
```json
{
  "job_id": "abc-123",
  "file_name": "my_document.pdf",
  "status": "completed",
  "total_chunks": 42,
  "duration_ms": 3200.0
}
```

### Chat (JSON)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main conclusion of the paper?", "top_k": 5}'
```

### Chat (streaming SSE)

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarise the methodology section", "stream": true}'
```

### Health check

```bash
curl http://localhost:8000/health
```

---

## 🗂 Project Structure

```
rag_chatbot/
├── main.py                        # Uvicorn entry point
├── docker-compose.yml             # Weaviate container
├── requirements.txt
├── .env.example
└── app/
    ├── config.py                  # All settings (pydantic-settings)
    ├── app.py                     # FastAPI factory + lifespan
    ├── domain/
    │   ├── enums.py               # LoaderType, ChunkStrategy, …
    │   └── models.py              # RawDocument, Chunk, RAGResponse, …
    ├── llm/
    │   ├── ollama_client.py       # Chat + streaming
    │   └── embeddings.py         # embed() / embed_batch()
    ├── vectorstore/
    │   └── weaviate_store.py      # CRUD + similarity search
    ├── ingestion/
    │   ├── pipeline.py            # Orchestrates load→chunk→embed→store
    │   ├── loaders/
    │   │   ├── base_loader.py     # ABC + file type detection
    │   │   ├── loader_router.py   # AUTO mode dispatcher
    │   │   ├── unstructured_loader.py
    │   │   ├── marker_loader.py
    │   │   └── pymupdf_loader.py
    │   └── chunking/
    │       └── semantic_chunker.py  # RECURSIVE / SEMANTIC / FIXED
    └── api/
        ├── dependencies.py        # FastAPI DI singletons
        ├── schemas.py             # Pydantic request/response models
        └── routes/
            ├── health.py
            ├── ingest.py
            └── chat.py
```

---

## ⚙️ Configuration

All config lives in `.env` (or environment variables):

| Variable | Default | Description |
|---|---|---|
| `CHAT_MODEL` | `llama3.2` | Ollama chat model |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `DEFAULT_LOADER` | `auto` | `auto` / `unstructured` / `marker` / `pymupdf` |
| `CHUNK_STRATEGY` | `recursive` | `recursive` / `semantic` / `fixed` |
| `CHUNK_SIZE` | `512` | Characters per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap between chunks |
| `TOP_K` | `5` | Chunks retrieved per query |
| `MARKER_ENABLED` | `true` | Use Marker for PDF → Markdown |

---

## 🔄 Loader Priority (AUTO mode)

```
PDF file
  └─ Marker (if MARKER_ENABLED=true)   ← best quality (layout, tables, equations)
       └─ Unstructured (hi_res)         ← good for most PDFs + OCR
            └─ PyMuPDF                  ← fast fallback (text-layer only)

DOCX / HTML / Image → Unstructured
TXT / Markdown → Unstructured (partition_text)
```

---

## 🧪 Dev Tips

```bash
# Reset the vector store (drops & recreates collection)
python -c "
from app.vectorstore.weaviate_store import WeaviateStore
s = WeaviateStore(); s.connect(); s.drop_schema(); s.close()
print('Dropped.')
"

# Switch to a lighter model for testing
CHAT_MODEL=phi3 uvicorn main:app --reload

# Use semantic chunking (slower but smarter)
CHUNK_STRATEGY=semantic uvicorn main:app --reload
```
