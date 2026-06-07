"""
Lesbarkeit deutscher Texte — Flesch-Reading-Ease (Amstad-Formel).

Misst, wie leicht ein Text zu lesen ist. Damit lässt sich objektiv zeigen, wie
stark Medi-Interpret die Verständlichkeit gegenüber dem Original-Arztbrief
erhöht (Evaluations-Dimension „Verständlichkeit", Folie 18).

Deutsche Flesch-Formel (Amstad, 1978):

    FRE = 180 − ASL − (58,5 × ASW)

    ASL = durchschnittliche Satzlänge (Wörter je Satz)
    ASW = durchschnittliche Wortlänge (Silben je Wort)

Höhere Werte = leichter lesbar (Skala grob 0–100, kann am Rand über-/
unterschreiten). Die Silbenzählung ist eine Heuristik über Vokalgruppen — für
Vergleichszwecke (Original vs. Ausgabe) ausreichend genau, aber keine perfekte
linguistische Silbentrennung.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

# Vokale inkl. Umlaute; aufeinanderfolgende Vokale zählen als EIN Silbenkern
# (Näherung für Diphthonge wie au, ei, eu, ie).
_VOWEL_GROUP = re.compile(r"[aeiouyäöü]+", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")
_SENTENCE_SPLIT = re.compile(r"[.!?]+(?:\s|$)")


@dataclass
class ReadabilityResult:
    flesch_de: float
    level: str
    n_sentences: int
    n_words: int
    n_syllables: int
    avg_sentence_length: float   # Wörter je Satz (ASL)
    avg_syllables_per_word: float  # Silben je Wort (ASW)

    def as_dict(self) -> dict:
        return asdict(self)


def count_syllables(word: str) -> int:
    """Silben eines Worts näherungsweise über Vokalgruppen zählen (min. 1)."""
    return max(1, len(_VOWEL_GROUP.findall(word)))


def _count_sentences(text: str) -> int:
    """Sätze über Satzendzeichen zählen; mindestens 1, wenn Text vorhanden."""
    parts = [p for p in _SENTENCE_SPLIT.split(text) if p.strip()]
    return max(1, len(parts))


# Interpretationsbänder (an die deutsche Flesch-Skala angelehnt).
_BANDS: list[tuple[float, str]] = [
    (90, "sehr leicht"),
    (80, "leicht"),
    (70, "mittelleicht"),
    (60, "mittel (Standard)"),
    (50, "mittelschwer"),
    (30, "schwer"),
    (float("-inf"), "sehr schwer (Fachsprache)"),
]


def interpret_flesch(score: float) -> str:
    """Lesbarkeitswert in eine verständliche Stufe übersetzen."""
    for threshold, label in _BANDS:
        if score >= threshold:
            return label
    return "sehr schwer (Fachsprache)"


def readability(text: str) -> ReadabilityResult:
    """Vollständige Lesbarkeitsanalyse eines Texts."""
    words = _WORD.findall(text)
    n_words = len(words)
    n_sentences = _count_sentences(text)

    if n_words == 0:
        return ReadabilityResult(0.0, "kein Text", n_sentences, 0, 0, 0.0, 0.0)

    n_syllables = sum(count_syllables(w) for w in words)
    asl = n_words / n_sentences
    asw = n_syllables / n_words
    fre = 180 - asl - 58.5 * asw

    return ReadabilityResult(
        flesch_de=round(fre, 1),
        level=interpret_flesch(fre),
        n_sentences=n_sentences,
        n_words=n_words,
        n_syllables=n_syllables,
        avg_sentence_length=round(asl, 2),
        avg_syllables_per_word=round(asw, 2),
    )


def compare(texts: dict[str, str]) -> dict[str, ReadabilityResult]:
    """
    Mehrere benannte Texte vergleichen, z. B.:

        compare({
            "Original-Arztbrief": brief_text,
            "Medi-Interpret (einfach)": ausgabe_einfach,
            "ChatGPT": chatgpt_text,
        })

    Returns ein Dict {Name: ReadabilityResult}.
    """
    return {name: readability(text) for name, text in texts.items()}


def format_table(results: dict[str, ReadabilityResult]) -> str:
    """Vergleich als einfache Texttabelle für die Konsole."""
    header = f"{'Text':<32} {'Flesch':>7} {'Stufe':<26} {'Ø Satz':>7} {'Ø Silben/Wort':>14}"
    lines = [header, "-" * len(header)]
    for name, r in results.items():
        lines.append(
            f"{name[:32]:<32} {r.flesch_de:>7.1f} {r.level:<26} "
            f"{r.avg_sentence_length:>7.1f} {r.avg_syllables_per_word:>14.2f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":  # Smoke-Test: Kontrast Fachsprache vs. einfache Sprache
    fachsprache = (
        "Paroxysmales Vorhofflimmern bei diastolischer Dysfunktion Grad I; "
        "Procedere: orale Antikoagulation, Betablocker-Titration, "
        "Reevaluation in drei Monaten."
    )
    einfach = (
        "Ihr Herz schlägt manchmal zu schnell und nicht im Takt. "
        "Das kommt und geht. Sie bekommen ein Mittel, das das Blut dünner macht. "
        "In drei Monaten schaut die Ärztin noch einmal nach Ihnen."
    )
    table = compare({
        "Arztbrief (Fachsprache)": fachsprache,
        "Medi-Interpret (einfach)": einfach,
    })
    print(format_table(table))
