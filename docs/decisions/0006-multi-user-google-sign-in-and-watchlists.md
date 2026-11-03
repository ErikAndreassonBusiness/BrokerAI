# 0006 - Small multi-user site: Google sign-in, invite only, per-user watchlist

Status: proposed. Date: 2026-11-03. Builds on ADR 0002 and 0005. Phase 2 (user-loaded stocks) is ADR 0007.

## Context
Erik wants a few invited people to use the site. Decided by Erik: (1) sign-in with Google only, replacing
the email magic link; (2) invite only, nobody signs up alone; (3) each user's stock list, valuations,
customers and notes are private; signed-out visitors see only a sign-in page; the shared stock numbers
may stay public in `data/` (the JSON is findable in the public repo, accepted).

Facts: live Supabase has the email provider on and `disable_signup` true. `valuations`, `customers` and
`notes` already isolate rows by `auth.uid() = user_id` (ADR 0005), so they are multi-user ready. Today
"my stocks" is simply all of `data/companies.json`; the weekly agent and the nightly price export both
work on that whole list. The built-in Supabase mailer only sends to members of Erik's Supabase team.

## Options: invite mechanism
A. **Admin-created users, sign-ups stay off.** Erik adds each person in the dashboard (Authentication >
   Users > Add user, "Auto Confirm" on, their Google address, no email sent). No code, nothing in the repo,
   no `service_role` key anywhere. Needs a manual test: with sign-ups disabled, Google sign-in for an
   existing user with the same verified email should link the identity to that user instead of
   creating one. **Unverified, verify by manual test before relying on it.**
B. **Sign-ups on + allowlist.** Table `allowed_emails` (Erik edits it in the dashboard) checked by a
   `before user created` auth hook (Postgres function) that rejects others. Works even if A's linking
   fails; costs a function, a migration and one more thing to test. RLS alone is not enough here
   (strangers would get real accounts).
C. Invite emails from Supabase: rejected, the built-in mailer cannot reach non-team addresses.

## Decision
- **Google only.** Supabase Google provider; `auth.js` uses `signInWithOAuth({provider: "google"})` with
  PKCE and a `redirectTo` of the current page. Email provider turned off **after** Erik has signed in with
  Google and confirmed it is the same user id as before (otherwise his valuations, customers and notes
  stay with an orphaned account). An unknown Google address returns to the site with an error in the URL
  (sign-ups disabled); the page shows "No account for this address. Ask Erik for an invite."
- **Invite: option A**, falling back to B if the manual test fails. Erik never needs a key outside the
  Supabase dashboard. People must use the exact Google address Erik added (no `+` aliases).
- **Manual setup checklist (supabase/README.md gets these steps in the implementation issue):**
  1. Google Cloud: new project, OAuth consent screen (External, only `openid`, `email`, `profile`,
     publish to production; test mode expires and caps users).
  2. Create OAuth client, type Web application. Authorized redirect URI:
     `https://<project-ref>.supabase.co/auth/v1/callback`. No JavaScript origin needed.
  3. Supabase > Authentication > Providers > Google: paste client id and secret (the secret lives only
     there, never in the repo). Leave "skip nonce check" off.
  4. URL Configuration stays as set in ADR 0005 (Site URL and `.../BrokerAI/**` redirect).
  5. Manual tests: invited user signs in; uninvited Google account is refused; Erik's id unchanged.
- **Sessions:** supabase-js stores the session in localStorage and refreshes the token itself, so users
  are not asked to sign in per visit. Signing out is explicit.
- **Table `watchlist`** (migration `supabase/migrations/<ts>_create_watchlist.sql`): `user_id uuid not null
  default auth.uid()`, `ticker text not null`, `created_at timestamptz default now()`, primary key
  `(user_id, ticker)`, ticker check `^[A-Za-z0-9.-]{1,20}$`. RLS on; policies `to authenticated` with
  `auth.uid() = user_id` for select, insert (with check) and delete; no update, no `anon`. The database
  cannot know which tickers exist; the frontend ignores tickers missing from `companies.json`.
- **CI:** `app/backend/supabase_check.py` rules from ADR 0005 already cover the new file (RLS, select
  policy, `auth.uid() = user_id`); add one test that `watchlist` has no update policy and one for the
  ticker check. JS tests for `auth.js` are rewritten (OAuth call, error-in-URL message, signed-out page).
- **Signed out:** `index.html` and `stock.html` show only the "Sign in with Google" page and load no
  `data/*.json` (a UX gate, not security: the files stay reachable by URL, as accepted). If Supabase is
  unreachable, they show "Unavailable right now" and no stocks. This replaces ADR 0002's "rest of the
  site works from `data/`".
- **Signed in:** the overview lists `companies.json` filtered by the user's watchlist, with an
  add/remove control over the tickers not yet followed, and filters the news to followed tickers
  (if the `updates.json` entries carry tickers; check in the issue). An empty list shows a short prompt.
  Any ticker in `companies.json` can be opened on its stock page (shared data). Erik's current stocks are
  seeded once by a SQL insert for his user id, not committed.
- **Which tickers:** only those already in `companies.json`, which Erik curates through PRs. Each added
  ticker increases the weekly agent's work and the nightly price fetch.

## Consequences
- Supabase becomes a hard dependency of the whole site (outage or free-tier pause = no stocks shown).
  Erik accepted the pause policy in ADR 0002; the effect is now larger.
- Privacy is between users. Erik, as project owner, can read every row in the dashboard; say so to
  invitees.
- `.github/` is untouched, `AGENT.md`, `validate.py`, `todo.py` and `reports.yml` are unaffected.
- Follow-up issues: (1) Google/invite setup and manual tests; (2) `watchlist` migration and CI test;
  (3) `auth.js` Google flow and tests; (4) sign-in page and signed-out gate; (5) watchlist UI on the
  overview; (6) README/ADR 0002 notes updated. Order: 1, 2, then 3-5.

## Risks for planning
- Linking behaviour (option A) is unverified; do the manual test first, before removing the email
  provider or building on it.
- Removing the magic link locks Erik out if Google setup breaks: keep email on until Google works.
- Public repo: no Google client secret, project ref notes or invitee addresses in files or issues.

## Open questions for Erik
1. Is it acceptable that Supabase down or paused means no stocks at all for everyone?
2. You can read every user's rows in the dashboard. Are you fine with that, and will you tell invitees?
3. Should new users start empty, or with a suggested set of stocks?
4. Roughly how many people (decides whether the weekly agent budget in `reports.yml` still fits)?
