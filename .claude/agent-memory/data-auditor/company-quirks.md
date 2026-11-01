---
name: company-quirks
description: Per-company reporting quirks to check first when auditing an agent/reports PR
metadata:
  type: project
---

- **TOM.OL (TOMRA Systems):** reported in NOK until 2024-Q1 (those quarters have `"currency": "NOK"`) and
  in EUR from 2024-Q2. The quarters 2024-Q2 … 2025-Q1 carry `comparatives`: the year-earlier quarter in EUR,
  as printed in each report.
- **RVRC.ST (RVRC Holding) and INISS-B.ST (Inission):** fiscal years that don't follow the calendar year.
  `period` must be the calendar quarter the report period ends in, never the fiscal quarter name.
- **gross_profit null:** in every stored quarter of AQ.ST, BORG.ST, HANZA.ST and INISS-B.ST (as of
  2026-11-01), probably because their income statements are by nature of expense. Not yet confirmed against
  the reports. Partly null: RVRC.ST (6 of 14 quarters) and TOM.OL (3 of 21).

**Why:** Erik named the TOMRA and fiscal-year quirks when this agent was set up (2026-11-01); the
gross_profit list comes from the stored data on that date.
**How to apply:** check these first when auditing those companies, and update this file when a report
confirms or contradicts an entry.
