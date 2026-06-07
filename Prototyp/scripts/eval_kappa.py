"""
CLI: Inter-Rater-Übereinstimmung (Cohen's Kappa) auswerten.

Erwartet eine CSV mit zwei Spalten (Bewertungen von Rater 1 und Rater 2),
standardmäßig mit Kopfzeile. Beispiel-CSV (ratings.csv):

    rater1,rater2
    4,4
    4,3
    3,3
    ...

Aufruf (aus dem Verzeichnis Prototyp/):

    python scripts/eval_kappa.py ratings.csv
    python scripts/eval_kappa.py ratings.csv --weights quadratic

Ohne Argumente wird ein Demo-Datensatz ausgewertet.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.agreement import (  # noqa: E402
    cohens_kappa,
    interpret_kappa,
    load_ratings_csv,
)


def main(argv: list[str]) -> int:
    weights = "unweighted"
    if "--weights" in argv:
        i = argv.index("--weights")
        try:
            weights = argv[i + 1]
            del argv[i:i + 2]
        except IndexError:
            print("--weights braucht einen Wert: unweighted | linear | quadratic",
                  file=sys.stderr)
            return 1

    if argv:
        path = Path(argv[0])
        if not path.exists():
            print(f"CSV nicht gefunden: {path}", file=sys.stderr)
            return 1
        r1, r2 = load_ratings_csv(path)
        print(f"Geladen: {len(r1)} Bewertungspaare aus {path.name}\n")
    else:
        # Demo-Datensatz (Skala 1–4, med. Korrektheit)
        r1 = [4, 4, 3, 4, 2, 3, 4, 4, 3, 4]
        r2 = [4, 3, 3, 4, 2, 4, 4, 4, 3, 4]
        print("(Demo ohne Argumente — eigene CSV als Argument übergeben.)\n")

    try:
        kappa = cohens_kappa(r1, r2, weights=weights)  # type: ignore[arg-type]
    except ValueError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    print(f"Gewichtung: {weights}")
    print(f"Cohen's Kappa: {kappa:.3f}  ({interpret_kappa(kappa)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
