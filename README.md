# Sellmo · MVP Trainings-App · Einwandbehandlung Textform

> **Zweck:** Funktionierender Trainings-Prototyp, mit dem Christian Einwandbehandlung in Textform üben kann.
> **Stack:** Python + Streamlit + Anthropic Claude API
> **Architektur:** Single-Mac, lokal, kein Deploy, keine Auth, keine Persistenz über Sessions hinaus
> **Status:** in Entwicklung · 2026-05-19 abends · v0.1-Skelett
> **Sprache:** Deutsch (für DACH-Beachhead)

---

## Pivot-Schutz · Wie du jederzeit zurück kannst

Diese MVP-App ist bewusst **räumlich isoliert** vom methodischen Sellmo-Material. Alles in diesem Ordner (`SELLMO/MVP_App/`) ist disposable. Die methodische Arbeit liegt in `SELLMO/Einwandbehandlung/` und ist davon nicht abhängig.

**Wenn du den MVP-Pfad verlassen willst, gehst du zurück zu:**

| Methodik-Pfad | Asset | Wo |
|---|---|---|
| **Persona-Definition aus 9 Real-World-Calls** | nicht-gestartet — Vera's 5-Schritt-Plan im Chat | (Chat-History 2026-05-19) |
| **SOHF v1.6 mit Hard-Persona-Validierung** | wartet auf DACH-Calls / Stolzer/Wütender-Real-World | `Einwandbehandlung/SOHF_Muster_Kandidaten.md` |
| **Sprint 3 Backend** | Brief liegt freigabe-bereit | `SELLMO/SPRINT3_Backend_Brief_v1.0.md` |
| **Layer-1-Prompt v0.4** (Stolzer-Tuning) | wartet auf nächste Iteration | `Einwandbehandlung/SOHF_PromptStub_Layer1_v0.3.md` + v0.7-Script |
| **Whitepaper-Distribution** | DOCX + MD liegen freigabe-bereit | `Einwandbehandlung/SELLMO_Whitepaper_v1.0_Anatomie-eines-Closings.{md,docx}` |

**Wenn der MVP morgen abgebrochen wird:** kein methodisches Asset wurde geändert. Diesen ganzen Ordner kannst du archivieren oder löschen, ohne dass irgendwas in `Einwandbehandlung/` betroffen ist.

---

## Status-Block (immer aktualisieren beim Pausieren)

**Zuletzt funktioniert:** v0.2 komplett. Alle 4 Pfad-A-Features eingebaut: Rollen-Wahl (Closer/Customer), Persona-Auswahl statt zufällig, Schwierigkeitsgrade (EASY/MEDIUM/HARD) mit Phasen-Coach-Schicht, Phasen-Leiste in der Sidebar. Streamlit-Theming nach Design-Brief v1.0 (Dark-Mode + Sellmo-Orange). Backup von v0.1 als `app_v0.1_backup.py` gesichert. (2026-05-20)
**Was offen ist:** (1) Erst-Start-Test der v0.2-Version. (2) Streamlit-Cloud-Deploy für Felix auf dem Handy. (3) Customer-Modus-Tuning (Closer-Bot ist noch nicht stark getestet).
**Nächster Schritt beim Wiedereinstieg:** App starten und testen — siehe „Start-Anleitung" oben.

## Datei-Übersicht v0.2

| Datei | Zweck |
|---|---|
| `README.md` | Pivot-Schutz + Status (dieses Dokument) |
| `app.py` | Streamlit-App v0.2 (Single-File) |
| `app_v0.1_backup.py` | Backup der v0.1-Version (vor Pfad-A-Erweiterung) |
| `requirements.txt` | Python-Dependencies |
| `personas.json` | 9 Real-World-Persona-Profile |
| `customer_bot_prompt.md` | KI als Customer |
| `feedback_coach_prompt.md` | SOHF v1.5-Bewertung |
| `phasen_coach_prompt.md` | Phasen-Hinweise + 3-Klick-Optionen (EASY/MEDIUM) |
| `closer_bot_prompt.md` | KI als Closer (Customer-Modus) |
| `.streamlit/config.toml` | Streamlit-Theming |

---

## Start-Anleitung (sobald Skelett liegt)

```bash
cd "/Users/christianhafner/Documents/02 - Projekte/SELLMO/MVP_App"
pip install -r requirements.txt
ANTHROPIC_API_KEY="$(cat ~/.sellmo_api_key)" python3 -m streamlit run app.py
```

App öffnet sich auf `http://localhost:8501`.

---

## Datei-Übersicht

| Datei | Zweck |
|---|---|
| `README.md` | dieses Dokument |
| `app.py` | Streamlit-App (Single-File) |
| `requirements.txt` | Python-Dependencies |
| `customer_bot_prompt.md` | SYSTEM-Prompt für die Customer-KI |
| `feedback_coach_prompt.md` | SYSTEM-Prompt für die Feedback-Coach-KI |
| `personas.json` | 9 Real-World-Persona-Profile (zufällige Auswahl in der App) |

---

## Architektur-Konzept

```
Du als Closer (Browser)
   ↕ Chat-UI
Streamlit-App (lokal · localhost:8501)
   ↕ session state
Anthropic API:
   - Customer-Bot (Persona aus personas.json)
   - Feedback-Coach (live + end-of-call Modi)
```

**Session-Flow:**
1. Du startest die App.
2. App zieht zufällig 1 Persona aus dem Pool.
3. Customer-Bot eröffnet mit dem Einwand der Persona.
4. Du tippst deine Closer-Antwort.
5. Feedback-Coach (live oder am Ende) gibt SOHF-Bewertung.
6. Customer-Bot antwortet auf deine Closer-Aussage realistisch.
7. Loop bis Close oder Abbruch.
8. End-of-Call-Report: Phase-Verlauf, Muster-Verwendung, methodische Hinweise.

---

## Was bewusst NICHT im MVP ist

- Voice (kommt in Sprint 4)
- Mobile-App
- Multi-User / Auth
- Session-Persistenz über App-Restart hinaus
- DSGVO-Compliance-Schicht (lokal-only, keine Customer-Daten)
- Cost-Tracking-UI (steht im Code, aber nicht angezeigt)
- Closed-Alpha-Mehrnutzer-Fähigkeit
- Persistente History / Statistik-Historie

Diese Features kommen alle in Sprint 3 NestJS-Backend. MVP ist „ich kann üben", nicht „mehrere Closer können üben".
