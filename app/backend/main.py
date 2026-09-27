"""Local API for the stock tracker.

Usage: uv run fastapi dev app/backend/main.py
"""

from fastapi import FastAPI, HTTPException

from app.backend import market
from app.backend.storage import DATA_DIR, read_json

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
