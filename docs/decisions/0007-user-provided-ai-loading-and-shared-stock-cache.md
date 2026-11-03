# 0007 - Users load new stocks with their own AI; shared cache (Phase 2)

Status: proposed. Date: 2026-11-03. Needs ADR 0006 (user identity) and a research spike first.

## Context
Erik's idea: a user links their own AI plan and loads the data for a stock that is not on the site yet; if
someone already loaded it, everyone reuses that data. Today new stocks reach the site only when Erik adds
them to `data/companies.json`; the Sunday agent extracts the reports (`AGENT.md`), `data-auditor` and
`validate.py` check them, and git history keeps them. User-loaded data cannot go through git (no one but the agent
writes there, via a reviewed PR).

Constraints (verified by Erik):
- Anthropic forbids third-party apps from using Claude Free/Pro/Max subscription OAuth (Feb 2026 terms).
  The Claude option is therefore **bring your own API key** (pay per use), not "link my Claude Pro".
- OpenAI launched "Sign in with ChatGPT" (~Oct 2026) so third-party apps can use a subscriber's plan
  allowance; reported with about 16 launch partners. **Whether any developer can integrate is
  unverified.** Not a basis for a commitment.
- Company IR sites and PDFs usually block cross-origin browser fetches; Pages cannot run code.
- The repo and site are public; Supabase holds only private rows and, per ADR 0005, no key in the repo.

## Options: where extraction runs
A. **Browser.** The user's key stays in the tab. The user gives the report as an uploaded PDF or a URL that
   the provider fetches itself (Claude can take a URL document source; to be verified) so CORS on IR sites
   does not matter. The browser writes the result through a Postgres function (RPC) that validates the
   JSON in SQL. Our servers never see the key; no new language or deploy path. Weaker: validation runs
   in plpgsql, duplicating `validate.py`; provider CORS support must be verified.
B. **Supabase Edge Function (Deno).** The browser sends the key per request; the function fetches the
   report, calls the AI, validates, writes with a server-side secret. Handles any IR site. Costs: we
   carry users' keys in transit, an SSRF and abuse surface (fetching arbitrary URLs), a TypeScript
   code base and a deploy path (ADR 0005 chose no CLI/token), and a third copy of the data rules.
C. **Request queue only.** A user asks for a ticker (`stock_requests` row); Erik adds it to
   `companies.json` and the agent loads it in the next Sunday run. No keys, reviewed, in git. Slow and
   not what Erik asked for, but zero new risk. This is the fallback.

## Options: where shared data lives
i. Git `data/`: not possible for user writes. ii. A Supabase table `shared_financials`, readable by
signed-in users. iii. ii plus a promote path to git (below).

## Decision (direction, to be confirmed by the spike)
- **Run the spike first** (one issue, time-boxed, no product code). Questions: (1) can any developer use
  "Sign in with ChatGPT", on what terms; (2) does Claude accept browser calls with the user's key and a
  report URL; (3) the cost in tokens and money of loading one stock like `AGENT.md` does; (4) Edge Function
  limits on the free tier for a PDF job; (5) is an uploaded PDF acceptable friction. Result: pick A, B or C.
- **Lean: A with RPC validation, falling back to C** if the provider cannot be called from the browser.
  B only if A is impossible and Erik accepts the key and SSRF risk.
- **Keys:** never stored, not in the database, localStorage or logs; held in memory for the one job. Users
  are told to use a key with a spend limit. "Sign in with ChatGPT" is added only if the spike verifies it.
- **Shared cache: option iii.** Table `shared_financials` (`ticker`, `quarter`, `values jsonb`,
  `source_url`, `loaded_by`, `loaded_at`, `status`), unique per `(ticker, quarter)`, insert-only, one
  row wins, no update or delete for users. Select for `authenticated`; `loaded_by` hidden from other
  users. Writes only through the validating RPC, never by direct table insert. RLS here is
  `to authenticated using (true)` on select: the ADR 0005 CI rule "every policy uses `auth.uid() =
  user_id`" must be relaxed for this one named table, deliberately, in a test that lists it.
- **Trust:** rows show as "loaded by a user's AI, not reviewed" with the source link. Minimum checks in
  the RPC: JSON shape as `AGENT.md`, `null` instead of 0 or guesses, source URL must be https, sane value
  ranges, revenue breakdown sums as `validate.py`. A second load that disagrees with a stored quarter
  does not overwrite; it is flagged for Erik. Erik deletes bad rows in the dashboard.
- **Promote to git:** when Erik adds the ticker to `companies.json`, the agent extracts it as usual
  (reviewed PR); the git data then supersedes the cache row and quotes start (prices exist only for
  tickers in `companies.json`, because the export reads that list). Until then a cached stock has no live
  price or P/E, and the site says so.
- **Limits:** the user pays tokens. Erik's costs are Supabase calls only. Add a per-user daily cap on
  loads (counter table checked in the RPC), a maximum quarters per load, and invite-only access.
- **Agent and workflows:** unchanged. The agent never reads Supabase and gets no secret; `AGENT.md`
  keeps its line about hosted data. No `.github/` change, so the agent-PR rule is not triggered.

## Consequences
- A second, unreviewed data path next to the audited one; the UI must always label it.
- SQL-side validation will drift from `validate.py` unless one test compares fixtures through both.
- If option B is chosen, a new language, deploy process and secret store enter the repo; revisit CI.
- Follow-up issues: (1) spike; (2) decision update of this ADR from its result; (3) `shared_financials`
  migration, RPC and CI test; (4) load UI; (5) promote and supersede flow in the frontend.

## Risks for planning
- Provider terms change quickly (subscription access was banned within a year); keep the provider
  behind one small module and do not promise ChatGPT linking before the spike.
- Prompt injection in an uploaded or fetched report only harms the data it produces: hence the checks.
- Do not build this before Phase 1 ships and is used.

## Open questions for Erik
1. Is key-based loading enough, or is plan-linking (ChatGPT) a must? (If a must, the spike gates it.)
2. Is an uploaded PDF or pasted report URL acceptable instead of the site finding the report itself?
3. Are unreviewed numbers from other users acceptable, shown with a label?
4. Should users be able to request a stock for you to add (option C) in addition?
5. Daily cap per user: what number?
