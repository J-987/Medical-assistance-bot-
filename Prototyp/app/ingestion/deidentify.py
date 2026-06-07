"""
De-Identifizierung für medizinische Dokumente (Privacy by Design, DSGVO Art. 9).

Entfernt personenbezogene Daten (PII) aus dem Rohtext, BEVOR er gechunkt,
eingebettet oder gespeichert wird. Regelbasiert (Regex) — bewusst ohne externe
NER-Abhängigkeit, damit der Schritt schnell und vollständig lokal läuft.

Wichtig: Es werden NUR identifizierende Angaben ersetzt (Namen, Geburtsdaten,
Patienten-/Versicherten-IDs, Kontaktdaten, Anschriften). Medizinischer Inhalt
— ICD-Codes, Laborwerte, Medikation, Dosierungen — bleibt erhalten, da er für
die Interpretation gebraucht wird.

Hinweis: Eine regelbasierte De-Identifizierung ist eine Schutzmaßnahme, keine
Garantie auf 100 % Vollständigkeit. Für den produktiven Einsatz sollte sie um
ein medizinisches NER-Modell (z. B. für freie Namensnennungen im Fließtext)
ergänzt werden.
"""

from __future__ import annotations

import re
from collections import Counter

# Reihenfolge ist relevant: spezifische Muster (E-Mail, Telefon, IDs) zuerst,
# damit sie nicht von allgemeineren Mustern (Datum) zerschnitten werden.

# ── Label-Felder (Wert hinter dem Doppelpunkt bis Zeilenende) ───────────────
# Typische Kopfzeilen in Arztbriefen / Entlassbriefen.
_LABEL_TOKENS: dict[str, str] = {
    r"Patient(?:in)?": "[NAME]",
    r"Name": "[NAME]",
    r"Vorname": "[NAME]",
    r"Nachname": "[NAME]",
    r"Geburtsdatum": "[GEBURTSDATUM]",
    r"Geb\.?-?\s?Datum": "[GEBURTSDATUM]",
    r"Patienten[-\s]?ID": "[PATIENTEN-ID]",
    r"Fallnummer": "[FALLNUMMER]",
    r"Versicherten[-\s]?(?:nummer|nr\.?)": "[VERSICHERTEN-NR]",
    r"Anschrift": "[ADRESSE]",
    r"Adresse": "[ADRESSE]",
    r"Telefon": "[TELEFON]",
    r"Tel\.?": "[TELEFON]",
    r"Behandler(?:in)?": "[NAME]",
}


def _label_pattern() -> re.Pattern[str]:
    labels = "|".join(_LABEL_TOKENS.keys())
    # Gruppe 1 = Label (für Token-Auswahl), Gruppe 2 = Wert bis Zeilenende.
    return re.compile(
        rf"(?im)^(\s*(?:{labels}))\s*[:\-]\s*(.+?)\s*$"
    )


_LABEL_RE = _label_pattern()
_LABEL_LOOKUP = [(re.compile(rf"(?i)^{lbl}$"), tok) for lbl, tok in _LABEL_TOKENS.items()]


def _token_for_label(label: str) -> str:
    label = label.strip()
    for rx, tok in _LABEL_LOOKUP:
        if rx.match(label):
            return tok
    return "[REDACTED]"


# ── Freitext-Muster (label-unabhängig) ──────────────────────────────────────
_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # E-Mail
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    # Telefon (nur mit Länder-/Ortskennung 0… oder +49, um Messwerte zu schonen)
    ("telefon", re.compile(r"(?<!\d)(?:\+49|0)[\d\s/\-()]{6,16}\d"), "[TELEFON]"),
    # Versichertennummer: 1 Buchstabe + 9 Ziffern (eGK)
    ("versicherten_nr", re.compile(r"\b[A-Z]\d{9}\b"), "[VERSICHERTEN-NR]"),
    # Patienten-/Fall-ID: z. B. HP-2026-003341
    ("patienten_id", re.compile(r"\b[A-Z]{1,4}-?\d{2,4}-\d{3,8}\b"), "[PATIENTEN-ID]"),
    # Vollständiges Datum DD.MM.YYYY oder DD.MM.YY
    ("datum", re.compile(r"\b\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})\b"), "[DATUM]"),
    # PLZ + Ort
    ("ort", re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:[-\s][A-ZÄÖÜ][a-zäöüß]+)*"), "[ORT]"),
    # Arzt-/Personennamen nach Titel (Titel bleibt erhalten, Name wird ersetzt)
    (
        "name_titel",
        re.compile(
            r"\b((?:Prof\.?\s*)?Dr\.?\s*(?:med\.?\s*)?)"
            r"[A-ZÄÖÜ][\wäöüß]+(?:\s+[A-ZÄÖÜ][\wäöüß]+){0,2}"
        ),
        r"\1[NAME]",
    ),
]


def deidentify(text: str) -> tuple[str, dict[str, int]]:
    """
    Entfernt PII aus ``text``.

    Returns ein Tupel ``(bereinigter_text, zaehler)``, wobei ``zaehler`` angibt,
    wie viele Ersetzungen je Kategorie vorgenommen wurden (für Logging/Audit).
    """
    counts: Counter[str] = Counter()

    # 1) Label-basierte Kopffelder zuerst (präziseste Treffer)
    def _label_sub(m: re.Match[str]) -> str:
        token = _token_for_label(m.group(1))
        counts["label_feld"] += 1
        return f"{m.group(1)}: {token}"

    text = _LABEL_RE.sub(_label_sub, text)

    # 2) Freitext-Muster in fester Reihenfolge
    for name, pattern, replacement in _PATTERNS:
        text, n = pattern.subn(replacement, text)
        if n:
            counts[name] += n

    return text, dict(counts)


if __name__ == "__main__":  # kleiner manueller Smoke-Test
    sample = (
        "Patient: Schmidt, Johann Karl\n"
        "Patienten-ID: HP-2026-003341\n"
        "Geburtsdatum: 14.03.1959\n"
        "Behandler: Dr. med. Karin Hoffmann\n"
        "Datum: 12.05.2026\n"
        "Beurteilung: Paroxysmales Vorhofflimmern (ICD-10 I48.0), Z. n. NSTEMI 2023. "
        "TTE: LVEF 48 %. Procedere: OAK mit Apixaban 5 mg 1-0-1, Reevaluation in 3 Monaten.\n"
        "Kontakt: 0151/23456789, praxis@example.de"
    )
    cleaned, stats = deidentify(sample)
    print(cleaned)
    print("\nErsetzungen:", stats)
