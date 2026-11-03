# 0007 - Users request new stocks; Erik adds them (request queue)

Status: proposed. Date: 2026-11-03. Needs ADR 0006 (user identity). Replaces an earlier draft of this ADR
(user-provided AI loading with a shared cache), which Erik rejected.

## Context
Invited users (2-10) can only follow stocks already in `data/companies.json`. They need a way to ask for
a stock that is missing. Today a stock gets on the site when Erik adds it to `companies.json` by PR (the
ticker verified by fetching it, per CLAUDE.md); the Sunday agent then extracts the reports (`AGENT.md`),
`data-auditor` and `validate.py` check them, and git keeps them. Prices exist only for tickers in
`companies.json`. User-written data cannot go through git, and Erik wants every number to stay reviewed.

## Options
A. **Request queue (chosen).** A table of requests; Erik decides; the existing flow loads the stock.
B. Users load stocks with their own AI and share a cache: rejected, see below.
C. Users email or message Erik outside the site: no code, but no status for the user and nothing to track.

## Decision
- **Table `stock_requests`** (migration `supabase/migrations/<ts>_create_stock_requests.sql`): `id uuid pk`,
  `user_id uuid not null default auth.uid()`, `ticker text not null` (check `^[A-Za-z0-9.-]{1,20}$`,
  Yahoo format such as `VOLV-B.ST`), `name text not null default ''` (free text help for Erik),
  `status text not null default 'requested'` (check: `requested`, `approved`, `rejected`, `added`),
  `created_at timestamptz default now()`; unique on `(user_id, lower(ticker))`.
- **RLS:** on; policies `to authenticated` with `auth.uid() = user_id`: select own rows, insert with check
  that also forces `status = 'requested'`. No update, no delete, no `anon`. Users cannot change a status.
- **Site:** on the personal home page (ADR 0006) a "Request a stock" form (ticker, optional name) and a
  short list of the user's own requests with their status. The form refuses tickers already in
  `companies.json` (it offers to add them to the watchlist instead). The site cannot verify a ticker
  (yfinance runs only in the backend); Erik does.
- **How Erik sees and approves, without a key in the browser: the Supabase dashboard (Table Editor).**
  As project owner he bypasses RLS, reads all requests, and edits `status`. No `is_admin` column, no
  admin page, no `service_role` key anywhere. For 2-10 users this is all that is needed; an in-site
  admin view can be added later if volume grows (it would need an `is_admin` check in RLS and its own ADR).
- **Flow:** user requests -> Erik reviews in the dashboard, sets `approved` or `rejected` -> for approved
  ones he adds the ticker, name, currency and `ir_url` to `companies.json` by PR (verifying the ticker
  by fetching it) -> after merge he sets `added` -> the Sunday agent loads the reports as today, and the
  nightly build adds prices. The stock then appears in every user's picker. Expect up to about a week
  before numbers show. Erik is not notified automatically; he checks the dashboard (for instance before
  the Sunday run).
- **CI:** the ADR 0005 rules in `supabase_check.py` already cover the file (RLS, select policy,
  `auth.uid() = user_id`). Add tests that `stock_requests` has no update or delete policy and that the
  insert policy forces `status = 'requested'`, plus JS tests for the form and the empty and unavailable
  states.
- **Unchanged:** `.github/`, `reports.yml`, `AGENT.md`, `validate.py`, `todo.py`. The agent never reads
  Supabase and gets no secret.

## Rejected options (user-provided AI loading with a shared cache)
- **Claude subscription linking:** Anthropic's terms (Feb 2026) forbid third-party apps from using Claude
  Free/Pro/Max OAuth; only API keys are allowed, which means pay per use for each user.
- **"Sign in with ChatGPT":** launched ~Oct 2026 with about 16 partners; whether any developer can use it
  is unverified, so it is no basis for a decision.
- **Trust and quality:** numbers loaded by users' AI would be unreviewed, skip `data-auditor`, and need
  a second copy of the `validate.py` rules (in SQL or Deno) that could drift. They also could not enter
  git, so a second data path would sit next to the audited one.
- **Key handling and abuse:** users' API keys would pass through the browser or an Edge Function; storing
  them is out, and a fetching function adds an SSRF and cost surface.
Revisit only if the number of users or requests makes manual adding a real burden.

## Consequences
- Loading a new stock is slow (Erik's PR plus the weekly run) but every number stays reviewed and in git.
- `companies.json` growth is still Erik's decision, so the agent's weekly work and cost stay under his
  control.
- Erik, as project owner, can read all requests (and all other user rows) in the dashboard.
- Follow-up issues: (1) `stock_requests` migration and CI tests; (2) request form and status list on the
  home page; (3) a README note on the manual approval flow. Order: after ADR 0006's watchlist and home
  page.

## Risks for planning
- Requests pile up unseen if Erik does not look at the dashboard; the user only sees "requested".
- A user may type a wrong or non-Yahoo ticker; Erik rejects it, and the status tells the user.
- Public repo: no ticker lists tied to users, no invitee addresses in files or issues.

## Open questions for Erik
None blocking. Optional: should a rejected request show a short reason to the user (needs one extra
`reason` column that you fill in the dashboard)?
