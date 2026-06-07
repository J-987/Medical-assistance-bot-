"""
Inter-Rater-Übereinstimmung — Cohen's Kappa.

Für die Evaluations-Dimension „medizinische Korrektheit" (Folie 18): Zwei
Fachpersonen bewerten die Medi-Interpret-Ausgaben unabhängig (Blind-Rating),
z. B. auf einer Skala 1–4. Cohen's Kappa misst, wie stark sie übereinstimmen —
bereinigt um die Übereinstimmung, die schon durch Zufall zustande käme.

    kappa = (p_o − p_e) / (1 − p_e)

    p_o = beobachtete Übereinstimmung
    p_e = zufällig erwartete Übereinstimmung

Reine Python-Implementierung (keine Abhängigkeiten). Unterstützt ungewichtetes
Kappa sowie linear/quadratisch gewichtetes Kappa für ordinale Skalen.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal, Sequence

Weights = Literal["unweighted", "linear", "quadratic"]


def _weight_matrix(k: int, scheme: Weights) -> list[list[float]]:
    """Gewichtsmatrix der Nicht-Übereinstimmung (0 = gleich, 1 = max. Distanz)."""
    if scheme == "unweighted":
        return [[0.0 if i == j else 1.0 for j in range(k)] for i in range(k)]
    denom = (k - 1) or 1
    if scheme == "linear":
        return [[abs(i - j) / denom for j in range(k)] for i in range(k)]
    if scheme == "quadratic":
        return [[((i - j) / denom) ** 2 for j in range(k)] for i in range(k)]
    raise ValueError(f"Unbekanntes Gewichtungsschema: {scheme}")


def cohens_kappa(
    rater1: Sequence,
    rater2: Sequence,
    weights: Weights = "unweighted",
) -> float:
    """
    Cohen's Kappa für zwei gleich lange Bewertungsreihen.

    rater1, rater2 : Listen kategorialer/ordinaler Bewertungen (gleiche Länge).
    weights        : "unweighted" | "linear" | "quadratic".

    Returns den Kappa-Wert (typ. −1.0 … 1.0).
    """
    if len(rater1) != len(rater2):
        raise ValueError("Beide Bewertungsreihen müssen gleich lang sein.")
    n = len(rater1)
    if n == 0:
        raise ValueError("Leere Bewertungsreihen.")

    categories = sorted(set(rater1) | set(rater2), key=str)
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)

    # Konfusionsmatrix
    observed = [[0 for _ in range(k)] for _ in range(k)]
    for a, b in zip(rater1, rater2):
        observed[idx[a]][idx[b]] += 1

    row_marg = [sum(observed[i]) for i in range(k)]
    col_marg = [sum(observed[i][j] for i in range(k)) for j in range(k)]

    w = _weight_matrix(k, weights)

    # Beobachtete und erwartete (gewichtete) NICHT-Übereinstimmung
    obs_dis = sum(
        w[i][j] * observed[i][j] for i in range(k) for j in range(k)
    ) / n
    exp_dis = sum(
        w[i][j] * row_marg[i] * col_marg[j] for i in range(k) for j in range(k)
    ) / (n * n)

    if exp_dis == 0:
        # Keine zufällig erwartete Uneinigkeit -> perfekte Definition
        return 1.0
    return 1.0 - obs_dis / exp_dis


# Interpretation nach Landis & Koch (1977)
_KAPPA_BANDS: list[tuple[float, str]] = [
    (0.81, "fast perfekt"),
    (0.61, "stark"),
    (0.41, "moderat"),
    (0.21, "ausreichend"),
    (0.01, "gering"),
    (float("-inf"), "keine / schlechter als Zufall"),
]


def interpret_kappa(kappa: float) -> str:
    """Kappa-Wert in eine verständliche Stufe übersetzen (Landis & Koch)."""
    for threshold, label in _KAPPA_BANDS:
        if kappa >= threshold:
            return label
    return "keine / schlechter als Zufall"


def load_ratings_csv(
    path: str | Path,
    col1: str | int = 0,
    col2: str | int = 1,
    has_header: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Bewertungen aus einer CSV laden. Standard: erste zwei Spalten = Rater 1 / 2.

    Spalten können per Name (bei Header) oder per Index angegeben werden.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = [r for r in reader if any(cell.strip() for cell in r)]

    if not rows:
        raise ValueError(f"Keine Daten in {path}.")

    start = 0
    if has_header:
        header = rows[0]
        start = 1
        if isinstance(col1, str):
            col1 = header.index(col1)
        if isinstance(col2, str):
            col2 = header.index(col2)

    r1 = [row[col1].strip() for row in rows[start:]]
    r2 = [row[col2].strip() for row in rows[start:]]
    return r1, r2


if __name__ == "__main__":  # Smoke-Test mit einem bekannten Beispiel
    # Zwei Rater bewerten 10 Ausgaben auf Skala 1–4 (med. Korrektheit).
    a = [4, 4, 3, 4, 2, 3, 4, 4, 3, 4]
    b = [4, 3, 3, 4, 2, 4, 4, 4, 3, 4]
    for scheme in ("unweighted", "linear", "quadratic"):
        kap = cohens_kappa(a, b, weights=scheme)  # type: ignore[arg-type]
        print(f"{scheme:>10}: kappa = {kap:.3f}  ({interpret_kappa(kap)})")
