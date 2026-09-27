# BrokerAI — rules for Claude Code

Personal website for following my stocks. I look at and analyze the numbers; I write my own
notes per stock. Owner: Erik. Keep it simple — no features I didn't ask for.

## How we work (always follow)

1. **Plan first.** When I ask for something, start in plan mode: read the relevant code, then
   present a short plan (what changes, which files, risks, how you'll test). Don't edit
   anything until I approve the plan.
2. **Ask before every change.** After the plan is approved, stay in the default (manual) permission
   mode: I want to approve each file edit and command. Never switch to auto-accept or bypass modes yourself.
3. **Always work on a branch.** Never commit to or push `main` directly.
   - Start from an up-to-date main: `git switch main && git pull`
   - Branch names: `feat/<short-name>`, `fix/<short-name>`, `chore/<short-name>`
   - Small, focused commits with clear messages
   - Push the branch and open a pull request with `gh pr create`. I review and merge.
4. **Review your own changes before you say you're done.** Run `git diff main...HEAD` and check:
   - **Errors:** does it run? Run the tests, `uv run ruff check`, and start the app if relevant.
   - **Ghost code:** unused imports, functions or files; leftover debug prints; commented-out code;
     duplicated logic; TODOs; placeholder or made-up values; files created but never used.
   - **Scope:** did you change anything I didn't ask for? Revert it or tell me.
   - Then give me a short summary: what changed, what you tested, anything you're unsure about.
5. If something is unclear, ask me instead of guessing.

## Security

- The GitHub token lives in my `gh` login / keychain. Never print it, write it to a file, or commit it.
- Never commit `.env` files or secrets. Keep `.env` in `.gitignore`.
- No force-pushes. Don't rewrite history on shared branches.

## Stack

- **Python via uv only.** Never use `pip` or `pip install`.
  - Add packages: `uv add <pkg>` (dev tools: `uv add --dev <pkg>`)
  - Run things: `uv run <command>`; sync: `uv sync`. Commit `pyproject.toml` and `uv.lock`.
- **Backend:** FastAPI (Python) in `app/backend/`. Run locally with `uv run fastapi dev app/backend/main.py`.
- **Market data:** `yfinance` for live key data only. Tickers must be Yahoo Finance format, e.g. `VOLV-B.ST`,
  `INVE-B.ST` (Stockholm = `.ST`, share class with a dash). Verify every new ticker by fetching it before saving.
- **Quarterly financials:** extracted by Claude from the official reports (see `AGENT.md`), each quarter
  with its source link. Check with `uv run python -m app.backend.validate`.
- **Frontend:** static HTML/CSS/JS (no framework) in `app/frontend/` (`templates/` for HTML, `client/` for JS/CSS),
  published to GitHub Pages by a GitHub Actions workflow (Pages can only publish the repo root or `/docs`
  straight from a branch). GitHub Pages can't run Python, so the site reads JSON files in `data/` that the
  backend exports.
- **Tests:** pytest (`uv run pytest`). Lint/format: ruff.

## Data conventions

- Financial tables: **line items as rows, quarters as columns** (oldest left → newest right).
- Amounts in millions of the reporting currency; per-share values as-is. Missing values are `null`,
  never 0 and never estimated.
- Store fetched quarters so history builds up over time; only fetch what's new.
- Show numbers in Swedish format (`sv-SE`).

## Notes

- My notes per stock are mine: never edit or delete them unless I explicitly ask.
