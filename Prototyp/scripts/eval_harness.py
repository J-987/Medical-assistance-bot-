"""
End-to-End-Evaluations-Harness.

Schickt Beispiel-Befunde durch alle drei Erklär-Modi (einfach / standard /
detailliert), speichert die Antworten und misst die Lesbarkeit (deutscher
Flesch) jeweils gegen das Original. Ergebnis ist eine reproduzierbare
Vergleichstabelle — die Datengrundlage für die Evaluations-Folie.

Voraussetzungen (alles lokal):
  1. Weaviate läuft:            docker compose up -d
  2. Ollama läuft + Modelle:    ollama pull llama3.2 / nomic-embed-text
  3. Server läuft:              uvicorn main:app --port 8000
  4. Korpus indexiert:          python scripts/seed_corpus.py
     (damit die Befunde im Vektorspeicher liegen)

Aufruf (aus dem Verzeichnis Prototyp/):
    python scripts/eval_harness.py
    python scripts/eval_harness.py --base-url http://localhost:8000
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.readability import readability  # noqa: E402

CORPUS = PROJECT_ROOT / "corpus"
OUT_DIR = PROJECT_ROOT / "eval_outputs"
MODES = ["einfach", "standard", "detailliert"]

# Welche Befunde getestet werden und mit welcher Frage.
CASES = [
    {
        "label": "Kardiologie",
        "file": CORPUS / "synthetische_arztbriefe" / "arztbrief-01-kardiologie.md",
        "query": "Bitte erkläre mir die Diagnosen und das weitere Vorgehen aus "
                 "meinem kardiologischen Arztbrief.",
    },
    {
        "label": "Pneumologie",
        "file": CORPUS / "synthetische_arztbriefe" / "arztbrief-02-pneumologie.md",
        "query": "Bitte erkläre mir die Diagnosen und Empfehlungen aus meinem "
                 "Entlassbrief der Lungenklinik.",
    },
]


def _strip_markdown(text: str) -> str:
    """Markdown-Auszeichnung grob entfernen, damit die Lesbarkeit nur den
    eigentlichen Fließtext misst (keine #, |, * etc.)."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"[#>*_`|]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _post_chat(base_url: str, query: str, mode: str, top_k: int = 5) -> dict:
    payload = json.dumps({"query": query, "mode": mode, "top_k": top_k}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv: list[str]) -> int:
    base_url = "http://localhost:8000"
    if "--base-url" in argv:
        base_url = argv[argv.index("--base-url") + 1]

    OUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    run_dir = OUT_DIR / f"run_{stamp}"
    run_dir.mkdir(exist_ok=True)

    table_rows: list[str] = []
    all_ok = True

    for case in CASES:
        if not case["file"].exists():
            print(f"Befund nicht gefunden: {case['file']}", file=sys.stderr)
            all_ok = False
            continue

        original_raw = case["file"].read_text(encoding="utf-8")
        original_clean = _strip_markdown(original_raw)
        orig = readability(original_clean)
        print(f"\n=== {case['label']} ===")
        print(f"Original-Arztbrief:  Flesch {orig.flesch_de:>6.1f}  ({orig.level})")

        # Tabellenzeile: Original
        table_rows.append(
            f"| {case['label']} | Original-Arztbrief | "
            f"{orig.flesch_de:.1f} | {orig.level} |"
        )

        for mode in MODES:
            try:
                result = _post_chat(base_url, case["query"], mode)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "ignore")
                print(f"  [{mode}] HTTP {exc.code}: {detail}", file=sys.stderr)
                all_ok = False
                continue
            except urllib.error.URLError as exc:
                print(f"  [{mode}] Server nicht erreichbar ({exc.reason}). "
                      f"Läuft uvicorn auf {base_url}?", file=sys.stderr)
                return 1

            answer = result.get("answer", "")
            r = readability(_strip_markdown(answer))
            print(f"  Modus {mode:<12} Flesch {r.flesch_de:>6.1f}  ({r.level})")

            # Antwort speichern
            (run_dir / f"{case['label'].lower()}_{mode}.md").write_text(
                f"# {case['label']} — Modus: {mode}\n\n"
                f"**Frage:** {case['query']}\n\n"
                f"**Flesch:** {r.flesch_de} ({r.level})\n\n---\n\n{answer}\n",
                encoding="utf-8",
            )
            table_rows.append(
                f"| {case['label']} | Medi-Interpret ({mode}) | "
                f"{r.flesch_de:.1f} | {r.level} |"
            )

    # Markdown-Ergebnistabelle schreiben
    table = (
        f"# Evaluations-Ergebnis — Lesbarkeit (Flesch-DE)\n\n"
        f"Erzeugt am {datetime.now():%d.%m.%Y %H:%M} · Modell und Korpus lokal.\n\n"
        f"| Fall | Variante | Flesch-DE | Stufe |\n"
        f"|---|---|---|---|\n"
        + "\n".join(table_rows)
        + "\n\n*Höherer Flesch-Wert = leichter lesbar. Erwartung: deutlich "
          "höhere Werte in den Erklär-Modi als im Original-Arztbrief.*\n"
    )
    results_file = run_dir / "results.md"
    results_file.write_text(table, encoding="utf-8")

    print(f"\nErgebnisse gespeichert in: {run_dir}")
    print(f"Tabelle: {results_file}")
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
