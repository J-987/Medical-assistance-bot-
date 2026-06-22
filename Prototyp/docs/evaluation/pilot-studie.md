# Pilot-Evaluation — Medi-Interpret

Formative Mixed-Methods-Pilotstudie zur Verständlichkeit und zum subjektiven
Nutzen von Medi-Interpret. Kleine Stichprobe, **keine Inferenzstatistik** — Ziel
ist die formative Verbesserung (u. a. die optimale Default-Granularität) und ein
erster Beleg des Nutzens.

## 1. Ziel und Fragestellung

- **F1 (Verständlichkeit):** Sind die Erklärungen von Medi-Interpret messbar und
  subjektiv verständlicher als der Original-Arztbrief?
- **F2 (Unsicherheit):** Sinkt die subjektive Unsicherheit der Person nach der
  Nutzung?
- **F3 (Korrektheit):** Sind die Ausgaben medizinisch korrekt und ohne
  gefährliche Fehler (Bewertung durch Fachpersonen)?
- **F4 (Granularität):** Welcher Erklär-Modus wird als bester Default empfunden?

## 2. Design

Within-Subjects-Vergleich: Jede teilnehmende Person sieht denselben
(synthetischen) Befund einmal im Original und einmal als Medi-Interpret-Ausgabe.
Drei Datenquellen:

1. **Objektive Lesbarkeit** — automatisch (deutscher Flesch, `eval_harness.py`).
2. **Selbstauskunft der Zielgruppe** — Fragebogen (Abschnitt 4–6).
3. **Fachliche Bewertung** — zwei unabhängige Rater (Abschnitt 7).

## 3. Stichprobe und Ablauf

- **Zielgruppe:** Erwachsene ohne medizinische Ausbildung; angestrebt ca. 8–12
  Personen (formativ, nicht repräsentativ).
- **Rater:** 2 Personen mit medizinischem Hintergrund (z. B. Medizinstudium
  höheres Semester / Pflegefachkraft).
- **Ablauf je Teilnehmer:in (ca. 20 Min.):**
  1. Kurze Einführung, Einwilligung.
  2. Unsicherheit **vorher** erfassen (Abschnitt 5).
  3. Original-Befund lesen lassen.
  4. Medi-Interpret-Ausgabe (Modus „Einfach erklärt") lesen lassen; mit dem
     Chatbot frei interagieren, Fragen-Checkliste ansehen.
  5. Verständnis-Items beantworten (Abschnitt 4).
  6. Unsicherheit **nachher** + Verständlichkeits-Bewertung + Modus-Präferenz
     (Abschnitt 5–6).

## 4. Verständnis-Items (Beispiel zum Kardiologie-Befund)

Pro Item: richtig / teilweise / falsch. Misst tatsächliches Verständnis, nicht
nur das Gefühl, etwas verstanden zu haben.

1. Was bedeutet „Vorhofflimmern" in Ihren eigenen Worten?
2. Wofür ist das Medikament zur Blutverdünnung (Apixaban) gedacht?
3. Was ist mit „Reevaluation in 3 Monaten" gemeint?
4. Nennen Sie zwei Dinge, die Sie bei Ihrem nächsten Arzttermin ansprechen
   sollten.
5. Ist Medi-Interpret eine Diagnose? (Erwartete Antwort: nein — eine Lesehilfe.)

## 5. Unsicherheits-Selbsteinschätzung (vorher / nachher)

Skala 1–7 (1 = trifft gar nicht zu, 7 = trifft voll zu). Jeweils vor und nach
der Nutzung erheben; Differenz auswerten.

- U1: Ich verstehe, was in meinem Befund steht.
- U2: Ich weiß, was die nächsten Schritte für mich sind.
- U3: Ich fühle mich sicher genug, im Arztgespräch nachzufragen.
- U4: Ich bin beunruhigt wegen der Begriffe in meinem Befund. *(invertiert)*

## 6. Verständlichkeit & Modus-Präferenz (nachher)

- V1 (Skala 1–7): Die Erklärung war leicht zu verstehen.
- V2 (Skala 1–7): Die Erklärung war hilfreich für die Vorbereitung aufs
  Arztgespräch.
- V3: Welcher Modus war für Sie am besten? ☐ Einfach ☐ Standard ☐ Detailliert
- V4 (offen): Was war unklar oder hat gefehlt?

## 7. Rating-Bogen medizinische Korrektheit (für 2 Rater)

Jede Ausgabe unabhängig und verblindet bewerten (Skala 1–4):

| Stufe | Bedeutung |
|---|---|
| 4 | korrekt, vollständig, sicher |
| 3 | weitgehend korrekt, kleine Auslassung |
| 2 | teils ungenau, aber nicht gefährlich |
| 1 | fehlerhaft oder potenziell gefährlich |

Zusätzlich ja/nein: „Enthält die Ausgabe eine unzulässige Diagnose- oder
Therapieempfehlung?"

**Auswertung:** Die beiden Bewertungsreihen als CSV speichern
(`ratings.csv` mit Spalten `rater1,rater2`) und auswerten mit:

```bash
python scripts/eval_kappa.py ratings.csv --weights quadratic
```

Cohen's Kappa zeigt die Übereinstimmung der Rater (Landis & Koch: ab 0,61 =
„stark", ab 0,81 = „fast perfekt").

## 8. Auswertung im Überblick

| Frage | Methode | Werkzeug |
|---|---|---|
| F1 Verständlichkeit (objektiv) | Flesch vorher/nachher | `eval_harness.py` |
| F1/V Verständlichkeit (subjektiv) | Fragebogen V1–V2 | manuell |
| F2 Unsicherheit | U1–U4 Differenz vorher/nachher | manuell |
| F3 Korrektheit | Rating 1–4, 2 Rater | `eval_kappa.py` |
| F4 Granularität | Modus-Präferenz V3 | Häufigkeiten |

## 9. Ethik & Datenschutz

Nur **synthetische** Befunde verwenden (keine echten Patientendaten). Teilnahme
freiwillig und anonym, Einwilligung vor Beginn, jederzeitiger Abbruch möglich.
Es werden keine personenbezogenen Gesundheitsdaten erhoben.
