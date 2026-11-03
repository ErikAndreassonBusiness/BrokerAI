---
name: architecture-decisions
description: Decision records made by the architect with issue numbers and where they are stored (docs/decisions/)
metadata:
  type: project
---

Decision records live in `docs/decisions/NNNN-<title>.md` (no earlier location existed).
- #41 (ADR 0001, proposed 2026-11-02): AI summary + SWOT in `data/summaries/<ticker>.json`; monthly refresh inside the weekly `reports.yml` run via a "summary due" list in `todo.py` (no second workflow); AGENT.md, reports.yml `git add` and validate.py widened together in a later issue.
- #44 (ADR 0002, proposed 2026-11-02): Supabase for user-entered data (valuations, customers, notes), set up before #45; site read-only until then; single-user magic-link auth, RLS, anon key public, service_role never in repo; export button for notes (no scheduled backups into the public repo).

**How to apply:** check status with Erik before building on either; both were "proposed" pending his approval.

- #47 (ADR 0003, proposed 2026-11-03): optional per-quarter `breakdown {geography, segment}` maps (name → MSEK/null) beside `values`; absent = not looked at (refill pseudo keys `breakdown.*`), null dimension = not reported; reuse stored names; validate sum within max(2 %, parts) of revenue.
- #51 (ADR 0004, proposed 2026-11-03): letters only in gitignored `private/`; local fetch script + local Claude Code compare; derived `data/ceo_letters/<ticker>.json` (tone, topics, short wording changes, no long quotes); validate fails if `git ls-files private` non-empty; agent not widened.
- #56 (ADR 0005, proposed 2026-11-03): Supabase schema details: valuations append-only (select+insert policies only, no updated_at, low/high added later as nullable), notes one row per ticker, policies `to authenticated` with `auth.uid() = user_id` (no pinned id); `supabase/migrations/` applied via SQL editor; `client/config.js` + vendored supabase-js; pytest SQL/secret scan.
- ADR 0006 + 0007 (proposed 2026-11-03, no issue yet, Erik answered the open questions): 0006 = Google-only sign-in, invite only via admin-created users in the dashboard (fallback: allowlist + before-user-created hook; unverified: OAuth linking with sign-ups off, needs manual test), `watchlist` table with RLS, designed landing page when signed out/unavailable, empty-start personal home page when signed in; Supabase outage = no stocks, accepted. 0007 (docs/decisions/0007-stock-requests-queue.md) = request queue: `stock_requests` table, Erik approves in the Supabase dashboard (no is_admin, no service_role), adds ticker to companies.json by PR, weekly agent loads it. Rejected: user-provided AI + shared cache (Claude subscription OAuth banned, ChatGPT sign-in unverified, unreviewed data, key handling).
- ADR 0008 (proposed 2026-11-03, issue #92; supersedes the sign-in part of 0006, Google dropped, nothing was set up there): email + password via Supabase email provider (stays on, sign-ups off, admin-created users with temp password + Auto Confirm). Temp password detected by absent `user_metadata.own_password` (set together with the password in one `updateUser`; no dashboard step). Forgot password via `resetPasswordForEmail` + `PASSWORD_RECOVERY` (needs custom SMTP: Gmail app password vs provider+domain, Erik picks). Keep supabase-js default implicit flow (works across devices). Settings: min length 10, Secure password change OFF, leaked-password protection probably paid (unverified). Erik's own id kept; remove magic link (#85) last.
