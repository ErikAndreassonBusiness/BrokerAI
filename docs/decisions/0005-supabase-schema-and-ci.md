# 0005 - Supabase schema, access rules, migrations and CI check (issue #56)

Status: proposed. Date: 2026-11-03. Builds on ADR 0002.

## Context
ADR 0002 chose Supabase but left the columns, the exact RLS pattern, where migrations live, how
supabase-js loads and how CI checks all this open. The site is static, the repo is public, there is no
test database, and the frontend has no CSP today (Pages can't set headers).

## Decision
- **valuations** (append-only history): `id uuid pk`, `user_id uuid not null default auth.uid()`,
  `ticker text not null`, `value numeric not null`, `valued_on date not null default current_date`,
  `note text not null default ''`, `created_at timestamptz default now()`. No `updated_at`: rows are
  never updated; a correction is a new row. Only select and insert policies exist (no update/delete).
  Optional low/high: add as nullable columns later, in the migration of the issue that settles
  entered vs derived (a nullable add is cheap and reversible; guessing now risks the wrong shape).
- **customers**: `id`, `user_id`, `ticker`, `name text not null`, `url text null` (check: starts with
  `http://` or `https://`), `created_at`, `updated_at`; unique on `(user_id, ticker, lower(name))`.
- **notes**: `id`, `user_id`, `ticker`, `body text not null default ''`, `created_at`, `updated_at`;
  one row per `(user_id, ticker)` (saved as an upsert). `updated_at` is set by a trigger.
- **Access rule:** `enable row level security` on every table; policies `to authenticated` with
  `using (auth.uid() = user_id)` and, for insert/update, `with check (auth.uid() = user_id)`. No policy
  for `anon`, so signed-out reads return nothing. Do not pin Erik's user id: `auth.uid() = user_id`
  already isolates rows per user, and with sign-ups off Erik is the only user; a hard-coded id adds
  brittleness (new account = edit every policy) for no extra safety. The real gate is the dashboard
  setting "sign-ups disabled", which is not in the repo, so it is a manual checklist item in #56.
- **Migrations:** `supabase/migrations/<yyyymmddhhmmss>_<name>.sql` (CLI-compatible naming), one file per
  change, an applied file is never edited. Erik applies them by pasting into the SQL editor in order; no
  CLI, no login or token on his machine. Moving to the CLI later needs no change to the files.
- **Public config:** `app/frontend/client/config.js` holds project URL and anon/publishable key (public
  by design). **supabase-js:** vendored, pinned file `app/frontend/client/vendor/supabase.js` (decided
  finally in #57): no third-party script runs on the page that holds Erik's session, and no CDN outage.
  No CSP exists now. If one is added (meta tag), it needs `connect-src 'self' https://*.supabase.co`.
- **CI (no database), a pytest file:** (1) parse every migration: each `create table` has
  `enable row level security` and a select policy; no `disable row level security`, no `to anon`, no
  `using (true)`; every policy mentions `auth.uid() = user_id`; `valuations` has no update/delete policy.
  (2) scan `git ls-files` for `service_role`, `sb_secret_` and JWT-shaped strings (`eyJ...\.eyJ...`);
  only `config.js` may hold a key, and its JWT payload must decode to `role: anon` (publishable key
  `sb_publishable_` also allowed). The vendored library is excluded from the scan.

## Consequences
- Regex parsing of SQL is a guard, not proof; it can miss odd SQL. Real RLS behaviour is verified once by
  hand (signed out returns nothing) when #56 is done.
- Append-only means mistakes stay in history; the UI shows the latest entry and the list.
- Vendored library must be bumped by hand (security fixes); note the version in the file header.
- Follow-up: the optional low/high issue adds columns by a new migration.
