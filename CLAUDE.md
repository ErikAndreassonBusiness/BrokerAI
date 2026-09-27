# Stock Tracker — project notes for Claude Code

Personal website for following my stocks. I only want to **look at and analyze** the numbers;
the site doesn't need editing, logins or calculations beyond simple comparisons.

## How it works

- **Website**: plain static files (`index.html`, `app.js`, `style.css`), no build step, no framework.
  Hosted free on GitHub Pages from the `main` branch root. Charts are hand-drawn SVG in `app.js`.
- **Data**: JSON files in `data/` act as the database (no Supabase/backend):
  - `companies.json` — the stocks I follow (edited by me)
  - `reports.json` — one object per company and quarter (written by the agent)
  - `updates.json` — weekly summaries, newest first (written by the agent)
- **Agent**: `.github/workflows/weekly-update.yml` runs Claude Code in GitHub Actions every Monday
  (and on demand via "Run workflow"). It follows `AGENT.md`, updates `data/`, validates with
  `node scripts/validate.js` and commits. Auth uses my Claude subscription via the
  `CLAUDE_CODE_OAUTH_TOKEN` repo secret (created with `claude setup-token`).

## Conventions

- Amounts in millions of the reporting currency; EPS per share. Missing figures are `null`.
- Numbers shown in Swedish format (`sv-SE`). UI text in English.
- Keep it dependency-free. Keep light and dark mode working (CSS variables in `style.css`).
- Test locally with `python3 -m http.server 8000` and open http://localhost:8000.
- Run `node scripts/validate.js` after any change to `data/`.
- The data format is documented in `AGENT.md`; if you change it, update `AGENT.md`, `app.js` and `scripts/validate.js` together.
