# Medi-Interpret

**Verständliche Lesehilfe für medizinische Dokumente — lokal, datenschutzfreundlich, RAG-gegroundet.**

Medi-Interpret übersetzt Arztbriefe und Befunde in verständliche Sprache, passt
die Erklärtiefe an (Scaffolding) und bereitet auf das Arztgespräch vor. Es ist
**kein Diagnose-Werkzeug**, sondern eine kognitive Lesehilfe. Alle Verarbeitung
läuft lokal (Ollama + Weaviate), ohne Cloud.

## Funktionen

- **Drei Erklär-Modi** (Scaffolding, DP4–7): *Einfach* (A2, viele Analogien),
  *Standard* (B1, Fachbegriffe erklärt), *Detailliert* (Originalbegriffe + Tiefe).
- **RAG-gegroundete Antworten** aus geprüftem deutschem Korpus → weniger
  Halluzination, mit Quellenangabe.
- **Fragen-Checkliste fürs Arztgespräch** (`POST /chat/checklist`, DP11).
- **De-Identifizierung**: personenbezogene Daten werden vor dem Einbetten
  entfernt (Privacy by Design, DSGVO Art. 9).
- **Verifizierter Wissenskorpus**: Glossar, Diagnose-Erklärtexte, synthetische
  Arztbriefe (`corpus/`).
- **Evaluations-Werkzeuge**: deutsche Lesbarkeit (Flesch) und Cohen's κ.

## Schnellstart

```bash
# 1. Weaviate starten
docker compose up -d

# 2. Ollama-Modelle laden
ollama pull llama3.2
ollama pull nomic-embed-text

# 3. Python-Abhängigkeiten
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4. Konfiguration
cp .env.example .env

# 5. Server starten
uvicorn main:app --reload --port 8000
#    → http://localhost:8000/docs  (Swagger-UI)

# 6. Wissenskorpus indexieren (Grundwissen + Glossar)
python scripts/seed_corpus.py
```

## API

| Endpoint | Zweck |
|---|---|
| `POST /ingest` | Dokument hochladen (PDF/DOCX/Bild …), inkl. De-Identifizierung |
| `POST /chat` | RAG-Antwort; Feld `mode`: `einfach` \| `standard` \| `detailliert` |
| `POST /chat/stream` | Wie `/chat`, aber als Token-Stream (SSE) |
| `POST /chat/checklist` | Fragen-Checkliste fürs Arztgespräch |
| `GET /health` | Status von Ollama & Weaviate |

Beispiel:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Was bedeutet LVEF 48 %?", "mode": "einfach"}'
```

## Evaluation

```bash
# Lesbarkeit (deutscher Flesch) zweier Texte vergleichen
python scripts/eval_readability.py original.txt ausgabe.txt

# Inter-Rater-Übereinstimmung (Cohen's Kappa) aus ratings.csv
python scripts/eval_kappa.py ratings.csv --weights quadratic

# End-to-End: Befunde durch alle Modi + Lesbarkeit messen (Server muss laufen)
python scripts/eval_harness.py
```

Studien-Material für den Pilot: [`docs/evaluation/pilot-studie.md`](docs/evaluation/pilot-studie.md).

## Projektstruktur

```
app/
├── api/            # FastAPI-Routen (chat, ingest, health) + Schemas
├── domain/         # Enums (inkl. ExplainMode) & Datenmodelle
├── llm/            # Ollama-Client (Modi-Prompts) & Embeddings
├── ingestion/      # Pipeline, Loader, Chunking, De-Identifizierung
├── vectorstore/    # Weaviate-Anbindung
└── evaluation/     # Lesbarkeit (Flesch) & Cohen's Kappa
corpus/             # verifizierter Wissenskorpus (siehe corpus/README.md)
scripts/            # seed_corpus, eval_* (CLIs)
docs/evaluation/    # Pilot-Studienmaterial
```

## Hinweis

Medi-Interpret ersetzt keine ärztliche Beratung. Es werden ausschließlich
synthetische Beispieldaten verwendet; echte Patientendaten gehören nicht ins
Repository.
