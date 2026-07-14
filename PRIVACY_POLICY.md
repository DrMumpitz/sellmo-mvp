# Sellmo · Datenschutz-Hinweise · Closed-Alpha

> **Stand:** 2026-05-23 · v1.0
> **Verantwortlich:** Christian Hafner, Sellmo (Sales-Founder)
> **Kontakt:** christian@sellmo.io
> **Phase:** Closed-Alpha · max. 50 Beta-Tester · DACH-Closer-Community

---

## 1 · Welche Daten verarbeiten wir?

Während du Sellmo nutzt, verarbeiten wir:

| Kategorie | Inhalt | Zweck |
|---|---|---|
| **Account-Daten** | E-Mail, Name, gehashtes Passwort (bcrypt) | Login + User-Identifikation |
| **Trainings-Sessions** | Deine eingegebenen Closer-/Customer-Aussagen, KI-Antworten, gewählte Persona, methodisches Feedback | Service-Bereitstellung + Methodik-Validierung |
| **Cost-Tracking** | Anzahl Turns, geschätzte API-Kosten pro Session | Faire Nutzungs-Kontrolle |
| **Technische Logs** | Login-Zeitpunkt, Session-Dauer | Sicherheit + Missbrauchs-Schutz |

**Was wir NICHT verarbeiten:**
- Inhalte von echten Kunden-Gesprächen (es sei denn, du lädst sie aktiv hoch)
- Telemetrie über deinen Browser oder andere Apps
- Tracking-Cookies oder Drittanbieter-Pixel

---

## 2 · Anthropic-Subprozessor (US-Routing)

Sellmo nutzt **Claude (Anthropic)** als KI-Backend für alle Trainings-Antworten. Das bedeutet:

- Deine Trainings-Aussagen + Persona-Profile werden **an Anthropic in den USA übermittelt**, um die KI-Antwort zu erzeugen
- Es gibt einen **Auftragsverarbeitungs-Vertrag (AVV)** zwischen Sellmo und Anthropic
- Anthropic-Datenschutz: https://www.anthropic.com/privacy
- **Cross-Border-Hinweis:** Datenübertragung in die USA unterliegt erhöhten Anforderungen — du erklärst dich mit der AVV-Akzeptanz ausdrücklich damit einverstanden.

**Anthropic gibt zu:** Anthropic verwendet Trainings-Dialoge des Sellmo-API-Zugriffs **NICHT zum weiteren Training ihrer Modelle** (Standard-API-Klausel der Anthropic-AGB).

---

## 3 · Hosting + Streamlit-Cloud (Subprozessor)

- **Aktuelles Hosting:** Streamlit Cloud (Snowflake Inc., USA) während der Closed-Alpha-Phase
- **Geplant ab Public-Beta:** Hetzner (EU, Falkenstein) — DSGVO-konformer
- **Datenresidenz Closed-Alpha:** USA via Streamlit Cloud
- **Bei Public-Beta-Wechsel:** alle User-Daten werden migriert, du wirst informiert

---

## 4 · Deine Rechte (DSGVO)

Du hast jederzeit das Recht auf:

| Recht | Wie umsetzen |
|---|---|
| **Auskunft** (Art. 15) | Email an christian@sellmo.io |
| **Berichtigung** (Art. 16) | Email an christian@sellmo.io |
| **Löschung** (Art. 17) | Email an christian@sellmo.io · innerhalb 7 Tagen umgesetzt · alle Sessions + Account werden gelöscht |
| **Datenübertragbarkeit** (Art. 20) | Export deiner Sessions als JSON auf Anfrage |
| **Widerspruch** (Art. 21) | Email an christian@sellmo.io |
| **Beschwerde** | Bei deiner zuständigen Datenschutz-Aufsichtsbehörde |

---

## 5 · Speicherdauer

- **Account aktiv:** so lange du Sellmo nutzt
- **Account inaktiv (90 Tage kein Login):** Erinnerungs-Mail + Auto-Löschung nach weiteren 30 Tagen
- **Aktiv gelöscht:** innerhalb 7 Tagen vollständig entfernt (inkl. Sessions, Cost-Logs)
- **Backups:** rolled werden täglich, gelöscht nach 14 Tagen

---

## 6 · Rechtsgrundlagen

| Verarbeitung | Rechtsgrundlage |
|---|---|
| Account + Login | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) |
| Trainings-Sessions | Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung) |
| Anthropic-Subprozessor + Cross-Border | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung via AVV-Confirm-Checkbox) |
| Cost-Tracking | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse: Missbrauchs-Schutz) |

---

## 7 · Änderungen dieser Hinweise

Sellmo ist Closed-Alpha. Sobald sich der Stack ändert (z.B. Wechsel zu Hetzner-EU-Hosting), werden diese Hinweise aktualisiert. Du wirst per E-Mail informiert.

---

## 8 · Kontakt

**Christian Hafner**
Sellmo · Sales-Founder
christian@sellmo.io

---

— Ende Datenschutz-Hinweise · v1.0 —
