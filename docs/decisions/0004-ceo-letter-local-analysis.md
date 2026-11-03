# 0004 - CEO letter ("VD har ordet"): local text, committed comparison (issue #51)

Status: accepted. Date: 2026-11-03.

## Context
Erik wants to see how the CEO's tone and topics change from quarter to quarter. Erik's decision: the full
letter text stays only on his Mac, in a gitignored place, and never reaches the public repo (copyright).
The report agent runs in GitHub Actions and Pages is static, so neither can read local files. Each stored
quarter already has a `source_url`. No new services.

## Options
1. Agent compares in Actions. Needs the text in the repo or the runner. Rejected by Erik's rule.
2. Local text, local Claude Code session compares, only a small derived JSON is committed.
3. Put the text in Supabase (ADR 0002). Still stores copyrighted text on a hosted service. Rejected.

## Decision
Option 2.
- **Local text:** `private/` at the repo root, in `.gitignore`. `private/reports/<ticker>/<period>.pdf` is
  the downloaded report, `private/ceo-letters/<ticker>/<period>.txt` the extracted letter.
- **Fetch:** `uv run python -m app.backend.letters fetch <ticker> <period>` reads the saved `source_url`
  and downloads the file to `private/reports/` (existing HTTP library, no new dependency). Claude Code
  then reads the PDF, saves the letter to `private/ceo-letters/`, compares it with the previous
  quarter's `.txt` and writes the derived file. Erik runs this per quarter; the Actions agent never does.
- **Committed output:** `data/ceo_letters/<ticker>.json`, `{ticker, comparisons: [ {period, compared_to,
  source_url, tone: {previous, current}, dropped_topics[], new_topics[], changed_wording: [{topic,
  before, after}], summary} ]}`. `tone` is negative/neutral/positive. Limits: topics max 6 each and 40
  chars; wording `before`/`after` max 6 words; `summary` max 300 chars (own words). No quote longer than
  6 words. Comparisons are appended and never rewritten, so the file keeps the history of how the letters
  changed. A `trend` block, `{from, to, summary}` (max 300 chars, own words), describes how tone and topics
  moved over the newest 8 comparisons (about two years). It is rewritten at each run from the stored
  comparisons, not from old letter texts, so older `.txt` files are not needed for it. Erik commits it in a
  normal PR, so `tests.yml` runs.
- **validate.py:** checks the limits and enums above (including `trend`: `from` and `to` are stored
  comparison periods, `from` before `to`); `period` and `compared_to` exist in the ticker's
  financials with `compared_to` earlier; `source_url` equals the stored one; and fails if `git ls-files
  private` returns anything (the repo-side guard against committing the text). It cannot see the full
  text, so quote length limits are the check.
- **Agent kept away:** nothing to widen. `data/ceo_letters/` is not in AGENT.md's allowed paths nor in
  `reports.yml`'s `git add`, so the agent neither writes nor commits it.
- **Site (#53):** a section "VD-brev, jämförelse" on the stock page, labelled AI-generated, with the
  latest comparison: tone before → now, dropped/new topics, wording changes as `bra → mycket starkt`, link
  to the report. The trend summary for the period above it, and tone per
  quarter over the period as a simple row. Older comparisons collapsed. Hidden when no file exists. No letter text.

## Consequences
- Manual per quarter; a quarter without a local run simply has no comparison. Erik's text goes to
  Anthropic in the local Claude session, as any report he reads there.
- Gitignore only protects against accident; the validate check catches a text file that is committed.
- Follow-ups: #52 builds the fetch script, `.gitignore`, format, validate and tests; #53 the section.
