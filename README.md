# Stock Tracker (BrokerAI)

A free, personal website that shows the latest quarterly reports for my stocks.
A Claude agent checks for new reports every Monday and updates the data automatically.

**Stack:** GitHub Pages (website) · JSON files in `data/` (storage) · Claude Code in GitHub Actions (weekly agent).

## Run locally

Needs [uv](https://docs.astral.sh/uv/). Never use pip.

```bash
uv sync                                  # install Python and all packages
uv run fastapi dev backend/app/main.py   # local API on http://127.0.0.1:8000 (docs at /docs)
uv run python -m backend.export          # fetch live key data from Yahoo -> data/quotes.json
uv run python -m backend.validate        # check all files in data/
uv run pytest                            # run the tests (no network needed)
uv run ruff check                        # lint
```

API endpoints: `/api/companies`, `/api/quotes/{ticker}` (live from Yahoo) and
`/api/financials/{ticker}` (stored quarters from the reports).

## Setup (one time, ~20 minutes)

1. **Open in VS Code** and start Claude Code in the terminal: `claude`.
2. **Add your stocks** to `data/companies.json`, e.g.:
   ```json
   [
     {
       "id": "volvo",
       "name": "Volvo B",
       "ticker": "VOLV B",
       "currency": "SEK",
       "ir_url": "https://www.volvogroup.com/en/investors.html"
     }
   ]
   ```
   (Or ask Claude Code: _"Add Volvo B, Investor B and Evolution to companies.json with their IR pages."_)
3. **Create a GitHub repo** and push:
   ```bash
   git add -A && git commit -m "Initial stock tracker"
   git remote add origin https://github.com/<you>/stock-tracker.git
   git push -u origin main
   ```
4. **Turn on GitHub Pages**: repo → Settings → Pages → Source: _Deploy from a branch_ → `main` / `(root)`.
   Your site appears at `https://<you>.github.io/stock-tracker/`.
5. **Give the agent access to Claude**: in your terminal run `claude setup-token`, log in, and copy the token.
   Repo → Settings → Secrets and variables → Actions → _New repository secret_:
   name `CLAUDE_CODE_OAUTH_TOKEN`, value = the token.
6. **Run it once**: repo → Actions → _Weekly report update_ → _Run workflow_.
   The first run backfills history; after a few minutes the site shows your numbers.

## Everyday use

- Open the site. The agent updates it every Monday morning.
- Want fresh data now? Actions → _Weekly report update_ → _Run workflow_.
- Change what the agent collects by editing `AGENT.md`.

## Good to know

- A free GitHub Pages site is **public** if someone knows the URL (the page asks search engines not to index it).
  Only public company data is stored here, but don't add personal info like number of shares or amounts invested.
- The agent uses your Claude subscription's usage when it runs.
- Figures are extracted by AI: check the linked source before acting on a number.
