# 0002 - Hosted backend for data Erik enters himself (issue #44)

Status: proposed (Erik approves). Date: 2026-11-02.

## Context
Valuations (#45/#46), known customers (#50) and notes (#54) are typed by Erik. GitHub Pages is static,
the repo is public, and Erik ruled out "local backend, then commit". The report agent must never see
this data. Single user, small data.

## Options
1. Stay read-only; user-entered features wait. Zero risk, but #45/#46/#50/#54 are blocked.
2. Supabase (Postgres, Auth, row-level security, REST from the browser). Free tier, no server to run.
3. Other (Firebase, own FastAPI host). More to operate, no gain for one user.

## Decision
Supabase, introduced by one setup issue that is done before #45; no code or account work now. Until it
is done the site stays read-only. The project manager schedules that issue when the first user-entered
feature reaches "Ready".

- **Sign-in:** Supabase Auth, email magic link, public sign-ups disabled, Erik is the only user. The
  site has a small "Sign in" control; the session lives in the browser (supabase-js).
- **Keys:** the anon/publishable key and project URL are public by design and may sit in the frontend
  config. Safety comes from row-level security on every table: writes only for Erik's user id. The
  `service_role` key never goes in the repo, the browser or `reports.yml`; if ever needed, it is a
  GitHub Actions secret in a workflow the report agent cannot influence.
- **Read access:** recommended private (select also requires sign-in), because notes are personal and the
  site is public. Signed out, the site shows only the JSON-based pages.
- **How Pages reads it:** the browser calls Supabase directly with the anon key plus Erik's session. If
  the service is down or Erik is signed out, those sections show a short "unavailable / sign in"
  message and the rest of the site works from `data/` as today.
- **Records:** one table each, keyed by ticker: `valuations`, `customers`, `notes`, with `user_id`,
  `created_at`, `updated_at`. Exact columns come with each feature's issue. Schema and RLS policies are
  versioned in the repo as SQL migrations (no data, no secrets).
- **Backup/export (notes):** an "Export" button on the site downloads all notes (and the other tables)
  as JSON/Markdown while signed in. Scheduled backups into the repo or Actions artifacts are rejected:
  both are public and would expose private notes. Supabase's own backups are the second layer.
- **Validation and tests:** `validate.py` does not cover hosted data. Tests cover the SQL (RLS enabled on
  every table, no `service_role` or key patterns in the repo) and the frontend states (signed out, down).
  AGENT.md states the agent never touches this data; `reports.yml` gets no Supabase secrets.

## Consequences
- First time the site holds state outside git: an external service, an account, a free-tier pause policy
  (projects pause after inactivity; Erik must keep it active) and a new failure mode.
- The CSP/connect to `*.supabase.co` must be allowed in the frontend; the supabase-js load is a new
  dependency (CDN or vendored, to be decided in the frontend issue).
- Follow-up issues: (1) Supabase project, auth, RLS and migrations setup; (2) frontend sign-in and
  Supabase client with down/signed-out states; (3) CI check for RLS and leaked keys; (4) export button;
  (5) AGENT.md line forbidding the data; then #45/#46, #50, #54 build on it.
