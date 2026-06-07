"""
CLI: Lesbarkeit von Texten vergleichen (deutscher Flesch / Amstad).

Beispiele (aus dem Verzeichnis Prototyp/ ausführen):

    # Mehrere Dateien vergleichen (Dateiname = Spaltenname):
    python scripts/eval_readability.py original_brief.txt medi_ausgabe.txt

    # Ohne Argumente: Demo am Korpus (Arztbrief vs. einfacher Diagnose-Text)
    python scripts/eval_readability.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.readability import compare, format_table  # noqa: E402

CORPUS = PROJECT_ROOT / "corpus"


def main(argv: list[str]) -> int:
    if argv:
        texts: dict[str, str] = {}
        for arg in argv:
            p = Path(arg)
            if not p.exists():
                print(f"Datei nicht gefunden: {p}", file=sys.stderr)
                return 1
            texts[p.name] = p.read_text(encoding="utf-8")
    else:
        # Demo: Original-Arztbrief vs. verständlicher Korpus-Text
        brief = CORPUS / "synthetische_arztbriefe" / "arztbrief-01-kardiologie.md"
        erklaert = CORPUS / "diagnosen" / "vorhofflimmern.md"
        if not brief.exists() or not erklaert.exists():
            print("Korpus-Dateien nicht gefunden — bitte Pfade als Argumente angeben.",
                  file=sys.stderr)
            return 1
        texts = {
            "Arztbrief (Original)": brief.read_text(encoding="utf-8"),
            "Diagnose-Erklärtext": erklaert.read_text(encoding="utf-8"),
        }
        print("(Demo ohne Argumente — eigene Dateien als Argumente übergeben.)\n")

    print(format_table(compare(texts)))
    print("\nHöherer Flesch-Wert = leichter lesbar. Ziel von Medi-Interpret: "
          "möglichst hoher Wert gegenüber dem Original.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
