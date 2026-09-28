"""Local API and website for the stock tracker.

Usage: uv run fastapi dev app/backend/main.py  (site on http://127.0.0.1:8000)
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.backend import market
from app.backend.storage import DATA_DIR, read_json

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="BrokerAI")


def _company(ticker: str) -> dict:
    for company in read_json(DATA_DIR / "companies.json", []):
        if company["ticker"] == ticker:
            return company
    raise HTTPException(status_code=404, detail=f"Unknown ticker {ticker}")


@app.get("/api/companies")
def companies() -> list[dict]:
    return read_json(DATA_DIR / "companies.json", [])


@app.get("/api/quotes/{ticker}")
def quote(ticker: str) -> dict:
    _company(ticker)
    try:
        return market.fetch_quote(ticker)
    except Exception as error:
        raise HTTPException(
            status_code=502, detail=f"Could not fetch {ticker} from Yahoo"
        ) from error


@app.get("/api/financials/{ticker}")
def financials(ticker: str) -> dict:
    company = _company(ticker)
    empty = {"ticker": ticker, "currency": company["report_currency"], "quarters": []}
    return read_json(DATA_DIR / "financials" / f"{ticker}.json", empty)


# The website, with the same paths as on GitHub Pages. Mounted last so the API routes win.
app.mount("/client", StaticFiles(directory=FRONTEND_DIR / "client"), name="client")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
app.mount(
    "/", StaticFiles(directory=FRONTEND_DIR / "templates", html=True), name="site"
)
