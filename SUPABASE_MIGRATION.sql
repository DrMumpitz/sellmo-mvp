-- Sellmo · Supabase-Migration v1.0
-- 2026-07-15
--
-- Ausführung: Supabase-Dashboard → SQL Editor → New query →
-- diese Datei komplett reinpasten → RUN.
-- Danach: Table Editor öffnen, prüfen dass "sessions" da ist.

create table if not exists public.sessions (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    session_id text not null unique,             -- Timestamp-basierter Identifier
    token_last4 text,                            -- letzten 4 Zeichen des Beta-Tokens
    user_name text,                              -- auth_name aus session_state
    role text,                                   -- closer | customer
    persona_id text,                             -- z.B. "F1"
    persona_name text,                           -- z.B. "Lukas"
    form_type text,                              -- F | O | R | M
    difficulty integer,                          -- 1..5
    coach_mode text,                             -- easy | medium | hard
    feedback_mode text,                          -- end_of_call | live | beides
    turn_count integer,
    total_cost_eur numeric,
    pricing_amount text,
    customer_goal text,
    programm_info jsonb,
    conversation_history jsonb,
    session_log jsonb,
    end_of_call_report jsonb,
    session_feedback jsonb,                      -- {turn_n: user_feedback_text}
    session_feedback_global text,
    started_at timestamptz,
    ended_at timestamptz
);

-- Indizes für Retention-Bar (letzte N Sessions) + Filter nach Token/Persona
create index if not exists sessions_created_at_idx on public.sessions (created_at desc);
create index if not exists sessions_token_idx on public.sessions (token_last4);
create index if not exists sessions_persona_idx on public.sessions (form_type, difficulty);

-- RLS: aktivieren, aber keine Policies für anon/authenticated definieren.
-- service_role bypasst RLS automatisch — d.h. der Streamlit-Server (nutzt
-- SUPABASE_SERVICE_KEY) hat vollen Zugriff, alle anderen Rollen NICHTS.
alter table public.sessions enable row level security;

-- Verifikation (kannst du nach dem RUN in einem neuen Query ausführen):
-- select count(*) from public.sessions;   -- sollte 0 zurückgeben

-- ============================================================
-- MIGRATION v2 (2026-07-15): user_alternatives-Feld für Ground-Truth-Sammlung
-- ============================================================
-- Kann als eigener Query ausgeführt werden. Idempotent — safe bei Wiederholung.

alter table public.sessions
    add column if not exists user_alternatives jsonb;
