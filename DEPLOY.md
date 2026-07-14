# Sellmo Deploy · Streamlit Cloud

Schritt-für-Schritt-Anleitung um die App auf Streamlit Cloud öffentlich zu machen, damit ein Beta-Tester sie im Browser nutzen kann.

**Voraussetzungen:**
- GitHub-Account (✓ vorhanden)
- Anthropic-API-Key (✓ vorhanden, dr.mumpitz@…)
- ~30 Min Zeit für die 4 Schritte unten

---

## Schritt 1 · GitHub-Repo erstellen und Code hochpushen

### 1.1 Repo auf github.com erstellen (3 Min)

1. Gehe auf https://github.com/new
2. **Repository name:** `sellmo-mvp`
3. **Description:** `Sellmo · KI-Sparring für Closer im DACH-Raum`
4. **Privacy:** wähle **Private** (wichtig — Code enthält Prompt-Engineering-IP)
5. **Initialize this repository with:** NICHTS ankreuzen (kein README, keine .gitignore — hab ich schon lokal)
6. Klick **Create repository**

Nach Klick zeigt GitHub die Seite mit Git-Kommandos. Du brauchst nur den Repo-Namen (nicht die Kommandos) — die geben ich Dir gleich.

### 1.2 Deinen GitHub-Username brauche ich

Bevor Du weitermachst: sag mir Deinen GitHub-Username (den Du eben bei Signup gewählt hast — z.B. `christian-sellmo` oder ähnlich). Ich pushe dann.

### 1.3 Push (mache ich, sobald ich den Username habe)

Ich führe für Dich aus (nachdem Du in Deinem Terminal `gh auth login` gemacht hast oder alternativ ein Personal-Access-Token erstellt hast — siehe 1.4):

```bash
git remote add origin https://github.com/<DEIN-USERNAME>/sellmo-mvp.git
git branch -M main
git push -u origin main
```

### 1.4 Wenn Push nach Passwort fragt

GitHub akzeptiert kein Passwort mehr, nur **Personal Access Token (PAT)**. Wenn's danach fragt:

1. Gehe zu https://github.com/settings/tokens/new
2. **Note:** `sellmo-deploy`
3. **Expiration:** 90 days
4. **Scopes:** haken bei `repo` (checked alles darunter)
5. **Generate token** → kopier den langen `ghp_...`-String
6. Beim Push als Passwort einfügen (der Username-Prompt bleibt gleich)

Alternativ eleganter: `brew install gh` (30 Sek) und dann `gh auth login` — merkt sich das für immer.

---

## Schritt 2 · Streamlit Cloud verbinden (5 Min)

1. Gehe auf https://share.streamlit.io/signup
2. **Continue with GitHub** — verwende denselben Account wie oben
3. Autorisiere Streamlit-Zugriff auf Deine Repos (nur read-only)
4. Nach Login: Klick **New app** (rechts oben)
5. Fülle aus:
   - **Repository:** `<DEIN-USERNAME>/sellmo-mvp`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** eigenes Subdomain wählen, z.B. `sellmo-mvp` → wird `sellmo-mvp.streamlit.app`
6. **NICHT sofort auf Deploy!** Erst Schritt 3 (Secrets eintragen), sonst crasht die App beim ersten Start.
7. Klick auf **Advanced settings** unten.

---

## Schritt 3 · Secrets eintragen (5 Min)

Im "Advanced settings"-Panel siehst Du ein Textfeld für **Secrets**. Kopier folgendes rein und ersetze die 3 Platzhalter:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-DEIN-ECHTER-KEY-HIER"
BETA_MODE = true
BETA_TOKENS = "SELLMO-BETA-9K3M"
```

**Erklärung:**
- `ANTHROPIC_API_KEY` → dein produktiver Key aus https://console.anthropic.com/settings/keys
- `BETA_MODE = true` → aktiviert das URL-Token-Gate (kein Login-Formular)
- `BETA_TOKENS` → **generier einen neuen Random-Token** für den ersten Tester. Beispiel: `SELLMO-BETA-` + 4 zufällige Zeichen. Mehrere Tokens durch Komma trennen wenn Du mehrere Tester hast.

Klick auf **Save** unten.

---

## Schritt 4 · Deploy und Testen (5 Min + Wartezeit)

1. Klick auf **Deploy!** unten
2. Streamlit baut jetzt einen Docker-Container mit Deiner App
3. Warte 2–5 Min beim ersten Deploy (siehst Log-Ausgabe live)
4. Wenn grüner Status: App ist live unter Deiner Subdomain

### 4.1 URL für den Tester bauen

Basis-URL: `https://<DEIN-SUBDOMAIN>.streamlit.app/?k=SELLMO-BETA-9K3M`

(Ersetze Subdomain + Token durch Deine echten Werte)

Beispiel-Nachricht an den Tester:

> Hey [Name], hier ist Sellmo als Preview:
>
> **https://sellmo-mvp.streamlit.app/?k=SELLMO-BETA-9K3M**
>
> Öffne den Link auf dem iPhone oder am Rechner. Beim ersten Öffnen dauert's evtl. 30 Sek bis alles lädt (Cold-Start).
>
> Wenn Du Feedback hast: einfach zurückschreiben. Was sich gut oder komisch anfühlt — beides hilft.
>
> Christian

### 4.2 Wenn der Token leakt

Ins Streamlit-Cloud-Dashboard, App-Settings → Secrets → Token aus `BETA_TOKENS` entfernen oder ersetzen → **Reboot app** → alter Link ist tot.

---

## Nach dem Deploy

- **Kosten-Monitor:** https://console.anthropic.com/settings/usage — Du siehst dort tägliche Costs. Setz Dir ein Alert bei 20 €/Monat unter Settings → Usage limits.
- **App-Metriken:** Streamlit Cloud zeigt Uptime, Cold-Starts, letzte Aktivität.
- **Updates deployen:** Änderungen an app.py lokal machen → `git add . && git commit -m "..." && git push` → Streamlit deployed automatisch in 1–2 Min neu.

---

## Bekannte Einschränkungen

- **Cold-Start** ca. 10–30 Sek wenn App länger als 15 Min idle war. Beim ersten Tester-Klick warnen.
- **Streamlit-Rerun-Verhalten:** Jede Interaktion (Persona-Auswahl, Chat-Message, etc.) rendert die App komplett neu. Für Tester merkbar aber nicht kritisch.
- **Keine Session-Persistenz** über Browser-Reload hinweg — jede Session startet frisch.
- **DSGVO:** Streamlit Cloud steht in USA. Für Beta-Test OK (Tester-Consent implizit über Beta-Vereinbarung), für Produktiv-Launch später Cloud-Provider mit EU-Hosting evaluieren (Fly.io Frankfurt, Hetzner).
