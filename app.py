"""
Sellmo MVP Trainings-App · Einwandbehandlung Textform · v0.2
============================================================
Single-File Streamlit-App fuer das Ueben von Einwandbehandlung.

Features v0.2 (Pfad A):
- Rollen-Wahl: Closer (Default) oder Customer
- MVP-Trainings-Matrix v1.0: 4 Kundentypen (F/O/R/M) × 5 Schwierigkeitsgrade (Kooperativ..Endgegner)
- Coach-Modus: EASY (Phasen-Coach + 3 Klick-Optionen) / MEDIUM (Phasen-Hinweis) / HARD (frei)
- Phasen-Leiste links in der Sidebar
- Streamlit-Theming nach Sellmo-Design-Brief v1.0
- Customer-Modus: KI spielt Closer (mit Closer-Bot-Prompt)

Start lokal:
  ANTHROPIC_API_KEY="$(cat ~/.sellmo_api_key)" python3 -m streamlit run app.py
"""

import json
import os
import random
from pathlib import Path
from datetime import datetime

import streamlit as st
from anthropic import Anthropic

# Auth + DSGVO (v1.1 · Phase 1.3 + 1.5)
try:
    import streamlit_authenticator as stauth
    import yaml
    from yaml.loader import SafeLoader
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


# ============================================================
# KONFIGURATION
# ============================================================

APP_DIR = Path(__file__).parent
PERSONAS_FILE = APP_DIR / "personas.json"
CUSTOMER_BOT_PROMPT_FILE = APP_DIR / "customer_bot_prompt.md"
FEEDBACK_COACH_PROMPT_FILE = APP_DIR / "feedback_coach_prompt.md"
PHASEN_COACH_PROMPT_FILE = APP_DIR / "phasen_coach_prompt.md"
CLOSER_BOT_PROMPT_FILE = APP_DIR / "closer_bot_prompt.md"
USERS_FILE = APP_DIR / "users.yaml"
PRIVACY_POLICY_FILE = APP_DIR / "PRIVACY_POLICY.md"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS_DEFAULT = 2048
MAX_TOKENS_COACH_LIVE = 1024
MAX_TOKENS_COACH_END = 4096
MAX_TOKENS_PHASEN_COACH = 1500
TEMPERATURE_BOT = 0.6
TEMPERATURE_COACH = 0.0

COST_PER_INPUT_TOKEN_EUR = 3.0 / 1_000_000
COST_PER_OUTPUT_TOKEN_EUR = 14.0 / 1_000_000

# Sellmo-Theming-Konstanten · CloserCoach-Palette-Adaption (2026-07-14)
ACCENT_PRIMARY = "#33E88E"       # Primary Green (CTA, Progress, Erfolg, Aktivierung)
ACCENT_SUBTLE = "#0F3D1E"        # Dark-Green-Fill (Trust-Kategorie, Active-Pill-BG)
BG_DEFAULT = "#000000"           # Reines Schwarz als Ground
BG_DEEP_FEEDBACK = "#08182D"     # Navy für Deep-Feedback-Screens
SURFACE_1 = "#17181C"            # Card-Fill
SURFACE_2 = "#2A2A2C"            # AI-Bubble-Fill / erhöhter Surface
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "rgba(255,255,255,0.7)"
TEXT_TERTIARY = "rgba(255,255,255,0.5)"
BORDER_DEFAULT = "rgba(255,255,255,0.15)"
SELLMO_ORANGE = "#33E88E"        # Legacy-Alias (deprecated, zeigt jetzt auf Grün)

# Sekundäre Akzente
ACCENT_BLUE = "#2E86FF"          # Rep-Bubble Blau
ACCENT_COBALT = "#3F5EFC"        # Sekundärer CTA-Cobalt
ACCENT_AMBER = "#F5A623"         # Analyzing / Keep-Going / Progress-mid
ACCENT_RED = "#E63946"           # Signal-Rot (End-Call, Error, Delete)
ACCENT_DEEP_RED = "#5A0F1E"      # Rot-hinterlegte Fehler-Bubble im Feedback
ACCENT_PURPLE = "#7E4FE8"        # Competition-Kategorie

SUCCESS = "#33E88E"              # unified mit Primary
WARNING = "#F5A623"
ERROR = "#E63946"

# Objection-Kategorie-Farbtokens (Fill + Border)
CAT_PRICE_FILL = "#5A0F1E";      CAT_PRICE_BORDER = "#E63946"
CAT_COMPETITION_FILL = "#2D0F3D"; CAT_COMPETITION_BORDER = "#7E4FE8"
CAT_TIMING_FILL = "#3D2D0F";     CAT_TIMING_BORDER = "#F5A623"
CAT_TRUST_FILL = "#0F3D1E";      CAT_TRUST_BORDER = "#33E88E"
CAT_AUTHORITY_FILL = "#0F2D3D";  CAT_AUTHORITY_BORDER = "#2E86FF"
CAT_URGENCY_FILL = "#3D1E0F";    CAT_URGENCY_BORDER = "#C86732"


# ============================================================
# AUTH + DSGVO HELPERS (v1.1 · Phase 1.3 + 1.5)
# ============================================================

def load_users_config():
    """Laedt users.yaml. Gibt None zurueck wenn nicht vorhanden (= Auth-disabled-Modus)."""
    if not AUTH_AVAILABLE:
        return None
    if not USERS_FILE.exists():
        return None
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader)


