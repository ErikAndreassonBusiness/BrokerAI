# Stock Tracker (BrokerAI)

A free, personal website for following my stocks: live key data from Yahoo Finance and
quarterly financials that a Claude agent reads from the official reports.

**Stack:** GitHub Pages (website) · JSON files in `data/` (storage) · Python/uv backend ·
GitHub Actions (daily prices, weekly report agent).

## Run locally

Needs [uv](https://docs.astral.sh/uv/). Never use pip.

```bash
uv sync                                 # install Python and all packages
uv run fastapi dev app/backend/main.py  # local API on http://127.0.0.1:8000 (docs at /docs)
uv run python -m app.backend.export     # fetch live key data from Yahoo -> data/quotes.json
uv run python -m app.backend.validate   # check all files in data/
uv run pytest                           # run the tests (no network needed)
uv run ruff check                       # lint
```

API endpoints: `/api/companies`, `/api/quotes/{ticker}` (live from Yahoo) and
`/api/financials/{ticker}` (stored quarters from the reports).

## How updates work

- **Publish site** (`.github/workflows/pages.yml`): weekdays after the Stockholm close, on every merge
  to `main`, or via _Run workflow_. Fetches fresh prices with yfinance and publishes `app/frontend/` and
  `data/` to GitHub Pages. Prices are not committed.
- **Report agent** (`.github/workflows/reports.yml`): every Sunday, or via _Run workflow_. Claude follows
  `AGENT.md`, adds new quarters to `data/financials/` and a weekly news entry to `data/updates.json`,
  and opens (or adds to) one pull request on the `agent/reports` branch. Review the numbers against
  each quarter's source link, then merge.

## One-time setup

1. **Pages**: repo → Settings → Pages → Source: _GitHub Actions_.
2. **Let workflows open PRs**: Settings → Actions → General → Workflow permissions →
   tick _Allow GitHub Actions to create and approve pull requests_.
3. **Give the agent access to Claude**: in your own terminal run `claude setup-token`, then
   `gh secret set CLAUDE_CODE_OAUTH_TOKEN` and paste the token there.
4. **First fill**: Actions → _Report agent_ → _Run workflow_. It reads at most 12 reports per run
   (adjustable), so the first 15 quarters take several runs. All runs add to the same PR.

## Good to know

- The GitHub Pages site is **public** (the page asks search engines not to index it).
  Don't add personal info like number of shares or amounts invested.
- The agent uses your Claude subscription's usage when it runs.
- Figures are extracted by AI: check the linked source before acting on a number.
