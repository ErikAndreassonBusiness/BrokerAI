# 0003 - Revenue by geography and by segment: data format and refill (issue #47)

Status: proposed. Date: 2026-11-03.

## Context
Erik wants revenue per quarter split by geography and by segment/industry (charts in #49). Today
`values` in `data/financials/<ticker>.json` holds only flat numbers or null, `validate.py` rejects keys
outside `LINE_ITEMS`, and `todo.py --refill` lists a quarter when a `LINE_ITEMS` key is missing from
`values`. Rules: millions of the reporting currency, missing is `null`, never estimated, a stored
quarter is never rewritten. Companies name and group segments differently and change them over time.

## Options
1. Flat keys in `values` such as `revenue_geo_sweden`. Fits the current code, but the names differ per
   company, so `LINE_ITEMS` would grow without end. Rejected.
2. A separate file `data/breakdowns/<ticker>.json`. Clean, but a second file to keep in step with the
   quarters, a new agent path and a join in the frontend.
3. An optional `breakdown` object next to `values` in each quarter. One file, one source link per
   quarter, `values` stays flat.

## Decision
Option 3. Per quarter:
`"breakdown": { "geography": {"Sverige": 410, "Norden": 220, "Övrigt": null} | null, "segment": {...} | null }`
- Names are free text, one map per dimension, amounts in millions, `null` for a part that quarter's
  report does not give. Never estimated, never 0 for unknown.
- Key `breakdown` absent = not looked at yet. A dimension set to `null` = looked, the company does not
  report it. Only an absent dimension counts as missing.
- **Refill:** `todo.py --refill` also lists a quarter when `breakdown` or one of its dimensions is
  absent, using the pseudo keys `breakdown.geography` / `breakdown.segment` in the same line format
  (`ticker period | keys | source_url`). The agent re-reads the saved `source_url` and only adds the
  missing part; it never changes existing numbers.
- **Names across quarters:** the agent reuses the exact names already stored for that ticker (latest
  quarter first). A renamed part keeps its old name. A merged or new part gets a new name and the old
  or missing quarters stay `null`/absent for it. If a company restates its segments, the new scheme
  starts from the quarters that report it; old quarters are not rewritten. Charts show gaps, not zeros.
  A remainder the report states ("Övrigt", eliminations) is stored under its own name.
- **validate.py:** `breakdown` may only have `geography` and `segment`; each is `null` or a non-empty map
  of name (max 60 chars) → number or null. If revenue and every part are numbers, the sum must be within
  max(2 % of revenue, number of parts) of `values.revenue`, otherwise an error (a sign of a wrong or
  missing part). With any null part, or null revenue, the sum check is skipped.
- **What other issues need:** #49 needs stable names and one unit per ticker (hence the name rule).
  #50 (customers, Supabase) only needs the latest segment names to let Erik tag a customer; it reads
  them from this file and no schema link is needed.

## Consequences
- `AGENT.md`, `validate.py` and `todo.py` change in the same PR (#48) so they cannot drift. Existing
  quarters have no `breakdown`, so the first refill runs list every quarter, newest first, capped as now.
- Harder: name drift is handled by agent instructions, not code; the sum check is the safety net.
- Follow-ups: #48 implements the above (fixtures for sum-ok, sum-off, null dimension); #49 reads the
  maps; no change to #50.