def save_users_config(config):
    """Persistiert Aenderungen an users.yaml (z.B. avv_accepted-Flag)."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_authenticator(config):
    """Erzeugt streamlit-authenticator-Instanz."""
    return stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )


def render_privacy_policy_expander():
    """Privacy-Policy als ausklappbares Element."""
    with st.expander("Datenschutz-Hinweise · Bitte lesen vor Akzeptanz"):
        if PRIVACY_POLICY_FILE.exists():
            with open(PRIVACY_POLICY_FILE, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.warning("PRIVACY_POLICY.md nicht gefunden — bitte an Christian wenden.")


def render_avv_consent_screen(authenticator, username, config):
    """Erst-Login-Screen: AVV-Akzeptanz erforderlich bevor App genutzt werden kann."""
    st.markdown("# Datenschutz-Akzeptanz")
    st.markdown(
        f'<div style="color:#94a3b8; font-size:14px; margin-bottom: 16px;">'
        f'Bevor du Sellmo nutzen kannst, brauchen wir deine ausdrueckliche Einwilligung '
        f'zur Verarbeitung deiner Trainings-Daten gemaess unserer Datenschutz-Hinweise.'
        f'</div>',
        unsafe_allow_html=True
    )

    render_privacy_policy_expander()

    st.markdown("---")
    accepted = st.checkbox(
        "Ich habe die Datenschutz-Hinweise gelesen und akzeptiere die Verarbeitung "
        "meiner Trainings-Daten gemaess AVV mit Anthropic (Cross-Border-Routing USA) "
        "sowie die Speicherung bei Streamlit Cloud waehrend der Closed-Alpha-Phase.",
        key="avv_consent_checkbox"
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Akzeptieren und starten", type="primary",
                      use_container_width=True, disabled=not accepted):
            # Update users.yaml: avv_accepted = true, avv_accepted_at = now
            config["credentials"]["usernames"][username]["avv_accepted"] = True
            config["credentials"]["usernames"][username]["avv_accepted_at"] = \
                datetime.now().isoformat()
            save_users_config(config)
            st.rerun()
    with col2:
        if st.button("Abmelden ohne Akzeptanz", use_container_width=True):
            authenticator.logout(location="unrendered")
            st.rerun()


def _render_closed_alpha_landing(authenticator):
    """Closed-Alpha Login-Landingpage v2 · Sleak-Layout in Sellmo-Identity.
    Aufbau: Top-Nav · Hero · Pain · How-It-Works (4 Steps) · Use-Case-Grid (2x2) · Trust · Bottom-CTA mit Login + Account-Button.
    Variante C: Dark-Mode + Orange-Akzent, sleak-strukturierte Layout-Disziplin.
    """
    WORDMARK_SVG_LARGE = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="280" height="68" viewBox="0 0 180 44" role="img" aria-label="sellmo">'
        '<text x="0" y="34" font-family="Inter, -apple-system, BlinkMacSystemFont, sans-serif" font-weight="800" font-size="40" letter-spacing="-1.6">'
        '<tspan fill="#F5F5F7">sell</tspan><tspan fill="#33E88E">mo</tspan>'
        '</text>'
        '</svg>'
    )
    WORDMARK_SVG_SMALL = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="30" viewBox="0 0 180 44" role="img" aria-label="sellmo">'
        '<text x="0" y="34" font-family="Inter, -apple-system, BlinkMacSystemFont, sans-serif" font-weight="800" font-size="40" letter-spacing="-1.6">'
        '<tspan fill="#F5F5F7">sell</tspan><tspan fill="#33E88E">mo</tspan>'
        '</text>'
        '</svg>'
    )

    # === Top-Nav (Wordmark links · Login-Link rechts) ===
    st.markdown(
        f'<div class="lp-container">'
        f'  <nav class="lp-nav">'
        f'    <div class="lp-nav-wordmark">{WORDMARK_SVG_SMALL}</div>'
        f'    <a class="lp-nav-login" href="#login-section">LOGIN</a>'
        f'  </nav>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === Pain-Anchor · OPENER (ganz oben) · Hero-Format · vertikal zentriert ===
    st.markdown(
        f'<div class="lp-container">'
        f'  <div class="lp-pain-hero">'
        f'    <div class="lp-pain-label">Das Problem</div>'
        f'    <h2 class="lp-pain-title">Du verlierst Deals und weißt nicht warum.</h2>'
        f'    <p class="lp-pain-body">'
        f'Liegt es am Lead, am Pitch, am Pricing — oder doch an dir? '
        f'Bisher konntest du das nicht prüfen, ohne echte Calls zu verbrennen. '
        f'Jeder verlorene Abschluss kostet dich vier- bis fünfstellig im Monat. '
        f'Und keiner sagt dir, wo du methodisch wackelst.</p>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === Hero · Zwei-Spalten-Grid (Tagline + Sub LINKS, FORM-Matrix-Preview RECHTS) ===
    st.markdown(
        f'<div class="lp-container">'
        f'  <div class="lp-hero">'
        f'    <div class="lp-hero-grid">'
        # Linke Spalte: Wordmark + Tagline + Sub
        f'      <div>'
        f'        <div class="lp-hero-wordmark">{WORDMARK_SVG_LARGE}</div>'
        f'        <div style="margin: -8px 0 20px 0;"><span class="cc-active-pill">Closed-Alpha läuft</span></div>'
        f'        <h1 class="lp-hero-tagline">Trainier die 4 Kundentypen,<br>bis du jeden abschließt.</h1>'
        f'        <p class="lp-hero-sub">Die KI-Sparring-Plattform für High-Ticket-Closer im DACH-Raum. '
        f'20 kanonische Trainings-Szenarien — 4 Kundentypen × 5 Schwierigkeitsgrade — mit echter DACH-Sprache.</p>'
        f'      </div>'
        # Rechte Spalte: Mini-FORM-Matrix als Produkt-Preview
        f'      <div class="lp-hero-visual">'
        f'        <div class="lp-hero-visual-label">Trainings-Matrix</div>'
        f'        <div class="lp-hero-visual-title">4 Kundentypen · 5 Schwierigkeitsgrade</div>'
        f'        <div class="lp-mini-matrix" style="grid-template-columns: 80px repeat(5, 1fr);">'
        f'          <div></div>'
        f'          <div class="lp-mini-matrix-h">Koop.</div>'
        f'          <div class="lp-mini-matrix-h">Skept.</div>'
        f'          <div class="lp-mini-matrix-h">Konfr.</div>'
        f'          <div class="lp-mini-matrix-h">Misstr.</div>'
        f'          <div class="lp-mini-matrix-h">Endg.</div>'
        # Fokussiert · Lukas
        f'          <div class="lp-mini-matrix-row-label">Fokussiert</div>'
        f'          <div class="lp-mini-cell-filled lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        # Offen · Niklas
        f'          <div class="lp-mini-matrix-row-label">Offen</div>'
        f'          <div class="lp-mini-cell-filled lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        # Ruhig · Andreas
        f'          <div class="lp-mini-matrix-row-label">Ruhig</div>'
        f'          <div class="lp-mini-cell-filled lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        # Methodisch · Sarah
        f'          <div class="lp-mini-matrix-row-label">Methodisch</div>'
        f'          <div class="lp-mini-cell-filled lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'          <div class="lp-mini-cell">●</div>'
        f'        </div>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === How-It-Works · 4 Steps (Sleak-Watermark-Layout in Sellmo-Orange) ===
    st.markdown(
        f'<div class="lp-container">'
        f'  <div class="lp-section">'
        f'    <div class="lp-steps-header">'
        f'      <h2 class="lp-steps-title">So funktioniert sellmo</h2>'
        f'      <p class="lp-steps-sub">Vier Schritte vom Setup bis zum nächsten gewonnenen Deal.</p>'
        f'    </div>'
        f'    <div class="lp-steps-grid">'
        f'      <div class="lp-step">'
        f'        <div class="lp-step-num">01</div>'
        f'        <h3 class="lp-step-title">Customer-Typ wählen</h3>'
        f'        <p class="lp-step-body">4 Kundentypen — Fokussiert, Offen, Ruhig, Methodisch — in 5 Schwierigkeitsstufen von Kooperativ bis Endgegner. Wahl per Klick.</p>'
        f'      </div>'
        f'      <div class="lp-step">'
        f'        <div class="lp-step-num">02</div>'
        f'        <h3 class="lp-step-title">Sparring starten</h3>'
        f'        <p class="lp-step-body">Du gehst in einen realistischen Sales-Dialog. Die KI spielt den Customer authentisch.</p>'
        f'      </div>'
        f'      <div class="lp-step">'
        f'        <div class="lp-step-num">03</div>'
        f'        <h3 class="lp-step-title">Methodisches Feedback</h3>'
        f'        <p class="lp-step-body">Jeder deiner Moves wird gegen das EPISCH-Framework bewertet. Der Phasen-Coach zeigt dir live 3 methodisch saubere Antwort-Optionen.</p>'
        f'      </div>'
        f'      <div class="lp-step">'
        f'        <div class="lp-step-num">04</div>'
        f'        <h3 class="lp-step-title">Skill-Tree füllen</h3>'
        f'        <p class="lp-step-body">Du siehst pro Zelle wo du stark bist und wo Lücken sind. Trainier gezielt nach.</p>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === Use-Case-Grid · 2x2 (Sleak-Card-Layout) ===
    st.markdown(
        f'<div class="lp-container">'
        f'  <div class="lp-section">'
        f'    <div class="lp-steps-header">'
        f'      <h2 class="lp-steps-title">Mehr als ein Trainings-Tool</h2>'
        f'      <p class="lp-steps-sub">Vier Bausteine, die zusammen mehr ergeben als die Summe ihrer Teile.</p>'
        f'    </div>'
        f'    <div class="lp-usecase-grid">'
        # Card 1: Personal Sparring
        f'      <div class="lp-usecase-card">'
        f'        <div class="lp-usecase-visual">'
        f'          <div class="lp-usecase-avatar">D</div>'
        f'          <div style="color:{TEXT_TERTIARY}; font-size:11px;">&nbsp;0:27&nbsp;</div>'
        f'          <div class="lp-usecase-avatar lp-usecase-avatar-muted">AI</div>'
        f'        </div>'
        f'        <h3 class="lp-usecase-title">Persönlicher KI-Sparringspartner</h3>'
        f'        <p class="lp-usecase-body">sellmo führt realistische Rollenspiele mit dir und gibt im Anschluss methodisches Feedback — kein Pep-Talk, nur Daten.</p>'
        f'      </div>'
        # Card 2: FORM-Cluster
        f'      <div class="lp-usecase-card">'
        f'        <div class="lp-usecase-visual" style="flex-wrap:wrap;">'
        f'          <span class="lp-usecase-chip">Fokussiert</span>'
        f'          <span class="lp-usecase-chip">Offen</span>'
        f'          <span class="lp-usecase-chip">Ruhig</span>'
        f'          <span class="lp-usecase-chip">Methodisch</span>'
        f'        </div>'
        f'        <h3 class="lp-usecase-title">4 Kundentypen × 5 Schwierigkeitsstufen</h3>'
        f'        <p class="lp-usecase-body">Fokussiert, Offen, Ruhig, Methodisch — jeder Typ in fünf Schwierigkeitsstufen (Kooperativ, Skeptisch, Konfrontativ, Misstrauisch, Endgegner). 20 Trainings-Zellen, alle einzeln trainierbar.</p>'
        f'      </div>'
        # Card 3: Skill-Gaps mit Progress-Bars
        f'      <div class="lp-usecase-card">'
        f'        <div class="lp-usecase-visual" style="flex-direction:column; align-items:stretch; gap:6px;">'
        f'          <div class="lp-usecase-progressrow">'
        f'            <span class="lp-usecase-progress-label">Fokussiert · Stufe 3</span>'
        f'            <div class="lp-usecase-progress-bar"><div class="lp-usecase-progress-fill" style="width:60%;"></div></div>'
        f'          </div>'
        f'          <div class="lp-usecase-progressrow">'
        f'            <span class="lp-usecase-progress-label">Ruhig · Stufe 1</span>'
        f'            <div class="lp-usecase-progress-bar"><div class="lp-usecase-progress-fill" style="width:85%;"></div></div>'
        f'          </div>'
        f'          <div class="lp-usecase-progressrow">'
        f'            <span class="lp-usecase-progress-label">Ruhig · Stufe 3</span>'
        f'            <div class="lp-usecase-progress-bar"><div class="lp-usecase-progress-fill" style="width:30%;"></div></div>'
        f'          </div>'
        f'        </div>'
        f'        <h3 class="lp-usecase-title">Skill-Gaps sichtbar machen</h3>'
        f'        <p class="lp-usecase-body">Pro Customer-Typ siehst du, wo du stark bist und wo du noch Lücken hast. Kein Bauchgefühl, sondern Mastery-Daten.</p>'
        f'      </div>'
        # Card 4: Methodik-Stack
        f'      <div class="lp-usecase-card">'
        f'        <div class="lp-usecase-visual">'
        f'          <div style="display:flex; gap:10px;">'
        f'            <div style="background:{SURFACE_2}; padding:8px 14px; border-radius:8px; border:1px solid {BORDER_DEFAULT}; font-size:11px; color:{TEXT_SECONDARY};">EPISCH-Framework</div>'
        f'            <div style="background:{SURFACE_2}; padding:8px 14px; border-radius:8px; border:1px solid {BORDER_DEFAULT}; font-size:11px; color:{TEXT_SECONDARY};">4×5-Matrix</div>'
        f'            <div style="background:{ACCENT_SUBTLE}; padding:8px 14px; border-radius:8px; border:1px solid {ACCENT_PRIMARY}55; font-size:11px; color:{ACCENT_PRIMARY};">DACH-Sprache</div>'
        f'          </div>'
        f'        </div>'
        f'        <h3 class="lp-usecase-title">Methodik statt Bauchgefühl</h3>'
        f'        <p class="lp-usecase-body">Das Sellmo Objection Handling Framework ist aus 27 Real-World-Transkripten kondensiert — nicht aus Sales-Lehrbüchern.</p>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === Outcome-Vision (Neuromarketing: Future-Self-Pain-Expansion) · zentriert ===
    st.markdown(
        f'<div class="lp-container">'
        f'  <div class="lp-section" style="text-align:center;">'
        f'    <div class="lp-section-label" style="text-align:center;">Was du erreichst</div>'
        f'    <h2 class="lp-section-title" style="text-align:center;">In 90 Tagen beherrschst du alle 20 Trainings-Zellen.</h2>'
        f'    <p class="lp-section-body" style="margin:0 auto; max-width:680px; text-align:center;">'
        f'Fokussiert, Offen, Ruhig, Methodisch — und jeden davon in fünf Schwierigkeitsstufen von Kooperativ bis Endgegner. '
        f'Egal welcher Typ in den Call kommt, du weißt was zu tun ist. Die Mechanik ist verinnerlicht. '
        f'Deine Abschluss-Quote steigt messbar — und du kannst pro Customer-Konstellation sagen, '
        f'an welcher methodischen Stelle du wackelst.</p>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === Trust-Signals (Social Proof + Authority) · zentriert ===
    st.markdown(
        f'<div class="lp-container">'
        f'  <div class="lp-section" style="text-align:center;">'
        f'    <div class="lp-section-label" style="text-align:center;">Methodik-Stack</div>'
        f'    <div class="lp-trust" style="justify-content:center;">'
        f'      <div class="lp-trust-item">'
        f'        <span class="lp-trust-num">27</span>'
        f'        <span class="lp-trust-label">Real-World-Transkripte als Trainings-Basis</span>'
        f'      </div>'
        f'      <div class="lp-trust-item">'
        f'        <span class="lp-trust-num">20</span>'
        f'        <span class="lp-trust-label">Trainings-Zellen · Kooperativ bis Endgegner</span>'
        f'      </div>'
        f'      <div class="lp-trust-item">'
        f'        <span class="lp-trust-num">4</span>'
        f'        <span class="lp-trust-label">Kundentypen · Fokussiert · Offen · Ruhig · Methodisch</span>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === Bottom-CTA mit Login + Account-Anfrage ===
    st.markdown(
        f'<div id="login-section" class="lp-container">'
        f'  <div class="lp-cta-final">'
        f'    <h2 class="lp-cta-final-title">Bereit zum Sparring?</h2>'
        f'    <p class="lp-cta-final-sub">Closed-Alpha läuft. Login mit deinem Account — oder schreib uns für einen Beta-Zugang.</p>'
        f'    <div class="lp-cta-buttons" style="align-items:center;">'
        f'      <a class="cc-cta-pill" href="#login-form" style="max-width:320px;">Login &nbsp;→</a>'
        f'      <a class="lp-btn-secondary" href="mailto:christian@sellmo.io?subject=sellmo%20Beta-Zugang%20anfragen">Account erstellen</a>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # === Login-Form in zentrierter, schmaler Spalte (~410px innerhalb 1280px) ===
    st.markdown('<div id="login-form"></div>', unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        try:
            authenticator.login(location="main", key="auth-login")
        except TypeError:
            authenticator.login("main")

        auth_status = st.session_state.get("authentication_status")
        if auth_status is False:
            st.error("Username oder Passwort falsch. Wenn du Hilfe brauchst, schreib Christian.")

    # === Footer mit Privacy-Expander als kleines zentriertes Feld ===
    st.markdown(
        '<div style="height:48px;"></div>'  # Spacer
        '<div style="max-width:1200px; margin: 0 auto; padding: 24px 24px 0 24px; border-top: 1px solid #2A2A30;"></div>',
        unsafe_allow_html=True
    )
    col_l_foot, col_c_foot, col_r_foot = st.columns([1, 1, 1])
    with col_c_foot:
        render_privacy_policy_expander()

    st.markdown('<div style="height:64px;"></div>', unsafe_allow_html=True)


def render_beta_token_gate():
    """URL-Query-Token-Gate für Beta-Preview (Cloud-Deploy).
    Aktiviert wenn st.secrets["BETA_MODE"] == True.
    Kein Login-Formular — reiner Token-Match aus ?k=<token>.
    Returns (dict, username, name) wenn Token OK, sonst (None, None, None).
    """
    # BETA_TOKENS als String in secrets: kommaseparierte Liste
    # Beispiel: BETA_TOKENS = "SELLMO-BETA-9K3M,SELLMO-BETA-2X7P"
    tokens_raw = st.secrets.get("BETA_TOKENS", "")
    valid_tokens = {t.strip() for t in tokens_raw.split(",") if t.strip()}

    query_token = st.query_params.get("k", "")
    if isinstance(query_token, list):
        query_token = query_token[0] if query_token else ""

    if query_token and query_token in valid_tokens:
        # Token OK → App startet
        # AVV-akzeptiert wird impliziert (Tester haben Beta-Vereinbarung separat)
        return ({"_beta_mode": True, "token": query_token}, f"beta_{query_token[-4:]}", "Beta-Tester")

    # Kein / falscher Token → Zugangs-Screen
    st.markdown(
        f'<div style="max-width: 480px; margin: 80px auto; padding: 40px 24px; text-align: center;">'
        f'  <div style="width: 88px; height: 88px; margin: 0 auto 24px; border-radius: 50%; '
        f'       background: radial-gradient(circle at 50% 40%, {ACCENT_SUBTLE}, #000 70%); '
        f'       display: grid; place-items: center; font-size: 40px;">🎯</div>'
        f'  <div style="font-weight: 800; font-size: 28px; letter-spacing: -0.02em; margin-bottom: 8px;">'
        f'    sell<span style="color: {ACCENT_PRIMARY};">mo</span></div>'
        f'  <div style="color: {TEXT_SECONDARY}; font-size: 14px; margin-bottom: 32px;">Beta-Preview · Zugang benötigt</div>'
        f'  <div style="background: {SURFACE_1}; border: 1px solid {BORDER_DEFAULT}; border-radius: 14px; '
        f'       padding: 20px 24px; text-align: left;">'
        f'    <div style="font-size: 15px; color: {TEXT_PRIMARY}; margin-bottom: 12px; font-weight: 600;">'
        f'      Kein gültiger Beta-Token</div>'
        f'    <div style="font-size: 13px; color: {TEXT_SECONDARY}; line-height: 1.5;">'
        f'      Du brauchst einen persönlichen Beta-Link von Christian. Wenn Du einen hast: '
        f'      Link direkt aufrufen (mit <code style="background:{SURFACE_2}; padding:1px 4px; '
        f'      border-radius:3px; font-size:11px;">?k=…</code> am Ende).<br><br>'
        f'      Kein Link? Schreib an <a href="mailto:christian@sellmo.io?subject=Sellmo%20Beta-Zugang" '
        f'      style="color: {ACCENT_PRIMARY};">christian@sellmo.io</a>.'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )
    return (None, None, None)


def render_login_wall():
    """Login-Wall: rendert Login-Form, gibt (config, username, name) zurueck wenn eingeloggt + AVV akzeptiert.
    Returns (None, None, None) wenn Login noch nicht abgeschlossen — Caller soll dann abbrechen.
    """
    config = load_users_config()
    if config is None:
        # Auth nicht konfiguriert (z.B. users.yaml fehlt) — Fallback: App ohne Auth
        st.warning(
            "Auth nicht konfiguriert (`users.yaml` fehlt). "
            "App läuft im Entwicklungs-Modus ohne Login. "
            "Fuer Closed-Alpha: `cp users.yaml.example users.yaml` und Test-User anlegen."
        )
        return ({"_dev_mode": True}, "dev", "Entwickler-Modus")

    authenticator = get_authenticator(config)

    # Pre-Check: ist bereits eingeloggt?
    pre_auth_status = st.session_state.get("authentication_status")
    if pre_auth_status is not True:
        # Noch nicht eingeloggt → Landing-Page mit Login-Form rendern
        _render_closed_alpha_landing(authenticator)
        auth_status = st.session_state.get("authentication_status")
        if auth_status is not True:
            return (None, None, None)
        # auth_status JUST became True (login successful) → fall through to AVV-Check

    # auth_status == True → eingeloggt
    username = st.session_state.get("username")
    name = st.session_state.get("name")

    # AVV-Check
    user_data = config["credentials"]["usernames"].get(username, {})
    if not user_data.get("avv_accepted", False):
        # AVV noch nicht akzeptiert → Consent-Screen rendern
        render_avv_consent_screen(authenticator, username, config)
        return (None, None, None)

    # Vollstaendig eingeloggt + AVV akzeptiert
    return (authenticator, username, name)


def render_user_info_sidebar(authenticator, username, name):
    """Zeigt User-Info + Logout-Button in der Sidebar."""
    with st.sidebar:
        st.markdown(
            f'<div style="background: rgba(51,232,142,0.08); border: 1px solid rgba(51,232,142,0.25); '
            f'border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 13px;">'
            f'<strong>{name}</strong><br>'
            f'<span style="color: #94a3b8; font-size: 11px;">{username}@sellmo</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        if authenticator is not None and not isinstance(authenticator, dict):
            try:
                authenticator.logout(location="sidebar", key="auth-logout")
            except TypeError:
                authenticator.logout("Logout", "sidebar")


# ============================================================
# RESSOURCEN LADEN
# ============================================================

@st.cache_data
def load_personas():
    with open(PERSONAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_prompt(file_path_str):
    file_path = Path(file_path_str)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 3:
            prompt = parts[1]
            if prompt.startswith("text\n"):
                prompt = prompt[5:]
            return prompt.strip()
    return content.strip()


PERSONAS_DATA = load_personas()
CUSTOMER_BOT_PROMPT = load_prompt(str(CUSTOMER_BOT_PROMPT_FILE))
FEEDBACK_COACH_PROMPT = load_prompt(str(FEEDBACK_COACH_PROMPT_FILE))
PHASEN_COACH_PROMPT = load_prompt(str(PHASEN_COACH_PROMPT_FILE))
CLOSER_BOT_PROMPT = load_prompt(str(CLOSER_BOT_PROMPT_FILE))

# ============================================================
# MVP-TRAININGS-MATRIX v1.0 (2026-06-03 · Lock #8)
# 4 Personas (F/O/R/M) x 5 Grade x Einwand Geld = 20 Trainings-Szenarien
# Quelle: Einwandbehandlung/Sellmo_MVP_Trainings_Matrix_v1.0.md
# ============================================================

MVP_PERSONAS = {
    "F": {"name": "Lukas", "alter": 34, "job": "Selbstaendiger Solo-Berater",
          "kern_einwand_kategorie": "Geld", "kurz": "Fokussiert",
          "avatar_bg": "#EEEDFE", "avatar_fg": "#26215C"},
    "O": {"name": "Niklas", "alter": 29, "job": "Angestellter Sales-Aufsteiger",
          "kern_einwand_kategorie": "Geld", "kurz": "Offen",
          "avatar_bg": "#FAECE7", "avatar_fg": "#4A1B0C"},
    "R": {"name": "Andreas", "alter": 41, "job": "Angestellter Vertriebs-Manager",
          "kern_einwand_kategorie": "Geld", "kurz": "Ruhig",
          "avatar_bg": "#E1F5EE", "avatar_fg": "#04342C"},
    "M": {"name": "Sarah", "alter": 36, "job": "Business-Consultant",
          "kern_einwand_kategorie": "Geld", "kurz": "Methodisch",
          "avatar_bg": "#E6F1FB", "avatar_fg": "#042C53"},
}

MVP_GRADE = [
    {"key": 1, "label": "Kooperativ", "color": "#EAF3DE"},
    {"key": 2, "label": "Skeptisch", "color": "#FAEEDA"},
    {"key": 3, "label": "Konfrontativ", "color": "#FAECE7"},
    {"key": 4, "label": "Misstrauisch", "color": "#FCEBEB"},
    {"key": 5, "label": "Endgegner", "color": "#2C2C2A"},
]

MVP_OPENING_EINWAENDE = {
    ("F", 1): "Das ist eine Menge Geld. Rechnet sich das für mich?",
    ("F", 2): "4.800 ist happig. Sag mir mal ganz konkret: worauf basiert der Preis?",
    ("F", 3): "Ehrlich, das ist mir zu teuer. Ich seh nicht, wo da 4.800 Euro Wert drinstecken sollen.",
    ("F", 4): "Ich hab schon mal in ein Coaching investiert. War versprochen mir eine Umsatzverdopplung, unterm Strich hab ich das Geld nachweislich verbrannt. Warum sollte das hier anders sein?",
    ("F", 5): "Lass mich raten: gleich fragst du mich, was ich bereit wäre für einen zusätzlichen Deal pro Monat zu investieren, dann rechnest du mir aus, dass sich das Ganze nach 3 Wochen amortisiert. Kenn ich. Ich hab zwei Programme gekauft, beide haben mir mit dem gleichen Rechenspiel das Blaue vom Himmel versprochen. Am Ende: 9.000 Euro futsch. Also spar dir die ROI-Rechnung.",
    ("O", 1): "Uff, das ist schon viel. Aber wenn's mich echt weiterbringt, ist es das wert…",
    ("O", 2): "Alter, 4.800 — das ist ne Hausnummer. Ich müsste schon sicher sein, dass ich damit wirklich hinkomme, wohin ich will.",
    ("O", 3): "Ehrlich, das ist mir grad zu viel. Ich hab Bock auf so ein Programm, klar — aber nicht für 4.800.",
    ("O", 4): "Ich hab mir letztes Jahr so ein Mindset-Programm geholt, war auch nicht billig. Am Ende war ich pumped, hab drei Wochen Vollgas gegeben, dann war die Luft raus und nix hat sich wirklich verändert. Weiß nicht, ob ich dafür nochmal Geld ausgeben will.",
    ("O", 5): "Und jetzt kommt der Teil, wo du mich fragst, wie mein Leben in einem Jahr aussehen soll, und mir dann sagst, dass 4.800 Euro dagegen nichts sind. Kenn ich. Genau den Move hat der Typ vom letzten Coaching auch gebracht. Zwei Programme, 7.000 Euro verbrannt, das Blaue vom Himmel versprochen. Nix davon ist eingetreten. Also lass die Vision-Nummer, die zieht bei mir nicht mehr.",
    ("R", 1): "Ich muss das ehrlich gesagt erst mit meiner Frau besprechen.",
    ("R", 2): "Ich weiß nicht… 4.800 ist eine Ansage, und meine Frau würde da definitiv Fragen stellen. Ehrlich gesagt bin ich auch selbst skeptisch.",
    ("R", 3): "Ehrlich, das ist einfach zu teuer. Ich weiß nicht, was das rechtfertigen soll, gerade jetzt.",
    ("R", 4): "Weißt du was, ich hab schon mal so ein Programm gemacht. Hat nicht gehalten, was es versprochen hat. Meine Frau hat mir das damals lange nachgetragen. Ich weiß nicht, ob ich mir das wieder antun will.",
    ("R", 5): "Du willst mich jetzt bestimmt fragen, was mir wichtig ist, und dann das Coaching drüberlegen. Kenn ich schon. Ich hab zwei Programme gekauft, beide haben mir das Blaue vom Himmel versprochen, ich hab 8.000 Euro verbrannt. Also spar dir bitte den Reframe.",
    ("M", 1): "Was ist da genau drin? Ich möchte das gegen andere Optionen vergleichen.",
    ("M", 2): "4.800 ist im oberen Drittel dessen, was ich bisher gesehen habe. Kannst du mir konkret sagen, was der Preis rechtfertigt gegenüber den 2.500-Euro-Angeboten?",
    ("M", 3): "Ich hab mir die Komponenten angeschaut. Ehrlich gesagt sehe ich nicht, warum ich hier 4.800 zahlen soll, wenn ich für die Hälfte etwas Vergleichbares bekomme.",
    ("M", 4): "Ich hab mir letztes Jahr ein Programm gekauft, war strukturell sauber aufgebaut, alle Module da — und trotzdem hat es nicht den Sprung gebracht, den es versprochen hat. Ich frage mich, ob der Unterschied zu deinem Programm groß genug ist, um das Risiko zu rechtfertigen.",
    ("M", 5): "Ich sehe schon, wo das hinläuft. Du präsentierst mir jetzt die USP-Differenzierung, wahrscheinlich mit einem 1:1-Anteil, den die anderen nicht haben. Ich hab genau das schon zweimal gehört und zweimal 6.000 Euro dafür bezahlt. Beide Programme haben mir am Ende das Blaue vom Himmel versprochen und nichts geliefert. Ich brauche keine weitere USP-Show, ich brauche einen Grund, warum ich dir mehr glauben soll als denen.",
}


def build_mvp_persona(form_type: str, grad: int) -> dict:
    """Konstruiert ein Persona-Dict fuer die aktuelle MVP-Zelle (form_type x grad)."""
    base = MVP_PERSONAS[form_type]
    grad_entry = next(g for g in MVP_GRADE if g["key"] == grad)
    return {
        "id": f"mvp_{form_type.lower()}{grad}",
        "cluster_id": f"mvp_{form_type.lower()}",
        "name": base["name"],
        "alter": base["alter"],
        "job": base["job"],
        "kern_einwand_kategorie": base["kern_einwand_kategorie"],
        "form_type": form_type,
        "difficulty": grad,
        "grad_label": grad_entry["label"],
        "discovery_summary": f"{base['name']} ({base['alter']}, {base['job']}) - FORM-Typ {form_type} ({base['kurz']}), Schwierigkeitsgrad {grad} ({grad_entry['label']}).",
        "opening_einwand": MVP_OPENING_EINWAENDE[(form_type, grad)],
        "personality_notes": f"MVP-Trainings-Zelle {form_type}{grad}. Verwende Sprach-Marker der Persona {base['name']} + Grad-Verhalten {grad_entry['label']}.",
    }


# ============================================================
# CUSTOM CSS (Sellmo-Theming)
# ============================================================

CUSTOM_CSS = f"""
<style>
    /* Globale Schrift-Verbesserungen */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        letter-spacing: -0.01em;
    }}

    /* Buttons aufbessern */
    .stButton > button {{
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        transition: all 200ms ease-out !important;
        border: 1px solid {BORDER_DEFAULT} !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(51, 232, 142, 0.20);
    }}

    /* Primary-Buttons */
    .stButton > button[kind="primary"] {{
        background: {ACCENT_PRIMARY} !important;
        color: {BG_DEFAULT} !important;
        font-weight: 600 !important;
        border: none !important;
    }}

    /* Chat-Input-Feld */
    .stChatInput textarea {{
        background: {SURFACE_2} !important;
        border: 1px solid {BORDER_DEFAULT} !important;
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
    }}
    .stChatInput textarea:focus {{
        border-color: {ACCENT_PRIMARY} !important;
        box-shadow: 0 0 0 3px {ACCENT_PRIMARY}33 !important;
    }}

    /* Phasen-Leiste */
    .phase-bar {{
        background: {SURFACE_1};
        border-radius: 12px;
        padding: 16px;
        border: 1px solid {BORDER_DEFAULT};
        position: sticky;
        top: 4.5rem;
        z-index: 10;
    }}

    /* Linke Spalte (mit der Phasen-Leiste) auf sticky-Verhalten vorbereiten */
    [data-testid="column"]:first-child {{
        position: sticky;
        top: 4.5rem;
        align-self: flex-start;
    }}

    /* These #2: Sidebar-Phasen-Bar sticky machen — bleibt beim Chat-Scroll sichtbar */
    section[data-testid="stSidebar"] .phase-bar {{
        position: sticky;
        top: 1rem;
        z-index: 100;
        margin-bottom: 16px;
    }}
    /* Sidebar-Container selbst soll bei Chat-Scroll mitscrollen */
    section[data-testid="stSidebar"] > div:first-child {{
        position: sticky;
        top: 0;
        max-height: 100vh;
        overflow-y: auto;
    }}
    .phase-item {{
        display: flex;
        align-items: center;
        padding: 8px 12px;
        margin-bottom: 4px;
        border-radius: 8px;
        transition: all 200ms ease;
        font-size: 14px;
    }}
    .phase-active {{
        background: {ACCENT_SUBTLE};
        border-left: 3px solid {ACCENT_PRIMARY};
        font-weight: 600;
        color: {TEXT_PRIMARY};
    }}
    .phase-completed {{
        opacity: 0.7;
        color: {TEXT_SECONDARY};
    }}
    .phase-pending {{
        opacity: 0.4;
        color: {TEXT_TERTIARY};
    }}
    .phase-dot {{
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 10px;
    }}

    /* Phasen-Coach-Box */
    .coach-box {{
        background: linear-gradient(135deg, {SURFACE_1}, {SURFACE_2});
        border: 1px solid {ACCENT_PRIMARY}33;
        border-left: 3px solid {ACCENT_PRIMARY};
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
    }}
    .coach-meta {{
        text-transform: uppercase;
        font-size: 11px;
        font-weight: 600;
        color: {ACCENT_PRIMARY};
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }}
    .coach-title {{
        font-size: 18px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        margin-bottom: 6px;
    }}
    .coach-body {{
        font-size: 14px;
        color: {TEXT_SECONDARY};
        line-height: 1.5;
    }}

    /* Headings */
    h1 {{ letter-spacing: -0.02em !important; font-weight: 700 !important; }}
    h2 {{ letter-spacing: -0.01em !important; font-weight: 600 !important; }}
    h3 {{ font-weight: 600 !important; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {SURFACE_1} !important;
        border-right: 1px solid {BORDER_DEFAULT};
    }}

    /* Metric Cards */
    [data-testid="stMetricValue"] {{
        font-weight: 700 !important;
        color: {ACCENT_PRIMARY} !important;
    }}

    /* Smaller caption */
    .small-caption {{
        font-size: 12px;
        color: {TEXT_TERTIARY};
        font-style: italic;
    }}

    /* Segmented Control · Sellmo-Orange für Ausgewählt, Outline für Unausgewählt */
    [data-testid="stSegmentedControl"] button {{
        background: transparent !important;
        border: 1px solid {BORDER_DEFAULT} !important;
        border-radius: 10px !important;
        padding: 12px 20px !important;
        font-weight: 500 !important;
        color: {TEXT_PRIMARY} !important;
        transition: all 200ms ease-out !important;
    }}
    [data-testid="stSegmentedControl"] button:hover {{
        border-color: {ACCENT_PRIMARY} !important;
        color: {ACCENT_PRIMARY} !important;
    }}
    [data-testid="stSegmentedControl"] button[aria-pressed="true"],
    [data-testid="stSegmentedControl"] button[data-selected="true"] {{
        background: {ACCENT_PRIMARY} !important;
        border-color: {ACCENT_PRIMARY} !important;
        color: {BG_DEFAULT} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stSegmentedControl"] button[aria-pressed="true"]:hover,
    [data-testid="stSegmentedControl"] button[data-selected="true"]:hover {{
        background: {ACCENT_PRIMARY} !important;
        color: {BG_DEFAULT} !important;
    }}

    /* =================================================== */
    /* LANDING-PAGE CLASSES (Closed-Alpha-Login als Hero)  */
    /* Variante C · Sleak-Stimmung in Dark-Mode            */
    /* =================================================== */

    /* Streamlit Block-Container Override (1280px max — page-wide constraint) */
    .main .block-container,
    [data-testid="stMainBlockContainer"],
    section.main > div.block-container {{
        max-width: 1280px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 24px !important;
        padding-right: 24px !important;
        padding-top: 0 !important;
    }}

    .lp-container {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 32px;
    }}

    /* Hero: Zwei-Spalten-Layout */
    .lp-hero {{
        padding: 80px 0 64px 0;
    }}
    .lp-hero-grid {{
        display: grid;
        grid-template-columns: 1.1fr 0.9fr;
        gap: 64px;
        align-items: center;
    }}
    @media (max-width: 880px) {{
        .lp-hero-grid {{
            grid-template-columns: 1fr;
            gap: 40px;
        }}
    }}
    .lp-hero-wordmark {{
        margin-bottom: 24px;
        line-height: 0;
    }}
    .lp-hero-tagline {{
        font-size: 44px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        line-height: 1.08;
        letter-spacing: -0.025em;
        margin: 0 0 24px 0;
    }}
    .lp-hero-sub {{
        font-size: 17px;
        color: {TEXT_SECONDARY};
        line-height: 1.6;
        margin: 0;
        max-width: 540px;
    }}

    /* Hero-Visual rechts: Mini-FORM-Matrix-Preview */
    .lp-hero-visual {{
        background: {SURFACE_1};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 18px;
        padding: 28px;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
    }}
    .lp-hero-visual-label {{
        font-size: 11px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {ACCENT_PRIMARY};
        font-weight: 600;
        margin-bottom: 14px;
    }}
    .lp-hero-visual-title {{
        font-size: 15px;
        color: {TEXT_PRIMARY};
        font-weight: 600;
        margin-bottom: 18px;
    }}
    .lp-mini-matrix {{
        display: grid;
        grid-template-columns: 110px repeat(3, 1fr);
        gap: 8px;
        font-size: 12px;
    }}
    .lp-mini-matrix-h {{
        color: {TEXT_TERTIARY};
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        text-align: center;
        padding-bottom: 4px;
    }}
    .lp-mini-matrix-row-label {{
        color: {TEXT_PRIMARY};
        font-weight: 700;
        font-size: 13px;
        display: flex;
        align-items: center;
        letter-spacing: -0.01em;
    }}
    .lp-mini-cell {{
        background: {SURFACE_2};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 6px;
        padding: 14px 8px;
        text-align: center;
        color: {TEXT_TERTIARY};
        font-size: 14px;
        line-height: 1;
    }}
    .lp-mini-cell-filled {{
        background: {ACCENT_SUBTLE};
        border-color: {ACCENT_PRIMARY}55;
        color: {ACCENT_PRIMARY};
        font-weight: 700;
    }}

    .lp-section {{
        padding: 48px 0;
        border-top: 1px solid {BORDER_DEFAULT};
    }}

    /* Pain-Hero: fast volle Viewport-Hoehe (PAGE-OPENER), vertikal zentriert */
    /* Direkt nach Top-Nav — kein border-top (Nav hat schon border-bottom) */
    .lp-pain-hero {{
        min-height: calc(100vh - 100px);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 40px 0 80px 0;
    }}
    .lp-pain-label {{
        font-size: 36px;
        font-weight: 800;
        color: {ACCENT_PRIMARY};
        letter-spacing: -0.01em;
        text-transform: uppercase;
        margin: 0 0 32px 0;
        line-height: 1.1;
    }}
    .lp-pain-title {{
        font-size: 44px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        line-height: 1.1;
        letter-spacing: -0.025em;
        margin: 0 0 36px 0;
        max-width: 1000px;
    }}
    .lp-pain-body {{
        font-size: 19px;
        color: {TEXT_SECONDARY};
        line-height: 1.7;
        margin: 0;
        max-width: 800px;
    }}
    .lp-section-label {{
        font-size: 11px;
        font-weight: 600;
        color: {ACCENT_PRIMARY};
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 16px;
    }}
    .lp-section-title {{
        font-size: 26px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        line-height: 1.25;
        letter-spacing: -0.015em;
        margin: 0 0 20px 0;
    }}
    .lp-section-body {{
        font-size: 16px;
        color: {TEXT_SECONDARY};
        line-height: 1.65;
        margin: 0;
        max-width: 600px;
    }}

    /* Solution-Bullets */
    .lp-bullet-list {{
        margin: 24px 0 0 0;
        padding: 0;
        list-style: none;
    }}
    .lp-bullet {{
        display: flex;
        gap: 16px;
        padding: 14px 0;
        border-bottom: 1px solid {BORDER_DEFAULT};
    }}
    .lp-bullet:last-child {{ border-bottom: none; }}
    .lp-bullet-num {{
        font-size: 13px;
        font-weight: 700;
        color: {ACCENT_PRIMARY};
        min-width: 24px;
        padding-top: 2px;
    }}
    .lp-bullet-text {{
        font-size: 16px;
        color: {TEXT_PRIMARY};
        line-height: 1.55;
    }}
    .lp-bullet-text em {{
        color: {TEXT_SECONDARY};
        font-style: normal;
    }}

    /* Trust-Row */
    .lp-trust {{
        display: flex;
        flex-wrap: wrap;
        gap: 32px;
        margin-top: 24px;
    }}
    .lp-trust-item {{
        display: flex;
        flex-direction: column;
        gap: 4px;
    }}
    .lp-trust-num {{
        font-size: 28px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.02em;
        line-height: 1;
    }}
    .lp-trust-label {{
        font-size: 12px;
        color: {TEXT_TERTIARY};
        letter-spacing: 0.04em;
    }}

    /* CTA-Section */
    .lp-cta-wrap {{
        padding: 32px 0 48px 0;
    }}
    .lp-cta-headline {{
        font-size: 22px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin: 0 0 8px 0;
    }}
    .lp-cta-sub {{
        font-size: 14px;
        color: {TEXT_SECONDARY};
        margin: 0 0 20px 0;
    }}

    /* Login-Form Wrapper (max-width-discipline) */
    .lp-login-wrap {{
        max-width: 440px;
        margin: 0;
    }}

    /* Footer */
    .lp-footer {{
        padding: 24px 0 64px 0;
        border-top: 1px solid {BORDER_DEFAULT};
        color: {TEXT_TERTIARY};
        font-size: 13px;
    }}

    /* =================================================== */
    /* LANDING-PAGE · v2 · Sleak-Layout in Sellmo-Identity */
    /* =================================================== */

    /* Top-Nav (sticky, Wordmark + Login-Link rechts) */
    .lp-nav {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 0;
        border-bottom: 1px solid {BORDER_DEFAULT};
        margin-bottom: 24px;
    }}
    .lp-nav-wordmark {{ line-height: 0; }}
    .lp-nav-login {{
        font-size: 14px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        text-decoration: none;
        padding: 8px 18px;
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 8px;
        transition: all 200ms ease-out;
    }}
    .lp-nav-login:hover {{
        border-color: {ACCENT_PRIMARY};
        color: {ACCENT_PRIMARY};
    }}

    /* 4-Steps-Section ("So funktioniert sellmo") */
    .lp-steps-header {{
        text-align: center;
        margin-bottom: 56px;
    }}
    .lp-steps-title {{
        font-size: 40px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.025em;
        line-height: 1.1;
        margin: 0 0 12px 0;
    }}
    .lp-steps-sub {{
        font-size: 16px;
        color: {TEXT_SECONDARY};
        margin: 0;
    }}
    .lp-steps-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 32px;
    }}
    .lp-step {{
        position: relative;
        padding: 0 0 0 20px;
        border-left: 2px solid {ACCENT_PRIMARY};
    }}
    .lp-step-num {{
        font-size: 96px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        opacity: 0.06;
        letter-spacing: -0.04em;
        line-height: 1;
        margin: 0 0 -56px -8px;
        position: relative;
        z-index: 0;
    }}
    .lp-step-title {{
        font-size: 18px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin: 0 0 12px 0;
        line-height: 1.3;
        position: relative;
        z-index: 1;
    }}
    .lp-step-body {{
        font-size: 14px;
        color: {TEXT_SECONDARY};
        line-height: 1.55;
        margin: 0;
        position: relative;
        z-index: 1;
    }}

    /* Use-Case-Grid (2x2 Card-Layout, Sleak-Style) */
    .lp-usecase-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(440px, 1fr));
        gap: 20px;
    }}
    .lp-usecase-card {{
        background: {SURFACE_1};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 16px;
        padding: 32px 28px;
        transition: border-color 200ms ease-out, transform 200ms ease-out;
    }}
    .lp-usecase-card:hover {{
        border-color: {ACCENT_PRIMARY}80;
        transform: translateY(-2px);
    }}
    .lp-usecase-visual {{
        margin-bottom: 24px;
        min-height: 80px;
        display: flex;
        align-items: center;
        gap: 16px;
    }}
    .lp-usecase-chip {{
        display: inline-block;
        padding: 5px 12px;
        background: {SURFACE_2};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 999px;
        font-size: 12px;
        color: {TEXT_SECONDARY};
        margin: 0 6px 6px 0;
    }}
    .lp-usecase-avatar {{
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: {SURFACE_2};
        border: 2px solid {ACCENT_PRIMARY};
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 18px;
        color: {ACCENT_PRIMARY};
    }}
    .lp-usecase-avatar-muted {{
        border-color: {TEXT_TERTIARY};
        color: {TEXT_SECONDARY};
    }}
    .lp-usecase-title {{
        font-size: 22px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin: 0 0 12px 0;
        letter-spacing: -0.015em;
    }}
    .lp-usecase-body {{
        font-size: 14px;
        color: {TEXT_SECONDARY};
        line-height: 1.6;
        margin: 0;
    }}
    .lp-usecase-progressrow {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 6px 0;
        font-size: 12px;
    }}
    .lp-usecase-progress-label {{
        min-width: 150px;
        color: {TEXT_SECONDARY};
    }}
    .lp-usecase-progress-bar {{
        flex: 1;
        height: 6px;
        background: {SURFACE_2};
        border-radius: 3px;
        overflow: hidden;
    }}
    .lp-usecase-progress-fill {{
        height: 100%;
        background: {ACCENT_PRIMARY};
        border-radius: 3px;
    }}

    /* Bottom-CTA (Login + Account-Anfrage) */
    .lp-cta-final {{
        text-align: center;
        padding: 80px 0 32px 0;
        border-top: 1px solid {BORDER_DEFAULT};
    }}
    .lp-cta-final-title {{
        font-size: 36px;
        font-weight: 800;
        color: {TEXT_PRIMARY};
        letter-spacing: -0.02em;
        line-height: 1.15;
        margin: 0 0 12px 0;
    }}
    .lp-cta-final-sub {{
        font-size: 16px;
        color: {TEXT_SECONDARY};
        margin: 0 0 32px 0;
    }}
    .lp-cta-buttons {{
        display: flex;
        gap: 12px;
        justify-content: center;
        flex-wrap: wrap;
    }}
    .lp-btn-primary {{
        display: inline-block;
        padding: 14px 32px;
        background: {ACCENT_PRIMARY};
        color: {BG_DEFAULT} !important;
        border: none;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        text-decoration: none !important;
        transition: all 200ms ease-out;
    }}
    .lp-btn-primary:hover {{
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(51, 232, 142, 0.30);
        text-decoration: none !important;
    }}
    .lp-btn-secondary {{
        display: inline-block;
        padding: 14px 32px;
        background: transparent;
        color: {TEXT_PRIMARY} !important;
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 10px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        text-decoration: none !important;
        transition: all 200ms ease-out;
    }}
    .lp-btn-secondary:hover {{
        border-color: {ACCENT_PRIMARY};
        color: {ACCENT_PRIMARY} !important;
        text-decoration: none !important;
    }}

    /* Nav-Login auch nicht unterstreichen */
    .lp-nav-login {{
        text-decoration: none !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-size: 12px;
    }}
    .lp-nav-login:hover {{
        text-decoration: none !important;
    }}

    /* =================================================== */
    /* CC-COMPONENTS · CloserCoach-Adaption (2026-07-14)   */
    /* =================================================== */

    /* Pill-CTA — grüner Vollbreit-Button mit Pfeil */
    .cc-cta-pill {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        background: {ACCENT_PRIMARY};
        color: #000;
        font-weight: 600;
        font-size: 17px;
        padding: 20px 40px;
        border: none;
        border-radius: 34px;
        cursor: pointer;
        text-decoration: none !important;
        transition: all 200ms ease-out;
        width: 100%;
        max-width: 480px;
        text-align: center;
    }}
    .cc-cta-pill:hover {{
        transform: translateY(-1px);
        box-shadow: 0 8px 24px rgba(51, 232, 142, 0.35);
        color: #000 !important;
    }}
    .cc-cta-cobalt {{
        background: {ACCENT_COBALT};
        color: #FFF !important;
        font-weight: 600;
        font-size: 15px;
        padding: 14px 26px;
        border: none;
        border-radius: 12px;
        cursor: pointer;
    }}

    /* Filter-Chip-Row — horizontal, grün-fill für active */
    .cc-chip-row {{
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin: 12px 0 20px;
    }}
    .cc-chip {{
        padding: 10px 20px;
        border-radius: 22px;
        border: 1px solid {BORDER_DEFAULT};
        color: {TEXT_PRIMARY};
        font-size: 14px;
        background: transparent;
        transition: all 150ms ease-out;
        cursor: pointer;
    }}
    .cc-chip:hover {{
        border-color: {ACCENT_PRIMARY};
    }}
    .cc-chip.active {{
        background: {ACCENT_PRIMARY};
        color: #000;
        border-color: {ACCENT_PRIMARY};
        font-weight: 500;
    }}

    /* Chat-Bubble im CloserCoach-Stil (asymmetrischer Radius) */
    .cc-bubble-wrap {{
        display: flex;
        flex-direction: column;
        gap: 14px;
        margin: 12px 0;
    }}
    .cc-bubble {{
        padding: 14px 16px;
        border-radius: 22px;
        font-size: 16px;
        line-height: 1.4;
        max-width: 90%;
        color: #FFF;
    }}
    .cc-bubble-rep {{
        background: {ACCENT_BLUE};
        align-self: flex-start;
        border-bottom-left-radius: 6px;
    }}
    .cc-bubble-ai {{
        background: {SURFACE_2};
        align-self: flex-end;
        border-bottom-right-radius: 6px;
    }}

    /* Inline-Feedback-Badge (innerhalb der AI-Bubble) */
    .cc-fb-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 13px;
        font-weight: 500;
    }}
    .cc-fb-icon {{
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: inline-grid;
        place-items: center;
        font-size: 11px;
        font-weight: 700;
    }}
    .cc-fb-great {{ color: {ACCENT_PRIMARY}; }}
    .cc-fb-great .cc-fb-icon {{ background: {ACCENT_PRIMARY}; color: #000; }}
    .cc-fb-analyzing {{ color: {ACCENT_AMBER}; }}
    .cc-fb-analyzing .cc-fb-icon {{ background: {ACCENT_AMBER}; color: #000; }}
    .cc-fb-keepgoing {{ color: {ACCENT_AMBER}; }}
    .cc-fb-keepgoing .cc-fb-icon {{ background: {ACCENT_AMBER}; color: #000; }}

    /* Session-Timer-Header (oberhalb Chat) */
    .cc-timer-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        background: {SURFACE_1};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 14px;
        margin-bottom: 16px;
    }}
    .cc-timer-persona {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .cc-timer-avatar {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: {SURFACE_2};
        display: grid;
        place-items: center;
        font-weight: 700;
        color: {ACCENT_PRIMARY};
        font-size: 14px;
    }}
    .cc-timer-name {{
        font-size: 15px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
    }}
    .cc-timer-value {{
        font-family: ui-monospace, 'SF Mono', Menlo, monospace;
        font-size: 14px;
        color: {ACCENT_PRIMARY};
        font-weight: 600;
    }}

    /* Checkpoint-Counter (Live-Progress unten am Chat) */
    .cc-checkpoint {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: {SURFACE_1};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 12px;
        margin: 12px 0;
    }}
    .cc-checkpoint-badge {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        border: 3px solid {ACCENT_AMBER};
        color: {ACCENT_AMBER};
        display: grid;
        place-items: center;
        font-weight: 700;
        font-size: 13px;
        flex-shrink: 0;
        transition: all 250ms ease-out;
    }}
    .cc-checkpoint-badge.complete {{
        border-color: {ACCENT_PRIMARY};
        color: {ACCENT_PRIMARY};
    }}
    .cc-checkpoint-label {{
        color: {TEXT_PRIMARY};
        font-size: 15px;
        font-weight: 500;
    }}

    /* Score-Ring (Hero + Compact) */
    .cc-ring-wrap {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
    }}
    .cc-top-pill {{
        display: inline-block;
        padding: 4px 14px;
        background: {ACCENT_SUBTLE};
        color: {ACCENT_PRIMARY};
        border: 1px solid {ACCENT_PRIMARY};
        border-radius: 14px;
        font-size: 12px;
        font-weight: 600;
    }}
    .cc-ring {{
        position: relative;
        width: 200px;
        height: 200px;
    }}
    .cc-ring svg {{ display: block; }}
    .cc-ring-label {{
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        font-weight: 700;
        color: {ACCENT_PRIMARY};
    }}
    .cc-ring-label.hero {{ font-size: 80px; letter-spacing: -0.02em; }}
    .cc-ring-label.compact {{ font-size: 28px; }}
    .cc-ring-caption {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}

    /* KPI-Tile (2-Spalten-Grid) */
    .cc-kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin: 16px 0;
    }}
    .cc-kpi {{
        background: {SURFACE_1};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 16px;
        padding: 18px 20px;
    }}
    .cc-kpi-value {{
        font-size: 28px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        line-height: 1.1;
        margin-bottom: 4px;
    }}
    .cc-kpi-label {{
        font-size: 13px;
        color: {TEXT_SECONDARY};
        line-height: 1.4;
    }}

    /* Talk/Listen-Ratio-Bar */
    .cc-tl {{
        background: {SURFACE_1};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 14px;
        padding: 14px 18px;
        margin: 12px 0;
    }}
    .cc-tl-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        font-size: 14px;
        color: {TEXT_PRIMARY};
    }}
    .cc-tl-label {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }}
    .cc-tl-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }}
    .cc-tl-bar {{
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
        display: flex;
    }}
    .cc-tl-bar-talk {{ background: {ACCENT_BLUE}; }}
    .cc-tl-bar-listen {{ background: {ACCENT_PRIMARY}; }}

    /* Coach-Suggestion-Reply mit Persona-Foto */
    .cc-coach-reply {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin: 12px 0;
    }}
    .cc-coach-reply-avatar {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: {SURFACE_2};
        display: grid;
        place-items: center;
        font-weight: 700;
        color: {ACCENT_PRIMARY};
        flex-shrink: 0;
        font-size: 15px;
    }}
    .cc-coach-reply-bubble {{
        background: {SURFACE_2};
        color: #FFF;
        padding: 14px 16px;
        border-radius: 18px;
        border-top-left-radius: 6px;
        font-size: 15px;
        line-height: 1.4;
        max-width: 90%;
    }}
    .cc-coach-reply-label {{
        font-size: 12px;
        color: {ACCENT_PRIMARY};
        font-weight: 600;
        margin-bottom: 8px;
        letter-spacing: 0.02em;
    }}

    /* Rot-hinterlegte Rep-Message im Feedback */
    .cc-error-bubble {{
        background: {ACCENT_DEEP_RED};
        color: #FFF;
        padding: 14px 16px;
        border-radius: 18px;
        border-top-left-radius: 6px;
        font-size: 15px;
        line-height: 1.4;
        max-width: 90%;
        margin: 8px 0;
    }}

    /* Cash-Card (Objection-Playbook, kategorie-farbig) */
    .cc-cash-card {{
        background: transparent;
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 14px;
        padding: 18px 16px;
        margin: 12px 0;
    }}
    .cc-cash-card.cat-price   {{ border-color: {CAT_PRICE_BORDER}; }}
    .cc-cash-card.cat-comp    {{ border-color: {CAT_COMPETITION_BORDER}; }}
    .cc-cash-card.cat-timing  {{ border-color: {CAT_TIMING_BORDER}; }}
    .cc-cash-card.cat-trust   {{ border-color: {CAT_TRUST_BORDER}; }}
    .cc-cash-card.cat-auth    {{ border-color: {CAT_AUTHORITY_BORDER}; }}
    .cc-cash-card.cat-urg     {{ border-color: {CAT_URGENCY_BORDER}; }}

    .cc-cash-head {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
    }}
    .cc-cash-icon {{
        width: 44px;
        height: 44px;
        border-radius: 10px;
        display: grid;
        place-items: center;
        font-size: 20px;
        flex-shrink: 0;
    }}
    .cc-cash-icon.cat-price   {{ background: {CAT_PRICE_FILL}; }}
    .cc-cash-icon.cat-comp    {{ background: {CAT_COMPETITION_FILL}; }}
    .cc-cash-icon.cat-timing  {{ background: {CAT_TIMING_FILL}; }}
    .cc-cash-icon.cat-trust   {{ background: {CAT_TRUST_FILL}; }}
    .cc-cash-icon.cat-auth    {{ background: {CAT_AUTHORITY_FILL}; }}
    .cc-cash-icon.cat-urg     {{ background: {CAT_URGENCY_FILL}; }}
    .cc-cash-title {{
        font-size: 17px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        flex: 1;
    }}
    .cc-cash-step {{
        display: grid;
        grid-template-columns: 32px 1fr;
        gap: 12px;
        padding: 10px 0;
        position: relative;
    }}
    .cc-step-num {{
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 1.5px solid;
        display: grid;
        place-items: center;
        font-size: 13px;
        font-weight: 600;
    }}
    .cc-cash-card.cat-price .cc-step-num,
    .cc-cash-card.cat-price .cc-step-label {{ color: {CAT_PRICE_BORDER}; }}
    .cc-cash-card.cat-price .cc-step-num {{ border-color: {CAT_PRICE_BORDER}; }}
    .cc-cash-card.cat-comp .cc-step-num,
    .cc-cash-card.cat-comp .cc-step-label {{ color: {CAT_COMPETITION_BORDER}; }}
    .cc-cash-card.cat-comp .cc-step-num {{ border-color: {CAT_COMPETITION_BORDER}; }}
    .cc-cash-card.cat-timing .cc-step-num,
    .cc-cash-card.cat-timing .cc-step-label {{ color: {CAT_TIMING_BORDER}; }}
    .cc-cash-card.cat-timing .cc-step-num {{ border-color: {CAT_TIMING_BORDER}; }}
    .cc-cash-card.cat-trust .cc-step-num,
    .cc-cash-card.cat-trust .cc-step-label {{ color: {CAT_TRUST_BORDER}; }}
    .cc-cash-card.cat-trust .cc-step-num {{ border-color: {CAT_TRUST_BORDER}; }}
    .cc-cash-card.cat-auth .cc-step-num,
    .cc-cash-card.cat-auth .cc-step-label {{ color: {CAT_AUTHORITY_BORDER}; }}
    .cc-cash-card.cat-auth .cc-step-num {{ border-color: {CAT_AUTHORITY_BORDER}; }}
    .cc-cash-card.cat-urg .cc-step-num,
    .cc-cash-card.cat-urg .cc-step-label {{ color: {CAT_URGENCY_BORDER}; }}
    .cc-cash-card.cat-urg .cc-step-num {{ border-color: {CAT_URGENCY_BORDER}; }}
    .cc-step-label {{
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        text-transform: uppercase;
    }}
    .cc-step-text {{
        font-size: 14px;
        line-height: 1.5;
        color: {TEXT_PRIMARY};
    }}
    .cc-step-line {{
        position: absolute;
        left: 15px;
        top: 34px;
        bottom: -6px;
        width: 1.5px;
        opacity: 0.5;
    }}
    .cc-cash-card.cat-price  .cc-step-line {{ background: {CAT_PRICE_BORDER}; }}
    .cc-cash-card.cat-comp   .cc-step-line {{ background: {CAT_COMPETITION_BORDER}; }}
    .cc-cash-card.cat-timing .cc-step-line {{ background: {CAT_TIMING_BORDER}; }}
    .cc-cash-card.cat-trust  .cc-step-line {{ background: {CAT_TRUST_BORDER}; }}
    .cc-cash-card.cat-auth   .cc-step-line {{ background: {CAT_AUTHORITY_BORDER}; }}
    .cc-cash-card.cat-urg    .cc-step-line {{ background: {CAT_URGENCY_BORDER}; }}

    /* Persona-Card-Grid (Setup-Screen 4-Kachel) */
    .cc-persona-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin: 16px 0 24px;
    }}
    .cc-persona-card {{
        background: {SURFACE_1};
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 18px;
        overflow: hidden;
        cursor: pointer;
        transition: all 200ms ease-out;
    }}
    .cc-persona-card:hover {{
        border-color: {ACCENT_PRIMARY};
        transform: translateY(-2px);
    }}
    .cc-persona-card.selected {{
        border-color: {ACCENT_PRIMARY};
        box-shadow: 0 0 0 2px {ACCENT_PRIMARY};
    }}
    .cc-persona-photo {{
        height: 140px;
        background: radial-gradient(circle at 50% 40%, {ACCENT_SUBTLE}, #000);
        position: relative;
        display: grid;
        place-items: center;
        font-size: 56px;
        line-height: 1;
    }}
    .cc-persona-body {{
        padding: 12px 14px 16px;
    }}
    .cc-persona-name {{
        font-size: 15px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 3px;
    }}
    .cc-persona-meta {{
        font-size: 12px;
        color: {TEXT_SECONDARY};
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    .cc-diff-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }}
    .cc-diff-easy   {{ background: {ACCENT_PRIMARY}; }}
    .cc-diff-med    {{ background: {ACCENT_AMBER}; }}
    .cc-diff-hard   {{ background: {ACCENT_RED}; }}

    /* Grade-Selector (5-Stufen als Chips mit Farb-Dot) */
    .cc-grade-row {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
        margin: 16px 0 24px;
    }}

    /* Wizard-Progress-Bar (8-Segment) */
    .cc-wizard-bar {{
        display: flex;
        gap: 4px;
        margin: 16px 0;
    }}
    .cc-wizard-seg {{
        flex: 1;
        height: 4px;
        border-radius: 2px;
        background: rgba(255,255,255,0.20);
    }}
    .cc-wizard-seg.done {{
        background: #FFF;
    }}

    /* Active-Status-Pill (grüner Dot + Text) */
    .cc-active-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 4px 12px;
        background: {ACCENT_SUBTLE};
        color: {ACCENT_PRIMARY};
        border: 1px solid {ACCENT_PRIMARY};
        border-radius: 14px;
        font-size: 12px;
        font-weight: 500;
    }}
    .cc-active-pill::before {{
        content: "";
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: {ACCENT_PRIMARY};
    }}

    /* Personalisierte Coach-Card (nach Session) */
    .cc-coach-card {{
        background: {ACCENT_SUBTLE};
        border-radius: 20px;
        padding: 16px 18px;
        margin: 16px 0;
        display: flex;
        gap: 12px;
        align-items: flex-start;
    }}
    .cc-coach-card-avatar {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: {SURFACE_2};
        display: grid;
        place-items: center;
        color: {ACCENT_PRIMARY};
        font-weight: 700;
        flex-shrink: 0;
    }}
    .cc-coach-card-body {{
        flex: 1;
    }}
    .cc-coach-card-label {{
        font-size: 12px;
        color: {ACCENT_PRIMARY};
        font-weight: 600;
        margin-bottom: 6px;
    }}
    .cc-coach-card-text {{
        font-size: 15px;
        color: {TEXT_PRIMARY};
        line-height: 1.45;
    }}

    /* Split-CTA (Share + Continue) */
    .cc-split-cta {{
        display: flex;
        gap: 12px;
        margin: 24px 0 12px;
    }}
    .cc-split-share {{
        flex: 0 0 40%;
        padding: 14px 18px;
        border: 1px solid {BORDER_DEFAULT};
        border-radius: 26px;
        color: {TEXT_PRIMARY};
        background: transparent;
        font-size: 14px;
        font-weight: 500;
        text-align: center;
        cursor: pointer;
    }}
    .cc-split-continue {{
        flex: 1;
        padding: 14px 18px;
        background: #FFF;
        color: #000;
        border-radius: 26px;
        border: none;
        font-size: 15px;
        font-weight: 600;
        text-align: center;
        cursor: pointer;
    }}
