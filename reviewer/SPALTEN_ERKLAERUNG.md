# Spalten-Erklärung · SESSION_REVIEW_TEMPLATE.csv

| Spalte | Wer füllt aus | Was rein |
|---|---|---|
| `session_id` | (vorausgefüllt) | Timestamp aus Session-Log-Dateiname |
| `persona` | (vorausgefüllt) | F / O / R / M |
| `schwierigkeit` | (vorausgefüllt) | 1 (Kooperativ) bis 5 (Endgegner) |
| `runde` | (vorausgefüllt) | 1..N |
| `kunde_move_kurz` | (vorausgefüllt) | 1 Zeile Zusammenfassung dessen was der Kunde sagte |
| `coach_hint_kurz` | (vorausgefüllt) | 1 Zeile methodischer Hinweis des Phasen-Coach |
| `user_wahl` | (vorausgefüllt) | A (richtig) / B (fast richtig) / C (falsch) / free (frei getippt) |
| `user_text_kurz` | (vorausgefüllt) | die tatsächliche Antwort des Users |
| **`is_methodisch_ok`** | **Salesprofi** | JA / NEIN — war die gewählte Antwort methodisch sauber im Kontext? |
| **`fehler_typ`** | **Salesprofi** | Wenn NEIN: einer von — `close_gate` (zu früh in P5/P6), `halluzination` (Zitat existiert nicht), `turn_widerspruch` (widerspricht früherer Coach-Empfehlung), `redundanz` (wiederholt was Kunde bereits sagte oder was Coach schon einmal empfahl), `phasen_sprung` (springt Phase über), `keiner` (methodisch ok), `anderes` (dann in `kommentar` erklären) |
| **`alternativ_vorschlag`** | **Salesprofi** | Wenn NEIN: was hätte gepasst? 1-2 Sätze Formulierungs-Vorschlag |
| **`sprach_natuerlichkeit_1_5`** | **Kommunikationsexperte** | 1 = klingt wie Skript / KI-Auto-Pilot · 5 = klingt wie ein erfahrener Sales-Rep |
| **`repetitions_marker`** | **Kommunikationsexperte** | Welche Formeln sind wieder aufgetaucht? Beispiele: „Du hast selbst gesagt", „Fair", „Mal angenommen", „wärst du dabei". Komma-getrennt, leer wenn nichts. |
| `kommentar` | beide | Freitext, optional. Alles, was in keine Spalte passt. |

## Wie einlesen in Excel/Numbers/Google Sheets

- **Google Sheets**: File → Import → Upload → CSV. Trennzeichen: Komma. Text-Zeichen: Doppel-Anführungszeichen.
- **Excel**: Daten → Aus Text/CSV → Datei wählen → UTF-8, Komma-getrennt.
- **Numbers**: Datei einfach mit Doppelklick öffnen.

## Beim Ausfüllen

- Nicht die Spalten-Reihenfolge ändern — wir mergen mehrere Reviewer-Files am Ende automatisch.
- Neue Zeilen einfach anhängen.
- `session_id`-Spalte pro Session gleich lassen, `runde` inkrementieren.
- Wenn eine Session nichts Auffälliges hat: trotzdem eine Zeile pro Runde füllen, `is_methodisch_ok = JA` und `sprach_natuerlichkeit_1_5 = 4` oder `5`. Auch „passt" ist ein wertvolles Datum.
