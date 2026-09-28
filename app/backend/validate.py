"""Check the JSON files in data/ before they are committed.

Usage: uv run python -m app.backend.validate
"""

import re
import sys
from datetime import date
from pathlib import Path

from app.backend.storage import DATA_DIR, read_json

LINE_ITEMS = [
    "revenue",
    "gross_profit",
    "ebit",
    "net_income",
    "eps",
    "cash",
    "inventory",
    "short_term_debt",
    "long_term_debt",
    "total_equity",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
]
QUOTE_FIELDS = {
    "price",
    "change_pct",
    "market_cap",
    "pe",
    "dividend_yield",
    "high_52w",
    "low_52w",
    "currency",
    "quote_time",
}
PERIOD = re.compile(r"^\d{4}-Q[1-4]$")


def _is_number_or_null(value) -> bool:
    return value is None or (
        isinstance(value, int | float) and not isinstance(value, bool)
    )


def _is_date(value) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def _check_companies(companies) -> tuple[list[str], set[str]]:
    errors, tickers = [], set()
    if not isinstance(companies, list):
        return ["companies.json: must be a list"], tickers
    for i, company in enumerate(companies):
        at = f"companies.json[{i}]"
        ticker = company.get("ticker")
        if not ticker:
            errors.append(f"{at}: missing ticker")
        elif ticker in tickers:
            errors.append(f"{at}: duplicate ticker {ticker}")
        tickers.add(ticker)
        for field in ("name", "currency", "report_currency"):
            if not company.get(field):
                errors.append(f"{at}: missing {field}")
        if not str(company.get("ir_url", "")).startswith("https://"):
            errors.append(f"{at}: ir_url must start with https://")
    return errors, tickers


def _check_quotes(quotes_file, tickers: set[str]) -> list[str]:
    errors = []
    if not quotes_file.get("updated_at"):
        errors.append("quotes.json: missing updated_at")
    for ticker, quote in quotes_file.get("quotes", {}).items():
        at = f"quotes.json {ticker}"
        if ticker not in tickers:
            errors.append(f"{at}: ticker not in companies.json")
        if set(quote) != QUOTE_FIELDS:
            errors.append(f"{at}: fields must be exactly {sorted(QUOTE_FIELDS)}")
        for field in QUOTE_FIELDS - {"currency", "quote_time"}:
            if not _is_number_or_null(quote.get(field)):
                errors.append(f"{at}: {field} must be a number or null")
    return errors


def _check_financials(path: Path, financials, tickers: set[str]) -> list[str]:
    name = f"financials/{path.name}"
    ticker = financials.get("ticker")
    errors = []
    if ticker not in tickers:
        errors.append(f"{name}: ticker {ticker!r} not in companies.json")
    if path.name != f"{ticker}.json":
        errors.append(f"{name}: file name must be <ticker>.json")
    if not financials.get("currency"):
        errors.append(f"{name}: missing currency")

    periods = []
    for quarter in financials.get("quarters", []):
        period = quarter.get("period")
        at = f"{name} {period}"
        if not PERIOD.match(str(period)):
            errors.append(f"{at}: period must look like 2026-Q2")
        if period in periods:
            errors.append(f"{at}: duplicate period")
        periods.append(period)
        if not _is_date(quarter.get("report_date")):
            errors.append(f"{at}: report_date must be YYYY-MM-DD")
        if not str(quarter.get("source_url", "")).startswith("https://"):
            errors.append(f"{at}: source_url must start with https://")
        values = quarter.get("values", {})
        if set(values) != set(LINE_ITEMS):
            errors.append(
                f"{at}: values must have exactly these keys: {', '.join(LINE_ITEMS)}"
            )
        for item, value in values.items():
            if not _is_number_or_null(value):
                errors.append(f"{at}: {item} must be a number or null")
    if periods != sorted(periods, key=str):
        errors.append(f"{name}: quarters must be sorted oldest first")
    return errors


def _check_updates(updates, tickers: set[str]) -> list[str]:
    if not isinstance(updates, list):
        return ["updates.json: must be a list"]
    errors = []
    dates = []
    for i, update in enumerate(updates):
        at = f"updates.json[{i}]"
        if not _is_date(update.get("date")):
            errors.append(f"{at}: date must be YYYY-MM-DD")
        dates.append(str(update.get("date")))
        if not update.get("summary"):
            errors.append(f"{at}: missing summary")
        if not isinstance(update.get("items"), list):
            errors.append(f"{at}: items must be a list")
            continue
        for j, item in enumerate(update["items"]):
            if item.get("ticker") not in tickers:
                errors.append(f"{at}.items[{j}]: ticker not in companies.json")
            if not item.get("text"):
                errors.append(f"{at}.items[{j}]: missing text")
            if not str(item.get("url", "")).startswith("https://"):
                errors.append(f"{at}.items[{j}]: url must start with https://")
    if dates != sorted(dates, reverse=True):
        errors.append("updates.json: entries must be sorted newest first")
    return errors


def validate(data_dir: Path = DATA_DIR) -> list[str]:
    """Returns a list of problems; empty means everything is valid."""
    errors, tickers = _check_companies(read_json(data_dir / "companies.json", []))
    quotes_file = read_json(data_dir / "quotes.json")
    if quotes_file is not None:
        errors += _check_quotes(quotes_file, tickers)
    for path in sorted((data_dir / "financials").glob("*.json")):
        errors += _check_financials(path, read_json(path), tickers)
    errors += _check_updates(read_json(data_dir / "updates.json", []), tickers)
    return errors


if __name__ == "__main__":
    problems = validate()
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)" if problems else "All data files are valid")
    sys.exit(1 if problems else 0)
