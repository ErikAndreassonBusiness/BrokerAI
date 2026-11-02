# 0001 - Where the AI company summary and SWOT are stored (issue #41)

Status: proposed (Erik approves). Date: 2026-11-02.

## Context
The report agent should write a short company summary and SWOT bullets per stock, refreshed once a
month from the weekly news in `data/updates.json` and the stored reports. Today the agent may only write
`data/financials/<ticker>.json` and `data/updates.json` (AGENT.md), and `reports.yml` only runs
`git add` on those paths. Erik's notes are his own and no agent may touch them. The site is static.

## Options
1. Add a `summary` block inside `data/financials/<ticker>.json`. Fewer files, but mixes prose with
   numbers, risks the rule "never change a stored quarter", and `validate.py`/`todo.py` read that file.
2. One file per company in a new folder `data/summaries/<ticker>.json`. One more path to allow and
   validate, but isolated and easy to review in the agent PR.
3. One `data/summaries.json` for all companies. Big diffs and merge conflicts as the list grows.

## Decision
Option 2. Shape (one file per ticker, no history, git keeps it):
`{ "ticker", "updated": "YYYY-MM-DD", "summary": "2-4 sentences", "swot": { "strengths": [Item], "weaknesses": [Item], "opportunities": [Item], "threats": [Item] } }`
where `Item = { "text": "one short sentence", "sources": ["https://..."] }`. Max about 4 items per list,
every item has at least one source link from an official report or a news item already in `updates.json`.
No buy/sell advice, same neutrality rule as the news.

**Permission:** a later issue adds `data/summaries/<ticker>.json` to AGENT.md's allowed paths and to
`git add -A -- data/financials data/updates.json data/summaries` in `reports.yml`, and teaches
`validate.py` the format (required keys, date, https sources, list sizes). AGENT.md and `validate.py`
change in the same PR so they cannot drift.

**Monthly refresh:** no second workflow. The weekly run stays the only run. `todo.py` gets a
"summary due" list (like the refill list): a ticker is due when its file is missing or its `updated` is
in an earlier calendar month than today, capped per run. The prompt passes that list; the agent reads
that month's entries in `updates.json` plus the latest stored quarters. Result: the first Sunday run
of each month refreshes summaries, other Sundays do none. Same branch, same PR, same tests.

**Separation from notes:** summaries live in `data/` (public, agent-written, labelled "AI-generated" in
the UI). Erik's notes never go in `data/` and never in a path the agent may write (see ADR 0002). The UI
shows them in separate sections.

## Consequences
- New folder, new validator rules, AGENT.md and `reports.yml` widened deliberately (not by this ADR).
- A monthly run touches many tickers, so the cap may spread a refresh over several Sundays.
- Summaries can only be as good as the weekly news; weeks with "No major news" give thin input.
- Follow-ups: (a) `validate.py` + format + fixtures; (b) `todo.py` summary-due list; (c) AGENT.md and
  `reports.yml` changes (merge when no agent PR is open: `.github/` rule); (d) frontend section.
