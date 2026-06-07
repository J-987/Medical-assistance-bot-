# Verifizierter Korpus — Medi-Interpret

Dieser Ordner enthält das **Grundwissen**, das Medi-Interpret beim Start in die
Vektor-Datenbank lädt. Dadurch kann der Chatbot Fachbegriffe erklären und
Diagnosen einordnen, auch bevor die Nutzerin oder der Nutzer ein eigenes
Dokument hochlädt — und die RAG-Antworten sind an geprüfte Inhalte gebunden
(weniger Halluzination).

## Herkunft & Rechtliches (wichtig)

Die Inhalte in `glossar.md` und `diagnosen/` sind **eigenständig formuliert**.
Sie beruhen fachlich auf den frei zugänglichen, qualitätsgesicherten
Patienteninformationen von:

- **IQWiG / gesundheitsinformation.de** — https://www.gesundheitsinformation.de
- **gesund.bund.de** (Bundesministerium für Gesundheit) — https://gesund.bund.de

Diese Quellen erlauben das **Zitieren und Verlinken**, aber **keine
vollständige Übernahme** ihrer Texte. Deshalb sind die Texte hier in eigenen
Worten geschrieben (Fakten sind nicht urheberrechtlich geschützt, die konkrete
Formulierung schon) und verweisen jeweils auf die Originalquelle zum Weiterlesen.

Die Dateien in `synthetische_arztbriefe/` sind **frei erfunden**. Namen,
Daten und Befunde sind fiktiv; jede Ähnlichkeit mit realen Personen ist
zufällig. Es werden **keine** echten Patientendaten (z. B. MIMIC) verwendet.

## Wichtiger Hinweis

Medi-Interpret ist eine **verständliche Lesehilfe**, kein Diagnose-Werkzeug.
Diese Texte ersetzen keine ärztliche Beratung.

## Aufbau

```
corpus/
├── glossar.md                      # häufige Fachbegriffe aus Arztbriefen
├── diagnosen/                      # verständliche Erklärtexte zu Diagnosen
│   ├── vorhofflimmern.md
│   ├── diabetes-typ-2.md
│   ├── copd.md
│   └── bluthochdruck.md
└── synthetische_arztbriefe/        # fiktive Demo-/Testdaten
    ├── arztbrief-01-kardiologie.md
    └── arztbrief-02-pneumologie.md
```

## Indexieren

Mit laufendem Ollama + Weaviate (siehe Haupt-README):

```bash
python scripts/seed_corpus.py
```

Das Skript lädt alle Dateien über die normale Ingest-Pipeline (inkl.
De-Identifizierung und Chunking) in die Vektor-Datenbank.
