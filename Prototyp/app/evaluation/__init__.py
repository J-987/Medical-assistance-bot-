"""
Evaluation — objektive Metriken zur Belegung des Nutzens von Medi-Interpret.

Module:
  - readability: deutsche Lesbarkeit (Flesch/Amstad) — Verständlichkeit messen.
  - agreement:   Cohen's Kappa — Inter-Rater-Übereinstimmung (med. Korrektheit).

Beide Module sind reine Python-Logik ohne externe Abhängigkeiten und lassen
sich unabhängig vom laufenden Server (Ollama/Weaviate) ausführen und testen.
"""

from app.evaluation.agreement import cohens_kappa, interpret_kappa
from app.evaluation.readability import compare, interpret_flesch, readability

__all__ = [
    "readability",
    "interpret_flesch",
    "compare",
    "cohens_kappa",
    "interpret_kappa",
]