</style>
"""


# ============================================================
# API-CLIENT
# ============================================================

def get_client():
    # Priorität: 1) Streamlit-Secrets (Cloud), 2) OS-Environment (lokal)
    api_key = ""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "").strip()
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        st.error("ANTHROPIC_API_KEY ist nicht gesetzt (weder in Secrets noch in Environment).")
        st.stop()
    return Anthropic(api_key=api_key)


def _clean_json(raw):
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    first_brace = raw.find("{")
    if first_brace > 0:
        raw = raw[first_brace:]
    last_brace = raw.rfind("}")
    if last_brace != -1:
        raw = raw[:last_brace + 1]
    return raw


def _calc_cost(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return 0.0
    in_t = getattr(usage, "input_tokens", 0)
    out_t = getattr(usage, "output_tokens", 0)
    return (in_t * COST_PER_INPUT_TOKEN_EUR + out_t * COST_PER_OUTPUT_TOKEN_EUR)


def _api_call(system_prompt, user_message, max_tokens, temperature):
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    cost = _calc_cost(response)
    raw = _clean_json(response.content[0].text.strip())
    return raw, cost


# ============================================================
# KI-CALLS
# ============================================================

def _inject_persona(prompt_template, persona):
    persona_block = (
        f"- ID: {persona['id']}\n"
        f"- Name: {persona['name']}\n"
        f"- Alter: {persona['alter']}\n"
        f"- Job: {persona['job']}\n"
        f"- Kern-Einwand-Kategorie: {persona['kern_einwand_kategorie']}\n"
        f"- Discovery-Profil: {persona['discovery_summary']}\n"
        f"- Eroeffnungs-Einwand: {persona['opening_einwand']}\n"
        f"- Personality-Hinweise (intern): {persona['personality_notes']}"
    )
    placeholder = (
        "[wird zur Laufzeit aus personas.json injiziert]\n"
        "- ID: {persona_id}\n"
        "- Name: {persona_name}\n"
        "- Alter: {persona_alter}\n"
        "- Job: {persona_job}\n"
        "- Kern-Einwand-Kategorie: {persona_kern_einwand_kategorie}\n"
        "- Discovery-Profil: {persona_discovery_summary}\n"
        "- Eroeffnungs-Einwand: {persona_opening_einwand}\n"
        "- Personality-Hinweise (NICHT direkt aussprechen, intern verwenden): {persona_personality_notes}"
    )
    if placeholder in prompt_template:
        return prompt_template.replace(placeholder, persona_block)
    return prompt_template + "\n\nPERSONA:\n" + persona_block


def call_customer_bot(persona, conversation_history, programm_info=None, customer_goal=None):
    """KI spielt Customer (v3.0 · form_type x difficulty basiert)."""
    form_type = persona.get("form_type", "F")
    difficulty = persona.get("difficulty", 1)

    if not conversation_history:
        opening = MVP_OPENING_EINWAENDE.get(
            (form_type, difficulty), persona.get("opening_einwand", "")
        )
        return {
            "customer_utterance": opening,
            "internal_state": {
                "stage_in_conversation": "opening",
                "active_concern": persona.get("kern_einwand_kategorie", "Geld"),
                "trust_level": "medium" if difficulty <= 2 else "low",
                "open_to_close": False,
                "grad_konsistenz_check": f"Zelle {form_type}{difficulty} · {persona.get('grad_label', '?')}",
            }
        }, 0.0

    # v3.0 Prompt kennt die 4 Personas + 5 Grade selbst, keine Persona-Injektion noetig
    user_message = json.dumps({
        "form_type": form_type,
        "difficulty": difficulty,
        "conversation_history": conversation_history,
        "programm_info": programm_info,
        "customer_goal": customer_goal,
    }, ensure_ascii=False)
    try:
        raw, cost = _api_call(CUSTOMER_BOT_PROMPT, user_message, MAX_TOKENS_DEFAULT, TEMPERATURE_BOT)
        return json.loads(raw), cost
    except Exception as e:
        return {
            "customer_utterance": f"[Bot-Fehler: {type(e).__name__}]",
            "internal_state": {"stage_in_conversation": "exploring", "active_concern": "unknown",
                                "trust_level": "medium", "open_to_close": False,
                                "grad_konsistenz_check": "error"}
        }, 0.0


def call_closer_bot(persona, conversation_history):
    """KI spielt Closer (Customer-Modus)."""
    system_prompt = _inject_persona(CLOSER_BOT_PROMPT, persona)
    user_message = json.dumps({"conversation_history": conversation_history}, ensure_ascii=False)
    try:
        raw, cost = _api_call(system_prompt, user_message, MAX_TOKENS_DEFAULT, TEMPERATURE_BOT)
        return json.loads(raw), cost
    except Exception as e:
        return {
            "closer_utterance": f"[Bot-Fehler: {type(e).__name__}]",
            "phase_now": "1", "muster_used": "error", "internal_reasoning": "error"
        }, 0.0


def call_phasen_coach(persona, conversation_history, current_phase, mode,
                       pricing_info=None, customer_goal=None, programm_info=None):
    """Phasen-Coach gibt didaktische Hilfestellung. mode: 'easy' oder 'medium'."""
    # These #9: letzter Closer-Move explizit als Kontext mitschicken,
    # damit Suggest-Optionen sich an dem realen letzten Move ausrichten
    last_closer_move = next(
        (m["text"] for m in reversed(conversation_history) if m["role"] == "closer"),
        None
    )
    user_message = json.dumps({
        "conversation_history": conversation_history,
        "persona_profile": {
            "id": persona.get("id"),
            "name": persona.get("name"),
            "kern_einwand_kategorie": persona.get("kern_einwand_kategorie"),
            "discovery_summary": persona.get("discovery_summary"),
            "form_type": persona.get("form_type"),  # v3.0/v2.5.1: FORM-Achse
            "difficulty": persona.get("difficulty"),  # v3.0/v2.5.1: 1-5 Grad
            "grad_label": persona.get("grad_label"),  # v3.0/v2.5.1: Kooperativ..Endgegner
        },
        "current_phase": current_phase,
        "mode": mode,
        "last_closer_move": last_closer_move,
        "pricing_info": pricing_info,
        "customer_goal": customer_goal,
        "programm_info": programm_info,
    }, ensure_ascii=False)
    try:
        raw, cost = _api_call(PHASEN_COACH_PROMPT, user_message,
                                MAX_TOKENS_PHASEN_COACH, TEMPERATURE_COACH)
        return json.loads(raw), cost
    except Exception as e:
        return {"error": str(e)}, 0.0


def call_feedback_coach(last_user_utterance, conversation_history, persona, mode, evaluating_role="closer"):
    """
    Feedback-Coach bewertet methodisch.
    evaluating_role: "closer" (default) — User-Closer-Aussagen bewertet
                     "ai_closer" — KI-Closer-Aussagen werden bewertet (Customer-Modus)
    """
    user_message = json.dumps({
        "last_closer_utterance": last_user_utterance,
        "conversation_history": conversation_history,
        "persona_profile": {
            "id": persona["id"],
            "name": persona["name"],
            "kern_einwand_kategorie": persona["kern_einwand_kategorie"],
            "discovery_summary": persona["discovery_summary"]
        },
        "mode": mode,
        "evaluating_role": evaluating_role
    }, ensure_ascii=False)
    max_t = MAX_TOKENS_COACH_END if mode == "end_of_call" else MAX_TOKENS_COACH_LIVE
    try:
        raw, cost = _api_call(FEEDBACK_COACH_PROMPT, user_message, max_t, TEMPERATURE_COACH)
        return json.loads(raw), cost
    except json.JSONDecodeError as e:
        return {"error": f"JSON-Parse-Fehler: {e}"}, 0.0
    except Exception as e:
        return {"error": str(e)}, 0.0


# ============================================================
# SESSION-STATE
# ============================================================

def init_session_state():
    defaults = {
        "session_started": False,
        "session_ended": False,
        "persona": None,
        "role": "closer",  # closer | customer
        "coach_mode": "easy",  # easy | medium | hard (was 'difficulty' pre-2026-06-03)
        "mvp_persona": "F",  # F | O | R | M — MVP-Trainings-Matrix v1.0 Persona-Achse
        "mvp_grad": 1,       # 1..5 — MVP-Trainings-Matrix v1.0 Grad-Achse
        "feedback_mode": "end_of_call",
        "conversation_history": [],
        "customer_internal_state": None,
        "live_feedback_history": [],
        "end_of_call_report": None,
        "total_cost_eur": 0.0,
        "turn_count": 0,
        "started_at": None,
        "current_phase": None,
        "phase_history": [],
        "phasen_coach_output": None,
        "pending_user_input": None,
        "last_phase_regression": None,  # These #14: Self-Correction-Banner
        "pricing_info": None,  # These #15: konfigurierbares Pricing
        "customer_goal": None,  # SOHF v2.0 Patch #53: Customer-Ziel Pflichtfeld
        "programm_info": None,  # NEU 31.05.: vollstaendige Programm-Beschreibung-Spec NEU-4
        "session_log": [],  # Session-Logging-System (30.05. nachmittags): jede Aktion mit Timestamp
        "session_feedback": {},  # Pro markierter Turn: {turn_n: "feedback_text"}
        "session_feedback_global": "",  # Gesamt-Session-Feedback
        "session_feedback_saved": False,  # Verhindert Doppel-Speichern
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_session():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    init_session_state()


# ============================================================
# SESSION-LOGGING-SYSTEM (30.05.2026 nachmittags)
# ============================================================

def _log_event(event_type, **kwargs):
    """Append event to session_log with timestamp + turn_n context."""
    if "session_log" not in st.session_state:
        st.session_state.session_log = []
    entry = {
        "type": event_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "turn_n": st.session_state.get("turn_count", 0),
    }
    entry.update(kwargs)
    st.session_state.session_log.append(entry)


def _save_session_log_to_file():
    """Schreibe das gesamte session_log + session_feedback als Markdown-Archiv."""
    if st.session_state.get("session_feedback_saved"):
        return None
    from pathlib import Path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    feedback_dir = APP_DIR.parent / "Feedback"
    feedback_dir.mkdir(exist_ok=True)
    file_path = feedback_dir / f"session_{timestamp}.md"

    persona = st.session_state.get("persona", {})
    role = st.session_state.get("role", "?")
    coach_mode = st.session_state.get("coach_mode", "?")
    pricing = st.session_state.get("pricing_info") or {}
    customer_goal = st.session_state.get("customer_goal") or "(nicht gesetzt)"

    lines = [
        f"# Sellmo Session-Log · {timestamp}",
        "",
        f"**Persona:** {persona.get('name', '?')} ({persona.get('id', '?')}) · Zelle {persona.get('form_type','?')}{persona.get('difficulty','?')} · {persona.get('grad_label','?')}",
        f"**Role:** {role}",
        f"**Coach-Mode:** {coach_mode}",
        f"**Pricing:** {pricing.get('amount', '?')} · {pricing.get('time_per_week', '?')}",
        f"**Customer-Ziel:** {customer_goal}",
        f"**Turns:** {st.session_state.get('turn_count', 0)}",
        f"**Total Cost:** {st.session_state.get('total_cost_eur', 0.0):.4f} EUR",
        "",
        "---",
        "",
        "## Session-Verlauf · Chronologisch",
        "",
    ]

    session_log = st.session_state.get("session_log", [])
    session_feedback = st.session_state.get("session_feedback", {})
    for entry in session_log:
        ts = entry.get("timestamp", "?")
        etype = entry.get("type", "?")
        turn_n = entry.get("turn_n", "?")
        lines.append(f"### Turn {turn_n} · {ts} · `{etype}`")
        for k, v in entry.items():
            if k in ("type", "timestamp", "turn_n"):
                continue
            if isinstance(v, (dict, list)):
                v_str = json.dumps(v, ensure_ascii=False, indent=2)
                lines.append(f"- **{k}:**\n```json\n{v_str}\n```")
            else:
                lines.append(f"- **{k}:** {v}")
        # Wenn Feedback fuer diesen Turn vorliegt: anhaengen
        fb_for_turn = session_feedback.get(str(turn_n))
        if fb_for_turn and etype == "feedback_marker":
            lines.append(f"\n> **Christian-Feedback (markiert):** {fb_for_turn}\n")
        lines.append("")

    # Globales Session-Feedback
    global_fb = st.session_state.get("session_feedback_global", "").strip()
    if global_fb:
        lines.append("---")
        lines.append("")
        lines.append("## Gesamt-Session-Feedback (Christian)")
        lines.append("")
        lines.append(global_fb)
        lines.append("")

    # End-of-Call-Report (falls vorhanden)
    eoc = st.session_state.get("end_of_call_report")
    if eoc:
        lines.append("---")
        lines.append("")
        lines.append("## End-of-Call-Auswertung (Feedback-Coach)")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(eoc, ensure_ascii=False, indent=2))
        lines.append("```")

    file_path.write_text("\n".join(lines), encoding="utf-8")
    st.session_state.session_feedback_saved = True
    return str(file_path)


# ============================================================
# PHASEN-LEISTE
# ============================================================

PHASE_DEFINITIONS = [
    # P-3-Fix (01.06.): EPISCH-Notation in Sidebar.
    # (phase_id, episch_letter, episch_name)
    ("Pre-0", "•", "Vertrauens-Baseline (Wütender)"),
    ("1", "E", "Entschärfen"),
    ("2", "P", "Präzisieren"),
    ("3", "I", "Isolieren"),
    ("4", "S", "Sichtweise"),
    ("5", "C", "Commitment"),
    ("6", "H", "Handlung"),
]


def render_phase_bar():
    persona = st.session_state.persona
    show_pre0 = bool(persona) and persona.get("persona_flag") in ("wuetend", "wuetender", "trauma")
    current = str(st.session_state.current_phase) if st.session_state.current_phase is not None else None
    visited = set(str(p) for p in st.session_state.phase_history)

    html_parts = ['<div class="phase-bar">']
    html_parts.append('<div class="coach-meta" style="margin-bottom: 12px;">EPISCH-Phasen-Pfad</div>')
    for phase, episch_letter, label in PHASE_DEFINITIONS:
        if phase == "Pre-0" and not show_pre0:
            continue
        if phase == current:
            klass = "phase-active"
            dot_color = ACCENT_PRIMARY
        elif phase in visited:
            klass = "phase-completed"
            dot_color = SUCCESS
        else:
            klass = "phase-pending"
            dot_color = TEXT_TERTIARY

        # P-3-Fix (01.06.): EPISCH-Buchstabe prominent statt "P1"
        html_parts.append(
            f'<div class="phase-item {klass}">'
            f'<span class="phase-dot" style="background:{dot_color};"></span>'
            f'<strong style="margin-right: 8px; font-size: 15px; color:{dot_color};">{episch_letter}</strong> '
            f'<span style="font-size: 13px;">{label}</span>'
            f'</div>'
        )
    html_parts.append('</div>')
    st.markdown("\n".join(html_parts), unsafe_allow_html=True)


# ============================================================
# SETUP-SCREEN
# ============================================================

def render_setup_screen():
    # Sellmo-Wordmark (Inline-SVG für scharfe Darstellung · "mo" in Akzentfarbe)
    st.markdown(
        '<div style="margin: 8px 0 4px 0;">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="44" viewBox="0 0 180 44" role="img" aria-label="sellmo">'
        '<text x="0" y="34" font-family="Inter, -apple-system, BlinkMacSystemFont, sans-serif" font-weight="800" font-size="40" letter-spacing="-1.6">'
        '<tspan fill="#F5F5F7">sell</tspan><tspan fill="#33E88E">mo</tspan>'
        '</text>'
        '</svg>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="color:{TEXT_TERTIARY}; margin-bottom: 4px; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;">'
        f"Trainings-App · Einwandbehandlung"
        f"</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="color:{TEXT_SECONDARY}; margin-bottom: 32px; font-size: 16px;">'
        f"Übe Einwandbehandlung gegen einen KI-Kunden, oder spiele den Kunden gegen einen KI-Closer. "
        f"4 Kundentypen · 5 Schwierigkeitsgrade · EPISCH-Framework · echte DACH-Sprache."
        f"</div>",
        unsafe_allow_html=True
    )

    # === 1. Rolle ===
    st.markdown("### Welche Rolle spielst du?")
    role = st.segmented_control(
        " ",
        options=["closer", "customer"],
        format_func=lambda x: {
            "closer": "Closer (du verkaufst)",
            "customer": "Kunde (du wehrst ab)"
        }[x],
        selection_mode="single",
        default="closer",
        label_visibility="collapsed",
        key="role_segctl"
    )

    # === 2. Persona (MVP-Matrix v1.0 · 4 Kundentypen) ===
    st.markdown("### Welchen Kundentyp spielst du gegen?")
    mvp_persona = st.segmented_control(
        " ",
        options=["F", "O", "R", "M"],
        format_func=lambda x: {
            "F": f"F · {MVP_PERSONAS['F']['name']} · {MVP_PERSONAS['F']['kurz']}",
            "O": f"O · {MVP_PERSONAS['O']['name']} · {MVP_PERSONAS['O']['kurz']}",
            "R": f"R · {MVP_PERSONAS['R']['name']} · {MVP_PERSONAS['R']['kurz']}",
            "M": f"M · {MVP_PERSONAS['M']['name']} · {MVP_PERSONAS['M']['kurz']}",
        }[x],
        selection_mode="single",
        default="F",
        label_visibility="collapsed",
        key="mvp_persona_segctl"
    )
    if mvp_persona is None:
        mvp_persona = "F"

    # === 3. Schwierigkeitsgrad der Persona (1..5) ===
    st.markdown("### Wie schwierig ist der Kunde?")
    mvp_grad = st.segmented_control(
        " ",
        options=[1, 2, 3, 4, 5],
        format_func=lambda x: f"{x} · " + next(g["label"] for g in MVP_GRADE if g["key"] == x),
        selection_mode="single",
        default=1,
        label_visibility="collapsed",
        key="mvp_grad_segctl"
    )
    if mvp_grad is None:
        mvp_grad = 1

    # Konstruiere die Persona aus der aktuellen Zelle
    selected_persona = build_mvp_persona(mvp_persona, mvp_grad)

    # === CloserCoach-Style Preview-Card der getroffenen Auswahl ===
    _persona_emoji = {"F": "🎯", "O": "🤝", "R": "🧘", "M": "🔍"}.get(mvp_persona, "👤")
    _diff_class = "cc-diff-easy" if mvp_grad <= 2 else ("cc-diff-med" if mvp_grad == 3 else "cc-diff-hard")
    _grad_label = next(g["label"] for g in MVP_GRADE if g["key"] == mvp_grad)
    _base = MVP_PERSONAS[mvp_persona]
    st.markdown(
        f'<div class="cc-persona-card selected" style="max-width:340px; margin: 8px 0 24px;">'
        f'  <div class="cc-persona-photo">{_persona_emoji}</div>'
        f'  <div class="cc-persona-body">'
        f'    <div class="cc-persona-name">{_base["name"]} · {_base["alter"]}</div>'
        f'    <div class="cc-persona-meta">'
        f'      <span class="cc-diff-dot {_diff_class}"></span> '
        f'      Grad {mvp_grad} · {_grad_label}'
        f'    </div>'
        f'    <div style="font-size:12px; color:{TEXT_TERTIARY}; margin-top:6px;">'
        f'      Zelle {mvp_persona}{mvp_grad} · {_base["job"]}'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    with st.expander(f"Zelle {mvp_persona}{mvp_grad} · Discovery-Profil sehen"):
        base = MVP_PERSONAS[mvp_persona]
        grad_entry = next(g for g in MVP_GRADE if g["key"] == mvp_grad)
        st.markdown(f"**{base['name']}** · {base['alter']} · {base['job']}")
        st.markdown(f"**Schwierigkeitsgrad:** {mvp_grad} · {grad_entry['label']}")
        st.markdown(selected_persona["discovery_summary"])
        st.markdown(f"_Eröffnungs-Einwand:_ „{selected_persona['opening_einwand']}\"")

    # === 4. Coach-Modus (wie viel Hilfe der User bekommt) ===
    if role == "closer":
        st.markdown("### Wie viel Coach-Hilfe willst du?")
        coach_mode = st.segmented_control(
            " ",
            options=["easy", "medium", "hard"],
            format_func=lambda x: {
                "easy": "Easy · Phasen-Hinweis + 3 Klick-Optionen",
                "medium": "Medium · Phasen-Hinweis, du tippst",
                "hard": "Hard · Du machst alles selbst"
            }[x],
            selection_mode="single",
            default="easy",
            label_visibility="collapsed",
            key="coach_mode_segctl"
        )
    else:
        coach_mode = "hard"
        st.markdown(
            f'<div style="color:{TEXT_TERTIARY}; font-size:13px; margin-bottom:16px;">'
            f"<em>Im Kunden-Modus kein Coach-Modus — die KI spielt einen Top-Closer.</em>"
            f"</div>",
            unsafe_allow_html=True
        )

    # === 4. Pricing (These #15 — konfigurierbar) ===
    st.markdown("### Programm-Pricing (optional)")
    st.markdown(
        f'<div style="color:{TEXT_TERTIARY}; font-size:12px; margin-bottom:8px;">'
        f"Wird in den Closer-Antworten + Phasen-Coach-Optionen verwendet "
        f"(statt Platzhaltern wie [X€]). Leer lassen = Phasen-Coach verwendet generische Platzhalter."
        f"</div>",
        unsafe_allow_html=True
    )
    # === 4. Programm-Beschreibung (NEU 31.05. · Pflichtfeld-Spec NEU-4) ===
    # Strukturierte Erfassung: Produkt-Typ + Rahmenbedingungen.
    # Loest Customer-Bot-Halluzinationen und gibt Coach den vollen Programm-Kontext.

    produkt_typ = st.selectbox(
        "Produkt-Typ *",
        options=["Coaching", "Training", "Online-Kurs", "Beratung", "Mentoring", "Sonstiges"],
        key="produkt_typ_input",
        index=0,
        help="Was verkauft der Closer? Sellmo ist für Coaching/Training optimiert."
    )

    st.markdown("#### Kosten")
    col_k1, col_k2 = st.columns([2, 1])
    with col_k1:
        gesamtkosten = st.text_input(
            "Gesamtkosten *",
            key="gesamtkosten_input",
            placeholder="z.B. 4.800€",
            help="Was kostet das gesamte Programm? Wird im Discovery genannt, in P6 nur noch Commitment."
        )
    with col_k2:
        ratenzahlung_moeglich = st.checkbox(
            "Ratenzahlung möglich",
            key="ratenzahlung_check",
            value=False
        )

    raten_dict = None
    if ratenzahlung_moeglich:
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            anzahl_raten = st.selectbox(
                "Anzahl Raten",
                options=[3, 6, 9, 12],
                key="anzahl_raten_input",
                index=0
            )
        with col_r2:
            # Auto-Berechnung wenn Gesamtkosten als Zahl interpretierbar
            try:
                # Extrahiere nur Ziffern + Komma/Punkt aus Gesamtkosten
                import re
                match = re.search(r"[\d.,]+", gesamtkosten or "")
                if match:
                    num_str = match.group().replace(".", "").replace(",", ".")
                    gesamt_val = float(num_str)
                    auto_rate = round(gesamt_val / anzahl_raten, 2)
                    rate_default = f"{auto_rate:.2f}€".replace(".", ",")
                else:
                    rate_default = ""
            except Exception:
                rate_default = ""
            hoehe_pro_rate = st.text_input(
                f"Hoehe pro Rate (auto-berechnet)",
                value=rate_default,
                key="hoehe_pro_rate_input"
            )
        raten_dict = {
            "anzahl": anzahl_raten,
            "hoehe": hoehe_pro_rate,
        }

    st.markdown("#### Dauer")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        dauer_stunden = st.text_input(
            "Stunden gesamt",
            key="dauer_stunden_input",
            placeholder="z.B. 40 Stunden"
        )
    with col_d2:
        dauer_wochen = st.text_input(
            "Wochen",
            key="dauer_wochen_input",
            placeholder="z.B. 8 Wochen"
        )

    st.markdown("#### Umfang (was ist enthalten?)")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        umfang_1zu1 = st.checkbox("1:1 Coaching", key="umfang_1zu1")
        umfang_online = st.checkbox("Online-Kurse", key="umfang_online")
        umfang_live = st.checkbox("Live-Calls", key="umfang_live")
    with col_u2:
        umfang_rollenspiele = st.checkbox("Rollenspiele", key="umfang_rollenspiele")
    umfang_freitext = st.text_area(
        "Freitext (weitere Programm-Infos)",
        key="umfang_freitext_input",
        placeholder="z.B. woechentliche Hausaufgaben, Telegram-Support, Community-Zugang...",
        height=80
    )

    # Konsolidierung in programm_info-Dict
    programm_info = {
        "produkt_typ": produkt_typ,
        "gesamtkosten": gesamtkosten.strip() if gesamtkosten else None,
        "ratenzahlung": raten_dict,
        "dauer_stunden": dauer_stunden.strip() if dauer_stunden else None,
        "dauer_wochen": dauer_wochen.strip() if dauer_wochen else None,
        "umfang": {
            "1zu1_coaching": umfang_1zu1,
            "online_kurse": umfang_online,
            "live_calls": umfang_live,
            "rollenspiele": umfang_rollenspiele,
            "freitext": umfang_freitext.strip() if umfang_freitext else None,
        }
    }

    # Legacy-Kompatibilitaet: pricing_info bleibt als Sub-Slice fuer alten Code
    pricing_amount = gesamtkosten
    pricing_time = f"{dauer_stunden} / {dauer_wochen}".strip(" /") if (dauer_stunden or dauer_wochen) else ""

    # === 4b. Customer-Ziel (NEU v2.0 · Patch #53 Pflichtfeld) ===
    st.markdown("### Was will der Kunde erreichen? *")
    st.markdown(
        f'<div style="color:{TEXT_TERTIARY}; font-size:12px; margin-bottom:8px;">'
        f"1-Satz, was der Kunde am Ende des Programms erreichen will. "
        f"Wird in Phase 6 vom Coach als Ziel-Anker verwendet (Patch #53)."
        f"</div>",
        unsafe_allow_html=True
    )
    customer_goal = st.text_input(
        "Customer-Ziel *",
        key="customer_goal_input",
        placeholder="z.B. 6.000€/Monat mit Closer-Skills"
    )

    # === 5. Feedback-Modus ===
    st.markdown("### Feedback-Modus")
    feedback_mode = st.segmented_control(
        " ",
        options=["end_of_call", "live", "beides"],
        format_func=lambda x: {
            "end_of_call": "Am Ende (immersiv)",
            "live": "Live nach jedem Turn (didaktisch)",
            "beides": "Beides"
        }[x],
        selection_mode="single",
        default="end_of_call",
        label_visibility="collapsed",
        key="feedback_mode_segctl"
    )

    st.markdown("---")

    # SOHF v2.0 Patch #52: Pflichtfeld-Validierung VOR Training-Start
    # Preis + Customer-Ziel sind NEU v2.0 Pflichtfelder.
    missing_fields = []
    if not pricing_amount or not pricing_amount.strip():
        missing_fields.append("Preis")
    if not customer_goal or not customer_goal.strip():
        missing_fields.append("Customer-Ziel")

    # NEU-2 Fix (31.05.): rote Border um fehlende Input-Felder via CSS
    if missing_fields:
        css_selectors = []
        if "Preis" in missing_fields:
            css_selectors.append('div[data-testid="stTextInput"]:has(input[aria-label*="Preis"])')
        if "Customer-Ziel" in missing_fields:
            css_selectors.append('div[data-testid="stTextInput"]:has(input[aria-label*="Customer-Ziel"])')
        if css_selectors:
            st.markdown(
                f'<style>'
                f'{", ".join(css_selectors)} input {{ '
                f'border: 2px solid #F87171 !important; '
                f'background: rgba(248, 113, 113, 0.06) !important; '
                f'}}'
                f'</style>',
                unsafe_allow_html=True
            )
        st.markdown(
            f'<div style="background: rgba(248, 113, 113, 0.12); border-left: 3px solid #F87171; '
            f'padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 13px;">'
            f'<strong>Pflichtfelder fehlen:</strong> {", ".join(missing_fields)}<br>'
            f'<span style="color: #94a3b8; font-size: 12px;">'
            f'Felder oben mit rotem Rand markiert. Bitte ausfuellen.</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    train_button_disabled = bool(missing_fields)

    # NEU-1 Fix (31.05.): Button wird GRUEN sobald alles ausfuellbar, plus angepasste Breite (nicht volle Seite)
    if not train_button_disabled:
        st.markdown(
            '<style>'
            'button[data-testid="stBaseButton-primary"] { '
            '  background-color: #33E88E !important; '
            '  border-color: #33E88E !important; '
            '  color: #000000 !important; '
            '  font-weight: 600 !important; '
            '  border-radius: 32px !important; '
            '  padding: 16px 32px !important; '
            '  font-size: 16px !important; '
            '}'
            'button[data-testid="stBaseButton-primary"]:hover { '
            '  background-color: #2ACE7C !important; '
            '  border-color: #2ACE7C !important; '
            '  box-shadow: 0 6px 18px rgba(51, 232, 142, 0.30) !important; '
            '  transform: translateY(-1px); '
            '}'
            '</style>',
            unsafe_allow_html=True
        )

    col_btn_left, col_btn_mid, col_btn_right = st.columns([1, 2, 1])
    with col_btn_mid:
        train_button_clicked = st.button(
            "Training starten" if train_button_disabled else "Bereit · Training starten",
            type="primary",
            use_container_width=True,
            disabled=train_button_disabled
        )
    if train_button_clicked:
        # selected_persona wird bereits im Setup-Screen aus mvp_persona x mvp_grad gebaut
        st.session_state.persona = selected_persona
        st.session_state.mvp_persona = mvp_persona
        st.session_state.mvp_grad = mvp_grad
        st.session_state.role = role
        st.session_state.coach_mode = coach_mode
        st.session_state.feedback_mode = feedback_mode
        st.session_state.session_started = True
        st.session_state.started_at = datetime.now().isoformat()
        # These #15: Pricing-Info im Session-State speichern
        pricing_dict = {}
        if pricing_amount and pricing_amount.strip():
            pricing_dict["amount"] = pricing_amount.strip()
        if pricing_time and pricing_time.strip():
            pricing_dict["time_per_week"] = pricing_time.strip()
        st.session_state.pricing_info = pricing_dict if pricing_dict else None
        # SOHF v2.0 Patch #53: Customer-Ziel im Session-State speichern
        st.session_state.customer_goal = customer_goal.strip() if customer_goal else None
        # NEU 31.05.: Vollstaendige Programm-Beschreibung im Session-State speichern
        st.session_state.programm_info = programm_info
        # Session-Logging-System: Setup-Event loggen
        _log_event(
            "setup",
            persona_id=selected_persona.get("id"),
            persona_name=selected_persona.get("name"),
            mvp_persona=mvp_persona,
            mvp_grad=mvp_grad,
            role=role,
            coach_mode=coach_mode,
            feedback_mode=feedback_mode,
            pricing_amount=pricing_dict.get("amount") if pricing_dict else None,
            pricing_time=pricing_dict.get("time_per_week") if pricing_dict else None,
            customer_goal=st.session_state.customer_goal,
        )

        # Erstes KI-Statement holen
        if role == "closer":
            # Customer-Bot eröffnet mit Einwand
            customer_response, cost = call_customer_bot(
                selected_persona, [],
                programm_info=programm_info,
                customer_goal=st.session_state.customer_goal
            )
            st.session_state.conversation_history.append({
                "role": "customer",
                "text": customer_response["customer_utterance"]
            })
            st.session_state.customer_internal_state = customer_response["internal_state"]
            st.session_state.total_cost_eur += cost
            st.session_state.current_phase = "1"  # Default-Start
            st.session_state.phase_history.append("1")
        else:
            # Customer-Modus: Closer-Bot eröffnet erst, wenn Christian ein Customer-Statement geliefert hat
            # Initial: Christian's Customer-Eröffnung über opening_einwand der Persona vorbelegen
            st.session_state.conversation_history.append({
                "role": "customer",
                "text": selected_persona["opening_einwand"]
            })
            st.session_state.current_phase = "1"
            st.session_state.phase_history.append("1")
            # Closer-Bot reagiert auf das Customer-Statement
            closer_response, cost = call_closer_bot(selected_persona,
                                                      st.session_state.conversation_history)
            st.session_state.conversation_history.append({
                "role": "closer",
                "text": closer_response["closer_utterance"]
            })
            st.session_state.current_phase = str(closer_response.get("phase_now", "1"))
            if st.session_state.current_phase not in st.session_state.phase_history:
                st.session_state.phase_history.append(st.session_state.current_phase)
            st.session_state.total_cost_eur += cost

        st.rerun()


# ============================================================
# CHAT-SCREEN
# ============================================================

def render_chat_screen():
    role = st.session_state.role
    persona = st.session_state.persona

    # Sidebar (automatisch sticky bei Streamlit): Phasen-Leiste + Persona + Buttons
    # BUG-FIX B7 (2026-05-30): Phasen-Leiste als Placeholder, der NACH Coach-Update
    # populated wird. Verhindert Sidebar/Coach-Phase-Mismatch wenn Coach current_phase
    # waehrend Render-Cycle aktualisiert.
    with st.sidebar:
        phase_bar_placeholder = st.empty()
        st.markdown(
            f'<div style="margin-top: 16px; padding: 12px; background:{SURFACE_2}; '
            f'border-radius: 12px; border: 1px solid {BORDER_DEFAULT};">'
            f'<div class="coach-meta">Kunde</div>'
            f'<div style="font-weight:600; color:{TEXT_PRIMARY}; margin-top:4px;">{persona["name"]}</div>'
            f'<div style="font-size:12px; color:{TEXT_SECONDARY}; margin-top:6px;">'
            f'{persona["alter"]} · {persona["job"]}</div>'
            f'<div style="font-size:11px; color:{TEXT_TERTIARY}; margin-top:8px;">'
            f'Einwand: {persona["kern_einwand_kategorie"]}</div>'
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Session beenden", use_container_width=True):
            _end_session()
            st.rerun()
        if st.button("↩  Neue Session", use_container_width=True):
            reset_session()
            st.rerun()

        st.markdown(
            f'<div style="font-size:11px; color:{TEXT_TERTIARY}; margin-top:12px; text-align:center;">'
            f'Turns: {st.session_state.turn_count}  ·  Cost: {st.session_state.total_cost_eur:.4f} €'
            f"</div>",
            unsafe_allow_html=True
        )

    # Main-Bereich (volle Breite): Chat
    title_role = "Closer-Training" if role == "closer" else "Kunde-Training"
    _persona_emoji = {"F": "🎯", "O": "🤝", "R": "🧘", "M": "🔍"}.get(persona.get("form_type", ""), "👤")
    _grad = persona.get("difficulty", 1)
    _diff_class = "cc-diff-easy" if _grad <= 2 else ("cc-diff-med" if _grad == 3 else "cc-diff-hard")
    st.markdown(
        f'<div class="cc-timer-header" style="margin-top:8px;">'
        f'  <div class="cc-timer-persona">'
        f'    <div class="cc-timer-avatar">{_persona_emoji}</div>'
        f'    <div>'
        f'      <div class="cc-timer-name">{persona["name"]} · {persona.get("alter", "")}</div>'
        f'      <div style="font-size:11px; color:{TEXT_TERTIARY}; display:inline-flex; align-items:center; gap:6px;">'
        f'        <span class="cc-diff-dot {_diff_class}"></span> {title_role} · Zelle {persona.get("form_type", "?")}{_grad}'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'  <span class="cc-active-pill">Session läuft</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Avatar-Pfade (Sellmo-Branding)
    AVATAR_CUSTOMER = str(APP_DIR / "assets" / "sellmo_avatar_customer.png")
    AVATAR_CLOSER = str(APP_DIR / "assets" / "sellmo_avatar_closer.png")

    # #4-Refactor (31.05.): WhatsApp-Layout - User-Bubble rechts, Other-Bubble links
    # F2b-Fix (31.05.): Chat-Area soll von unten starten (flex-end), wie WhatsApp
    # User = Christian (closer wenn role=closer, customer wenn role=customer)
    st.markdown(
        '<style>'
        '.chat-area {'
        '  display: flex; flex-direction: column; justify-content: flex-end;'
        '  min-height: 60vh;'
        '}'
        '.chat-row { display: flex; margin: 14px 0; align-items: flex-end; gap: 10px; }'
        '.chat-row.user { flex-direction: row-reverse; justify-content: flex-start; }'
        '.chat-row.other { flex-direction: row; justify-content: flex-start; }'
        '.chat-bubble { max-width: 68%; padding: 14px 16px; border-radius: 22px;'
        '  word-wrap: break-word; line-height: 1.4; font-size: 15px; }'
        '.chat-bubble.user { background: #2E86FF; color: white; border-bottom-right-radius: 6px; }'
        '.chat-bubble.other { background: #2A2A2C; color: #FFFFFF; border-bottom-left-radius: 6px; }'
        '.chat-avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover;'
        '  background: #444; flex-shrink: 0; border: 2px solid rgba(255,255,255,0.08); }'
        '</style>',
        unsafe_allow_html=True
    )
    # F2b-Fix: Chat-Area-Wrapper mit flex-end (Inhalt klebt unten)
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)
    import base64
    def _img_data_url(path):
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{b64}"
        except Exception:
            return ""
    avatar_customer_url = _img_data_url(AVATAR_CUSTOMER)
    avatar_closer_url = _img_data_url(AVATAR_CLOSER)

    # Conversation rendern (WhatsApp-Style)
    for i, msg in enumerate(st.session_state.conversation_history):
        msg_role = msg["role"]
        # User-Side bestimmen: Christian ist Closer oder Customer
        is_user = (msg_role == "closer" and role == "closer") or (msg_role == "customer" and role == "customer")
        side_class = "user" if is_user else "other"
        # Avatar nur fuer "other" (User selbst ohne Avatar lassen, Christians Wunsch)
        if msg_role == "customer":
            avatar_url = avatar_customer_url
        else:
            avatar_url = avatar_closer_url
        avatar_html = (
            f'<img class="chat-avatar" src="{avatar_url}" alt="">'
            if (avatar_url and not is_user) else ''
        )
        # Bubble-Text: Streamlit-Markdown vorab konvertieren (basic, escaped fuer HTML)
        bubble_text = msg["text"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        st.markdown(
            f'<div class="chat-row {side_class}">'
            f'{avatar_html}'
            f'<div class="chat-bubble {side_class}">{bubble_text}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Live-Feedback im Closer-Modus (unter der Bubble)
        if msg_role == "closer" and role == "closer" and st.session_state.feedback_mode in ("live", "beides"):
            closer_idx = sum(1 for m in st.session_state.conversation_history[:i+1]
                               if m["role"] == "closer") - 1
            if 0 <= closer_idx < len(st.session_state.live_feedback_history):
                fb = st.session_state.live_feedback_history[closer_idx]
                if fb:
                    _render_live_feedback(fb)

    # F2b-Fix: Chat-Area schliessen vor Coach-Box
    st.markdown('</div>', unsafe_allow_html=True)

    # Phasen-Coach-Box (vor Input, nur wenn Closer-Modus + EASY/MEDIUM)
    if role == "closer" and st.session_state.coach_mode in ("easy", "medium"):
        _render_phasen_coach_box()

    # BUG-FIX B7 (2026-05-30): Phase-Bar NACH Coach-Update rendern (in Sidebar-Placeholder).
    # current_phase wurde ggf. von _render_phasen_coach_box() aktualisiert -- diese
    # Re-Render-Stelle stellt sicher dass Sidebar den aktuellsten Stand zeigt.
    # U4-Fix (2026-05-30): IMMER rendern, auch wenn Closer-Coach-Box nicht aktiv ist
    # (z.B. customer-mode oder HARD-difficulty), damit Sidebar nie leer ist.
    with phase_bar_placeholder.container():
        render_phase_bar()

    # U1-Fix (2026-05-30): Auto-Scroll zum Ende der Chat-Historie (WhatsApp-Style).
    # Streamlit rendert sequentiell, aber bei langen Sessions ist der Input am unteren Rand
    # und der Nutzer muss nicht scrollen. Anchor + JS-Scroll fuer den Fall dass Browser
    # die Position nicht automatisch nachzieht.
    st.markdown(
        '<div id="chat-bottom"></div>'
        '<script>'
        'setTimeout(function() {'
        '  var anchor = document.getElementById("chat-bottom");'
        '  if (anchor) anchor.scrollIntoView({behavior: "smooth", block: "end"});'
        '}, 100);'
        '</script>',
        unsafe_allow_html=True
    )

    # Input · Placeholder leer, damit Chat-Feld sauber aussieht
    user_input = st.chat_input("")
    if user_input:
        _process_user_turn(user_input)
        st.rerun()


def _render_phasen_coach_box():
    """Zeigt Phasen-Coach-Output. Triggert KI-Call, wenn noch nicht aktuell."""
    persona = st.session_state.persona
    history = st.session_state.conversation_history
    current_phase = st.session_state.current_phase
    coach_mode = st.session_state.coach_mode

    # Coach-Call wenn nötig — schlanke Progress-Line statt Vollbild-Overlay
    if st.session_state.phasen_coach_output is None or \
       st.session_state.phasen_coach_output.get("_for_turn") != st.session_state.turn_count:
        loading_placeholder = st.empty()
        # Subtile indeterminate Progress-Line (kein Modal, kein Blur)
        loading_placeholder.markdown(
            f'<div style="margin: 12px 0 8px; padding: 10px 14px; '
            f'background: {SURFACE_1}; border: 1px solid {BORDER_DEFAULT}; '
            f'border-radius: 10px; display: flex; align-items: center; gap: 12px;">'
            f'  <div style="font-size: 13px; color: {TEXT_SECONDARY}; flex-shrink: 0;">'
            f'    Coach analysiert…</div>'
            f'  <div style="flex: 1; height: 3px; background: rgba(255,255,255,0.10); '
            f'       border-radius: 2px; overflow: hidden; position: relative;">'
            f'    <div class="cc-progress-slide" style="position: absolute; top: 0; left: 0; '
            f'         height: 100%; width: 40%; background: {ACCENT_PRIMARY}; '
            f'         border-radius: 2px;"></div>'
            f'  </div>'
            f'</div>'
            f'<style>'
            f'@keyframes cc-slide {{ '
            f'  0% {{ left: -40%; }} '
            f'  100% {{ left: 100%; }} '
            f'}}'
            f'.cc-progress-slide {{ animation: cc-slide 1.4s ease-in-out infinite; }}'
            f'</style>',
            unsafe_allow_html=True
        )
        coach_output, cost = call_phasen_coach(
            persona, history, current_phase, coach_mode,
            pricing_info=st.session_state.get("pricing_info"),
            customer_goal=st.session_state.get("customer_goal"),
            programm_info=st.session_state.get("programm_info")
        )
        loading_placeholder.empty()  # Progress-Line verschwindet nach Coach-Response
        st.session_state.total_cost_eur += cost
        if "error" not in coach_output:
            coach_output["_for_turn"] = st.session_state.turn_count
            st.session_state.phasen_coach_output = coach_output

    coach = st.session_state.phasen_coach_output
    if not coach or "error" in coach:
        if coach and "error" in coach:
            st.warning(f"Coach-Fehler: {coach.get('error', '?')}")
        return

    # === BUG-FIX #20: Phase-State aus Phasen-Coach syncen ===
    # Bisher wurde current_phase NUR via Feedback-Coach aktualisiert (live-Modus).
    # Bei feedback_mode != "live" blieb current_phase auf "1" haengen, obwohl der
    # Phasen-Coach laengst Phase 4+ anzeigte. Sidebar zeigte dann falschen Stand.
    coach_phase_now = coach.get("phase_now")
    if coach_phase_now and str(coach_phase_now) != str(st.session_state.current_phase):
        old_phase = st.session_state.current_phase
        st.session_state.current_phase = str(coach_phase_now)
        if str(coach_phase_now) not in st.session_state.phase_history:
            st.session_state.phase_history.append(str(coach_phase_now))
        # Self-Correction-Detection (These #14): erkenne Phase-Rueckspruenge
        try:
            if old_phase and str(old_phase).isdigit() and str(coach_phase_now).isdigit():
                if int(coach_phase_now) < int(old_phase):
                    st.session_state.last_phase_regression = {
                        "from": str(old_phase),
                        "to": str(coach_phase_now),
                        "reason": "D5 Self-Correction · Phase-Ruecksprung wegen schwacher Antwort-Substanz"
                    }
        except Exception:
            pass

    # === Self-Correction-Banner (These #14) ===
    regression = st.session_state.get("last_phase_regression")
    if regression and str(regression.get("to")) == str(st.session_state.current_phase):
        st.markdown(
            f'<div style="background: rgba(250, 204, 21, 0.12); border-left: 3px solid #FACC15; '
            f'padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 13px;">'
            f'<strong>D5 Self-Correction</strong> · '
            f'Phasen-Ruecksprung P{regression["from"]} → P{regression["to"]}<br>'
            f'<span style="color: #94a3b8; font-size: 12px;">{regression["reason"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # P-4-Fix 01.06.: Coach-Box-Header uebersichtlicher.
    # Vorher: 4 Info-Blocks vermischt in einer Box.
    # Nachher: kompakter Phase-Pill oben + Methodischer Tipp prominent + Customer-Zustand als Hover/Sekundaer.
    phase_now_str = coach.get("phase_now", "?")
    phase_next_str = coach.get("phase_next_target", "?")
    # Phase-Pill: kompakte Top-Zeile
    if phase_now_str != phase_next_str and phase_now_str != "?" and phase_next_str != "?":
        phase_pill = f"Phase {phase_now_str} → {phase_next_str}"
    else:
        phase_pill = f"Phase {phase_now_str}"
    customer_state = coach.get("customer_state", "")
    methodical_hint = coach.get("methodical_hint", "")
    st.markdown(
        f'<div class="coach-box" style="padding: 16px 20px;">'
        # Top-Zeile: kompakter Phase-Pill
        f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">'
        f'<span style="background:{SELLMO_ORANGE}; color:#0a0a0a; padding:3px 10px; '
        f'border-radius:12px; font-size:11px; font-weight:700; letter-spacing:0.05em;">'
        f'{phase_pill}</span>'
        f'<span style="font-size:12px; color:{TEXT_TERTIARY};">'
        f'Kunde: {customer_state}</span>'
        f'</div>'
        # Methodischer Tipp prominent
        f'<div style="font-size:14px; line-height:1.55; color:{TEXT_PRIMARY};">'
        f'{methodical_hint}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Multiple-Choice-Buttons bei EASY (SOHF v2.0 Patch #51: Lern-Pfad A/B/C)
    if coach_mode == "easy" and coach.get("options"):
        # Session-Logging: Coach-Output diesen Turn loggen (nur einmal pro Turn)
        coach_log_key = f"coach_logged_turn_{st.session_state.turn_count}"
        if not st.session_state.get(coach_log_key):
            _log_event(
                "coach_output",
                phase_now=coach.get("phase_now"),
                phase_next_target=coach.get("phase_next_target"),
                form_cell=coach.get("form_cell"),
                methodical_hint=coach.get("methodical_hint"),
                options=[
                    {"label": o.get("label"), "text": o.get("text"),
                     "correctness": o.get("correctness"),
                     "muster": o.get("muster")}
                    for o in coach.get("options", [])
                ],
            )
            st.session_state[coach_log_key] = True
        # Session-Logging: Live-Markierungs-Button fuer Feedback-Marker
        col_header, col_flag = st.columns([4, 1])
        with col_header:
            st.markdown(
                f'<div class="coach-meta" style="margin-top: 12px;">Drei Antwort-Optionen — '
                f'<strong>A = richtig · B = fast richtig · C = falsch</strong> '
                f'(Lern-Pfad, Patch #51)</div>',
                unsafe_allow_html=True
            )
        with col_flag:
            # F5-Fix (31.05.): Klick auf "markieren" oeffnet sofort inline Textfeld
            flag_open_key = f"flag_open_turn_{st.session_state.turn_count}"
            if st.button("🚩 markieren",
                         key=f"flag_turn_{st.session_state.turn_count}",
                         help="Markiert diesen Turn und oeffnet sofort ein Feedback-Textfeld",
                         use_container_width=True):
                _log_event("feedback_marker", note="manual flag by Christian")
                st.session_state[flag_open_key] = True
                st.toast("Turn markiert · Textfeld unten")

        # F5-Fix: Inline-Textfeld direkt unter Coach-Box, wenn markiert
        if st.session_state.get(flag_open_key, False):
            current_turn = st.session_state.turn_count
            inline_fb_key = f"inline_feedback_turn_{current_turn}"
            inline_text = st.text_area(
                f"Was an Turn {current_turn} ist gut/schlecht? (wird automatisch gespeichert)",
                key=inline_fb_key,
                height=80,
                placeholder="z.B. 'Coach hat hier Reframe-Move in P2 angeboten, sollte erst P4 sein.'"
            )
            if inline_text:
                # Sofort ins session_feedback dict speichern (kein Submit-Button noetig)
                st.session_state.session_feedback[str(current_turn)] = inline_text
        # SOHF v2.0 Patch #51 · P-2-Refactor 01.06.: Karten direkt klickbar (Button = Karte)
        # P-2-Fix: Buttons unter den Karten entfernt. Die Karte selbst IST jetzt der Button.
        # Realisiert via CSS-Targeting per Marker-Span + :has()-Selector.
        correctness_color_map = {
            "richtig": "#15803d",
            "fast_richtig": "#a16207",
            "halb_richtig": "#a16207",  # legacy
            "falsch": "#b91c1c",
        }
        correctness_color_hover_map = {
            "richtig": "#166534",
            "fast_richtig": "#854d0e",
            "halb_richtig": "#854d0e",
            "falsch": "#991b1b",
        }
        correctness_label_map = {
            "richtig": "RICHTIG",
            "fast_richtig": "FAST RICHTIG",
            "halb_richtig": "FAST RICHTIG",
            "falsch": "FALSCH",
        }
        correctness_marker_class = {
            "richtig": "lern-pfad-marker-richtig",
            "fast_richtig": "lern-pfad-marker-fast",
            "halb_richtig": "lern-pfad-marker-fast",
            "falsch": "lern-pfad-marker-falsch",
        }
        # Reihenfolge C → B → A (Leserichtung Falsch-Fast-Richtig)
        sort_order = {"falsch": 0, "fast_richtig": 1, "halb_richtig": 1, "richtig": 2}
        options_sorted = sorted(
            coach["options"],
            key=lambda o: sort_order.get(o.get("correctness", ""), 99)
        )
        # P-2-Fix: globales CSS fuer Karten-Buttons via :has()-Selector
        # Streamlit-Buttons werden via Marker-Span im selben Column-Container ausgewaehlt.
        st.markdown(
            f'''<style>
            [data-testid="stColumn"]:has(.lern-pfad-marker-richtig) [data-testid="stBaseButton-secondary"] {{
                background: {correctness_color_map["richtig"]} !important;
                border: 1px solid {correctness_color_map["richtig"]} !important;
                color: #ffffff !important;
                min-height: 240px !important;
                padding: 18px 20px !important;
                text-align: left !important;
                font-weight: 400 !important;
                line-height: 1.5 !important;
                white-space: normal !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: flex-start !important;
                align-items: flex-start !important;
                transition: background 0.15s ease, transform 0.15s ease;
            }}
            [data-testid="stColumn"]:has(.lern-pfad-marker-richtig) [data-testid="stBaseButton-secondary"]:hover {{
                background: {correctness_color_hover_map["richtig"]} !important;
                transform: translateY(-2px);
            }}
            [data-testid="stColumn"]:has(.lern-pfad-marker-fast) [data-testid="stBaseButton-secondary"] {{
                background: {correctness_color_map["fast_richtig"]} !important;
                border: 1px solid {correctness_color_map["fast_richtig"]} !important;
                color: #ffffff !important;
                min-height: 240px !important;
                padding: 18px 20px !important;
                text-align: left !important;
                font-weight: 400 !important;
                line-height: 1.5 !important;
                white-space: normal !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: flex-start !important;
                align-items: flex-start !important;
                transition: background 0.15s ease, transform 0.15s ease;
            }}
            [data-testid="stColumn"]:has(.lern-pfad-marker-fast) [data-testid="stBaseButton-secondary"]:hover {{
                background: {correctness_color_hover_map["fast_richtig"]} !important;
                transform: translateY(-2px);
            }}
            [data-testid="stColumn"]:has(.lern-pfad-marker-falsch) [data-testid="stBaseButton-secondary"] {{
                background: {correctness_color_map["falsch"]} !important;
                border: 1px solid {correctness_color_map["falsch"]} !important;
                color: #ffffff !important;
                min-height: 240px !important;
                padding: 18px 20px !important;
                text-align: left !important;
                font-weight: 400 !important;
                line-height: 1.5 !important;
                white-space: normal !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: flex-start !important;
                align-items: flex-start !important;
                transition: background 0.15s ease, transform 0.15s ease;
            }}
            [data-testid="stColumn"]:has(.lern-pfad-marker-falsch) [data-testid="stBaseButton-secondary"]:hover {{
                background: {correctness_color_hover_map["falsch"]} !important;
                transform: translateY(-2px);
            }}
            </style>''',
            unsafe_allow_html=True
        )
        cols = st.columns(len(options_sorted))
        for idx, opt in enumerate(options_sorted):
            with cols[idx]:
                correctness = opt.get("correctness")
                consequence_hint = opt.get("consequence_hint", "")
                badge_label = correctness_label_map.get(correctness, opt.get("label", "?"))
                muster_tooltip = opt.get("muster", "")
                tip_text = opt.get("tip", "")
                marker = correctness_marker_class.get(correctness, "lern-pfad-marker-neutral")
                # Unsichtbarer Marker-Span im Column-Container fuer CSS-Targeting
                st.markdown(f'<span class="{marker}" style="display:none;"></span>',
                            unsafe_allow_html=True)
                # Button-Label mit Karten-Inhalt (Markdown multi-line)
                btn_label = (
                    f"**{badge_label}**\n\n"
                    f"{opt.get('text', '')}"
                )
                if consequence_hint:
                    btn_label += f"\n\n*Folge: {consequence_hint}*"
                help_parts = [p for p in [muster_tooltip, tip_text] if p]
                help_text = "\n\n".join(help_parts) if help_parts else None
                if st.button(
                    btn_label,
                    key=f"coach_opt_{idx}_{st.session_state.turn_count}",
                    use_container_width=True,
                    help=help_text
                ):
                    _log_event(
                        "closer_action",
                        action="click_option",
                        option_label=opt.get("label"),
                        option_correctness=opt.get("correctness"),
                        text=opt["text"],
                    )
                    _process_user_turn(opt["text"])
                    st.rerun()


def _render_live_feedback(fb):
    if not fb or "error" in fb:
        if fb and "error" in fb:
            with st.expander("Feedback-Fehler"):
                st.code(fb.get("error", ""))
        return
    rating = fb.get("rating", "?")
    # Rating-Label-Map: kurze, klare Labels ohne Emoji
    label_map = {
        "stark": "STARK",
        "okay": "OK",
        "verbesserungswuerdig": "BORDERLINE",
        "methodisch_fehlerhaft": "GEBROCHEN",
    }
    label = label_map.get(rating, rating.upper())
    # C-1-Fix 01.06.: P2/P4-Verwechslungs-Warnung bei Phase-Lag
    phase_id = str(fb.get('phase_identified', '?'))
    phase_exp = str(fb.get('phase_methodologically_expected', '?'))
    phase_lag = fb.get('phase_lag', 0)
    try:
        phase_lag_int = int(phase_lag) if phase_lag is not None else 0
    except Exception:
        phase_lag_int = 0
    # Bei Phase-Lag != 0 prominente Warnung anzeigen (typischer P2/P4-Verwechslungs-Fall)
    if phase_lag_int != 0 and phase_id != "?" and phase_exp != "?":
        st.markdown(
            f'<div style="background: rgba(250, 204, 21, 0.12); '
            f'border-left: 3px solid #FACC15; padding: 8px 12px; '
            f'border-radius: 6px; margin: 6px 0; font-size: 12px;">'
            f'<strong>Phase-Warnung:</strong> Dein Move war methodisch in Phase {phase_id}, '
            f'der Coach erwartete Phase {phase_exp}. '
            f'{"Du bist vorgeprescht." if phase_lag_int < 0 else "Du bist hinterher."}'
            f'</div>',
            unsafe_allow_html=True
        )
    with st.expander(
        f"{label}  ·  Phase {phase_id} "
        f"(erwartet: {phase_exp})  ·  "
        f"{fb.get('muster_used', '?')}"
    ):
        st.markdown(f"**Bewertung:** {fb.get('rating_reason', '')}")
        if fb.get("improvement_tip"):
            st.markdown(f"**Tipp:** {fb['improvement_tip']}")
        if fb.get("muster_alternative_suggestion"):
            st.markdown(f"**Alternative:** {fb['muster_alternative_suggestion']}")
        viols = fb.get("disziplin_violations", [])
        if viols:
            st.markdown(f"**Disziplin-Verletzungen:** {', '.join(viols)}")
        strengths = fb.get("disziplin_strengths", [])
        if strengths:
            st.markdown(f"**Disziplin-Stärken:** {', '.join(strengths)}")


def _process_user_turn(user_text):
    role = st.session_state.role
    persona = st.session_state.persona

    # Session-Logging: Closer-Move (egal ob Click-Option oder Typed-Input)
    _log_event("closer_turn", text=user_text, role=role)

    if role == "closer":
        # Christian's Aussage als Closer
        st.session_state.conversation_history.append({
            "role": "closer",
            "text": user_text
        })
        st.session_state.turn_count += 1

        # Live-Feedback
        if st.session_state.feedback_mode in ("live", "beides"):
            with st.spinner("Coach wertet aus..."):
                fb, cost = call_feedback_coach(
                    user_text, st.session_state.conversation_history,
                    persona, "live", evaluating_role="closer"
                )
                st.session_state.live_feedback_history.append(fb)
                st.session_state.total_cost_eur += cost
        else:
            st.session_state.live_feedback_history.append(None)

        # Customer reagiert
        with st.spinner("Kunde überlegt..."):
            customer_response, cost = call_customer_bot(
                persona, st.session_state.conversation_history,
                programm_info=st.session_state.get("programm_info"),
                customer_goal=st.session_state.get("customer_goal")
            )
            customer_utterance = customer_response["customer_utterance"]
            st.session_state.conversation_history.append({
                "role": "customer",
                "text": customer_utterance
            })
            # Session-Logging: Customer-Antwort + internal_state
            _log_event(
                "customer_response",
                text=customer_utterance,
                stage_in_conversation=customer_response.get("internal_state", {}).get("stage_in_conversation"),
                trust_level=customer_response.get("internal_state", {}).get("trust_level"),
            )
            st.session_state.customer_internal_state = customer_response["internal_state"]
            st.session_state.total_cost_eur += cost
            # Phase ggf. aktualisieren via Feedback-Coach
            if st.session_state.live_feedback_history and st.session_state.live_feedback_history[-1]:
                fb = st.session_state.live_feedback_history[-1]
                if isinstance(fb, dict) and fb.get("phase_identified"):
                    new_phase = str(fb["phase_identified"])
                    if new_phase != st.session_state.current_phase:
                        st.session_state.current_phase = new_phase
                        if new_phase not in st.session_state.phase_history:
                            st.session_state.phase_history.append(new_phase)
            # Auto-End wenn Customer abgeschlossen
            stage = customer_response["internal_state"].get("stage_in_conversation", "")
            if stage in ("closed", "refused"):
                _end_session()
    else:
        # Customer-Modus: Christian spielt Kunde, KI antwortet als Closer
        st.session_state.conversation_history.append({
            "role": "customer",
            "text": user_text
        })
        st.session_state.turn_count += 1
        with st.spinner("Closer überlegt..."):
            closer_response, cost = call_closer_bot(
                persona, st.session_state.conversation_history
            )
            st.session_state.conversation_history.append({
                "role": "closer",
                "text": closer_response["closer_utterance"]
            })
            new_phase = str(closer_response.get("phase_now", st.session_state.current_phase))
            if new_phase != st.session_state.current_phase:
                st.session_state.current_phase = new_phase
                if new_phase not in st.session_state.phase_history:
                    st.session_state.phase_history.append(new_phase)
            st.session_state.total_cost_eur += cost


def _end_session():
    if st.session_state.session_ended:
        return
    st.session_state.session_ended = True
    history = st.session_state.conversation_history
    persona = st.session_state.persona
    role = st.session_state.role

    # Letzte zu bewertende Aussage hängt vom Modus ab
    if role == "closer":
        last_to_eval = next((m["text"] for m in reversed(history) if m["role"] == "closer"), "")
        eval_role = "closer"
    else:
        last_to_eval = next((m["text"] for m in reversed(history) if m["role"] == "closer"), "")
        eval_role = "ai_closer"  # KI-Closer-Moves werden bewertet

    if last_to_eval:
        with st.spinner("End-of-Call-Auswertung läuft..."):
            report, cost = call_feedback_coach(last_to_eval, history, persona,
                                                "end_of_call", evaluating_role=eval_role)
            st.session_state.end_of_call_report = report
            st.session_state.total_cost_eur += cost


# ============================================================
# END-OF-CALL-SCREEN
# ============================================================

def render_end_of_call_screen():
    col_phases, col_main = st.columns([1, 3])
    with col_phases:
        render_phase_bar()

    with col_main:
        persona = st.session_state.persona
        role = st.session_state.role
        title_role = "Closer-Training" if role == "closer" else "Kunde-Training"
        st.markdown(f"## Session beendet  ·  {title_role}  ·  {persona['name']}")

        report = st.session_state.end_of_call_report
        if not report:
            st.warning("Keine Auswertung verfügbar.")
            if st.button("Neue Session starten"):
                reset_session()
                st.rerun()
            return

        if "error" in report:
            st.error(f"Auswertungs-Fehler: {report['error']}")
            if st.button("Neue Session starten"):
                reset_session()
                st.rerun()
            return

        overview = report.get("session_overview", {})
        quote = report.get("methodisch_valide_quote", {})
        pct = int(quote.get("percentage", 0))
        overall_rating = report.get("overall_rating", "?")

        # === Hero-Score-Ring (CloserCoach-Style) ===
        _rating_short = overall_rating.strip().upper()[:2] if overall_rating else "?"
        # Grade → Note (mappt SehrGut → A, Gut → B, etc.)
        _rating_map = {
            "SE": "A", "SEHR": "A", "AU": "A", "AUSGEZEICHNET": "A",
            "GU": "B", "GUT": "B",
            "OK": "C", "OKAY": "C", "MI": "C", "MITTEL": "C",
            "SC": "D", "SCHWACH": "D", "SCHLECHT": "D",
        }
        note = _rating_map.get(_rating_short, overall_rating[:1].upper() if overall_rating else "–")
        # Perzentil-Pill nur bei hoher Quote
        _pill_html = ""
        if pct >= 80:
            _pill_html = '<span class="cc-top-pill">Top 20%</span>'
        elif pct >= 60:
            _pill_html = '<span class="cc-top-pill" style="border-color:#F5A623; color:#F5A623; background:#3D2D0F;">Solide</span>'
        # Ring-Umfang: 2πr = 2·π·42 ≈ 264
        _dash_offset = 264 * (1 - pct / 100)
        _ring_color = ACCENT_PRIMARY if pct >= 60 else (ACCENT_AMBER if pct >= 30 else ACCENT_RED)
        st.markdown(
            f'<div class="cc-ring-wrap" style="margin: 16px 0 20px;">'
            f'  {_pill_html}'
            f'  <div class="cc-ring">'
            f'    <svg viewBox="0 0 100 100" width="200" height="200">'
            f'      <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="6"/>'
            f'      <circle cx="50" cy="50" r="42" fill="none" stroke="{_ring_color}" stroke-width="6" '
            f'              stroke-dasharray="264" stroke-dashoffset="{_dash_offset:.1f}" '
            f'              stroke-linecap="round" transform="rotate(-90 50 50)"/>'
            f'    </svg>'
            f'    <div class="cc-ring-label hero" style="color:{_ring_color};">{note}</div>'
            f'  </div>'
            f'  <div class="cc-ring-caption">{pct}% methodisch valide · {quote.get("valid_turns", 0)}/{quote.get("total_turns", 0)} Turns</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # === Personalisierte Coach-Card ===
        _user_name = st.session_state.get("auth_name", "").split()[0] if st.session_state.get("auth_name") else ""
        _first_insight = report.get("key_insights", [""])[0] if report.get("key_insights") else ""
        _coach_text = report.get("next_level_tipp", _first_insight or "Session ausgewertet.")
        _greeting = f"{_user_name}, " if _user_name else ""
        st.markdown(
            f'<div class="cc-coach-card">'
            f'  <div class="cc-coach-card-avatar">AI</div>'
            f'  <div class="cc-coach-card-body">'
            f'    <div class="cc-coach-card-label">AI Coach sagt…</div>'
            f'    <div class="cc-coach-card-text">{_greeting}{_coach_text}</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # === KPI-Tiles (CloserCoach-Style) ===
        st.markdown(
            f'<div class="cc-kpi-grid">'
            f'  <div class="cc-kpi">'
            f'    <div class="cc-kpi-value">{overview.get("n_turns", 0)}</div>'
            f'    <div class="cc-kpi-label">Turns gesamt</div>'
            f'  </div>'
            f'  <div class="cc-kpi">'
            f'    <div class="cc-kpi-value">{overview.get("pfad_variant_identified", "?")}</div>'
            f'    <div class="cc-kpi-label">Pfad-Variante</div>'
            f'  </div>'
            f'  <div class="cc-kpi">'
            f'    <div class="cc-kpi-value">{overview.get("closing_status", "?")}</div>'
            f'    <div class="cc-kpi-label">Outcome</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )

        journey = overview.get("phase_journey", [])
        if journey:
            st.markdown(f"**Phase-Verlauf:** {' → '.join(f'P{p}' for p in journey)}")

        st.markdown("---")
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### Stärken")
            for s in report.get("staerken", []):
                with st.expander(f"Turn {s.get('turn', '?')}: {s.get('what', '')}"):
                    st.markdown(s.get("why_strong", ""))
        with col_r:
            st.markdown("### Schwächen")
            for w in report.get("schwaechen", []):
                with st.expander(f"Turn {w.get('turn', '?')}: {w.get('what', '')}"):
                    st.markdown(f"**Was hätte gepasst:** {w.get('what_would_have_fit', '')}")
                    st.markdown(f"**Warum:** {w.get('why', '')}")

        st.markdown("---")
        st.markdown("### Key Insights")
        for insight in report.get("key_insights", []):
            st.markdown(f"- {insight}")

        st.markdown("### Next-Level-Tipp")
        st.info(report.get("next_level_tipp", ""))

        # ============================================================
        # SESSION-FEEDBACK-FORM (Session-Logging-System · 30.05.)
        # ============================================================
        st.markdown("---")
        st.markdown("### Christian-Feedback zu dieser Session")
        st.markdown(
            f'<div style="color:{TEXT_TERTIARY}; font-size:12px; margin-bottom:8px;">'
            f"Markierte Turns + Gesamt-Feedback werden im Archiv-File gespeichert "
            f"(Feedback/session_<timestamp>.md)."
            f"</div>",
            unsafe_allow_html=True
        )

        # Markierte Turns aus session_log extrahieren
        session_log = st.session_state.get("session_log", [])
        marked_turns = sorted({
            e.get("turn_n") for e in session_log if e.get("type") == "feedback_marker"
        })

        if marked_turns:
            st.markdown("#### Feedback pro markiertem Turn")
            for turn_n in marked_turns:
                # Kontext: Coach-Output + Closer-Action des markierten Turns finden
                coach_event = next(
                    (e for e in session_log
                     if e.get("turn_n") == turn_n and e.get("type") == "coach_output"),
                    None
                )
                closer_event = next(
                    (e for e in session_log
                     if e.get("turn_n") == turn_n and e.get("type") == "closer_action"),
                    None
                )
                with st.expander(f"Turn {turn_n} · {coach_event.get('phase_now', '?') if coach_event else '?'}"):
                    if coach_event:
                        st.markdown(f"**Coach-Hinweis:** {coach_event.get('methodical_hint', '')}")
                    if closer_event:
                        st.markdown(f"**Closer-Wahl:** Option {closer_event.get('option_label', '?')} ({closer_event.get('option_correctness', '?')}) — *{closer_event.get('text', '')}*")
                    fb_key = f"feedback_turn_{turn_n}"
                    feedback_text = st.text_area(
                        "Was war hier gut/schlecht?",
                        key=fb_key,
                        height=80,
                        placeholder="z.B. 'Coach hat hier Reframe-Move in P2 angeboten, sollte erst P4 sein.'"
                    )
                    # Speichern im session_feedback dict
                    if feedback_text:
                        st.session_state.session_feedback[str(turn_n)] = feedback_text
        else:
            st.caption("Keine Turns markiert (waehrend der Session 🚩-Button nutzen).")

        st.markdown("#### Gesamt-Session-Feedback")
        global_fb = st.text_area(
            "Was lief generell gut/schlecht in dieser Session?",
            key="session_feedback_global_input",
            height=120,
            placeholder="z.B. Customer-Bot halluziniert ab Turn 5, EPISCH-Phasen werden nicht durchlaufen, etc."
        )
        if global_fb:
            st.session_state.session_feedback_global = global_fb

        col_save, col_new = st.columns(2)
        with col_save:
            if st.button("Feedback speichern + archivieren", use_container_width=True):
                file_path = _save_session_log_to_file()
                if file_path:
                    st.success(f"Gespeichert: {file_path}")
                else:
                    st.info("Feedback bereits gespeichert.")

        with col_new:
            if st.button("↩  Neue Session", type="primary", use_container_width=True):
                # Auto-Speichern beim Verlassen falls noch nicht passiert
                if not st.session_state.get("session_feedback_saved"):
                    _save_session_log_to_file()
                reset_session()
                st.rerun()


# ============================================================
# MAIN
# ============================================================

def main():
    st.set_page_config(page_title="sellmo",
                        page_icon=str(APP_DIR / "assets" / "sellmo_icon.png"),
                        layout="wide",
                        initial_sidebar_state="expanded")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # === Auth-Wall ===
    # BETA_MODE: URL-Token-Gate (für Cloud-Preview, kein Login-Formular)
    # Sonst: klassische Login-Wall mit users.yaml + AVV
    beta_mode = False
    try:
        beta_mode = bool(st.secrets.get("BETA_MODE", False))
    except Exception:
        beta_mode = False
    if beta_mode:
        authenticator, username, name = render_beta_token_gate()
    else:
        authenticator, username, name = render_login_wall()
    if authenticator is None:
        # Login noch nicht abgeschlossen (oder AVV-Akzeptanz ausstehend) — App nicht rendern
        return

    # User ist eingeloggt + AVV akzeptiert
    init_session_state()
    # User-Info im Session-State (fuer spaetere Personalisierung)
    st.session_state.auth_username = username
    st.session_state.auth_name = name

    # User-Info + Logout in Sidebar (oben)
    if not isinstance(authenticator, dict):
        render_user_info_sidebar(authenticator, username, name)

    if not st.session_state.session_started:
        render_setup_screen()
    elif st.session_state.session_ended:
        render_end_of_call_screen()
    else:
        render_chat_screen()


if __name__ == "__main__":
    main()
