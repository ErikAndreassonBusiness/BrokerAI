---
name: roadmap
description: Roadmap issues #41-#53 for the four open features, order, and decisions
metadata:
  type: project
---

Created 2026-11-02 (board "BrokerAI" is project #1, owner ErikAndreassonBusiness).
- Item 1 AI summary + SWOT: #41 arch -> #42 data -> #43 UI
- Item 2 Valuation history: #44 arch (storage for user-entered data, shared with item 3) -> #45 backend -> #46 UI
- Item 3 Revenue charts + customers: #47 arch (breakdown format + refill; also covers item 4 text) -> #48 data -> #49 charts; #50 customers (needs #45, #49)
- Item 4 CEO letter: #51 arch (needs #47) -> #52 data -> #53 UI
Iteration 1 (Ready): #41, #42, #43, #44.
**Why:** dependency order agreed with Erik. **How to apply:** update status here as PRs land; the report agent may only write data/financials and data/updates.json today, so each data issue widens that on purpose.

Update 2026-11-02 (Erik's decisions):
- #44 is now "hosted backend (Supabase or similar) for user data"; replaces local-FastAPI-then-commit. Covers valuations #45/#46, customers #50, notes #54.
- #54 = Erik's own notes feature (blocked by #44).
- SWOT/summary refreshed monthly from weekly news (#41/#42).
- Valuation = one number; range is optional/low priority, source of range undecided (#46).
- CEO letter full text stays local and gitignored; only derived comparison committed (#51-#53). #51 no longer blocked by #47.
- ADRs 0001/0002 in PR #55. New issues: #56 Supabase setup+RLS tests (arch), #57 frontend sign-in client, #58 export button. #45/#46/#50/#54 blocked by #56/#57. #42 holds validate+todo+AGENT/reports.yml (+ AGENT.md hosted-data line); #43 UI.
