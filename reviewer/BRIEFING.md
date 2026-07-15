# Sellmo · Reviewer-Briefing

**Version:** 1.0 · 2026-07-15
**Für:** Externer Salesprofi + Kommunikationsexperte
**Zeitbedarf:** 20 Sessions × ~10 Min Review = ~3-4 Stunden pro Reviewer

---

## Was ist Sellmo?

Sellmo ist eine **KI-Trainings-Plattform für Einwandbehandlung im High-Ticket-Coaching-Vertrieb (DACH)**. Der User (ein Sales-Rep, „Closer") übt gegen eine KI-Persona, die einen realistischen Kunden spielt. Während des Trainings gibt eine zweite KI-Instanz („Phasen-Coach") methodische Hinweise und 3 Antwort-Optionen zur Auswahl. Nach Session-Ende bewertet eine dritte KI-Instanz („Feedback-Coach") die Session methodisch.

Die App befindet sich in Beta-Testing. Wir suchen **externe fachliche Absicherung** für zwei Fragen:

1. **Salesprofi**: Sind die Coach-Empfehlungen methodisch sauber? Wo bricht die Verkaufslogik?
2. **Kommunikationsexperte**: Klingen die Formulierungen wie natürliche Sales-Sprache oder wie ein wiederholendes KI-Skript?

Beide Fragen werden pro Session einzeln in einem Sheet dokumentiert (siehe `SESSION_REVIEW_TEMPLATE.csv`).

---

## Das methodische Fundament: EPISCH-Framework

Sellmo folgt einem Framework namens **SOHF (Sellmo Objection Handling Framework)**, das auf 6 Phasen basiert — abgekürzt **EPISCH**:

| Phase | Buchstabe | Name | Was passiert |
|---|---|---|---|
| 1 | **E** | Entschärfen | Druck rausnehmen. „Verstehe.", „Fair.", „Ok." — keine Argumente. |
| 2 | **P** | Präzisieren | Informationen vom Kunden holen. Kein Reframe, kein Widerspruch. |
| 3 | **I** | Isolieren | EINE Frage: „Geld/Zeit mal beiseite — würdest du es tun?" |
| 4 | **S** | Sichtweise | Frame-Challenge. Symptom→Problem-Reframes, Konsequenzen verstärken, Glaubenssätze brechen. |
| 5 | **C** | Commitment | Verantwortungs-Anker, explizite Verpflichtungs-Frage: „Bist du bereit, dich zu verpflichten?" |
| 6 | **H** | Handlung | Vertrag ankündigen, gemeinsam durchgehen — Kunde nie allein lassen. |

**Wichtigste Regel**: Kein Close vor Phase 5/6 ohne dass **Pain-Quantifizierung + Outcome-Quantifizierung + Selbst-Commitment** wörtlich vom Kunden belegt sind (Close-Gate).

---

## Die 4 Personas (FORM-Matrix)

Der Kunde-Typ variiert entlang zweier Achsen. Für das MVP relevante Kombination: **F-1, O-1, R-1, M-1** (Kooperativ + Kommunikations-Stil-Achse):

| Buchstabe | Name | Alter | Beruf | Kommunikations-Stil | Vertrauensmarker |
|---|---|---|---|---|---|
| **F** | Lukas | 34 | Selbständiger Solo-Berater | fokussiert, ROI-orientiert, direkt | Zahlen, Referenzen |
| **O** | Niklas | 29 | Sales-Aufsteiger | offen, vision-affin, Lifestyle | Success-Stories, Zukunftsbilder |
| **R** | Andreas | 41 | Vertriebs-Manager, Familie | ruhig, bedächtig, verlässlich | Sicherheit, Familien-Verträglichkeit |
| **M** | Sarah | 36 | Business-Consultant | methodisch, analytisch, präzise | Struktur, Belege, Komponenten |

Kunde stellt jeweils den gleichen Kern-Einwand: **„4.800€ sind eine Menge Geld"** — variiert in Ton und Framing pro Persona.

---

## Was der User (Closer) tut

1. Wählt Persona + Schwierigkeitsgrad im Setup-Screen
2. Chatet mit der Kunde-KI (Text)
3. Bekommt in der Easy-Variante 3 vorformulierte Antwort-Optionen: **A = richtig · B = fast richtig · C = falsch** (Lern-Pfad)
4. Klickt eine Option ODER tippt frei
5. Kunde-KI antwortet, Coach schlägt neue Optionen vor
6. Session endet nach 5-15 Runden, wenn Kunde `closed` oder `refused` signalisiert
7. Feedback-Coach liefert Auswertung: Score (0-100%), Stärken, Potenziale, Insight, Next-Level-Tipp

---

## Bekannte Schwachstellen, die wir dringend geprüft brauchen

Diese Punkte hat die interne Beta-Runde ergeben — wir wollen wissen, ob sie fundamental sind oder Symptome kleiner Prompt-Regel-Lücken:

1. **Zu früher Close**: Coach schlägt „Wärst du dabei?"-Fragen vor, bevor der Kunde substantiell committed hat.
2. **Halluzinierte Zitate**: Coach sagt „Du hast selbst gesagt X", obwohl X nie gesagt wurde.
3. **Turn-Widersprüche**: Coach empfiehlt in Runde N „keine Garantien", in Runde N+1 „bei garantiertem Ergebnis dabei?".
4. **Wording-Repetition**: „Du hast selbst gesagt", „Fair", „Mal angenommen" — begrenztes Repertoire, klingt nach Skript.
5. **Cross-Coach-Widerspruch**: Phasen-Coach markiert Option als RICHTIG, Feedback-Coach bewertet dieselbe Aktion als „methodisch fehlerhaft". (Prompt-Fix v2.6.3 sollte das clampen — bitte testen ob es greift.)
6. **Redundanz nach Kaufsignal**: Kunde sagt „wo unterschreibe ich" → Coach fragt trotzdem „Bist du bereit dich zu verpflichten?"

---

## Dein Review-Auftrag

**Für jede Session** (typischerweise 5-15 Runden) füllst du eine Zeile pro Runde im `SESSION_REVIEW_TEMPLATE.csv` aus. Wir liefern dir:

1. **Session-Log** als Markdown-Datei (oder DB-Export). Enthält: alle Kunde-/Closer-Moves, alle Coach-Empfehlungen (3 Optionen pro Runde), gewählte Option, Feedback-Coach-Bewertung.
2. **Session-ID + Persona + Schwierigkeitsgrad** in der Datei-Kopfzeile.

**Deine Aufgabe:**

- Salesprofi: pro Runde bewerten (`is_methodisch_ok`), Fehlertyp benennen wenn nicht, konkreten Alternativvorschlag notieren.
- Kommunikationsexperte: pro Runde `sprach_natuerlichkeit_score` (1-5) und `repetitions_marker` (welche Formel ist wieder aufgetaucht?).

**Zeit-Kalkulation:** ~10 Min pro Session bei geübtem Review. 20 Sessions in ~3.5 Stunden.

---

## Deliverable

- Ausgefülltes CSV (bitte NICHT umsortieren, wir mergen mehrere Reviewer-Files)
- Optional: 1-seitiges Meta-Feedback am Ende: „Die 3 Muster, die mir übergreifend aufgefallen sind."

Bei Rückfragen: Christian direkt (christian@sellmo.io).

**Wichtig:** Wir wollen **harte, ehrliche Kritik**. Was du nicht schreibst, können wir nicht fixen. Kein Beauty-Contest — Fokus auf methodisch bricht und/oder sprachlich unnatürlich.
