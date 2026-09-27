"""All yfinance access lives here. Only live key data; financials come from the reports."""

import math
from datetime import UTC, datetime

import yfinance as yf


def _num(value) -> float | None:
    """Number from yfinance, or None when it's missing, NaN or not a number."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) or math.isinf(number) else number


def fetch_quote(ticker: str) -> dict:
    """Live key data for one stock. Raises if Yahoo returns no price."""
    info = yf.Ticker(ticker).info
    price = _num(info.get("regularMarketPrice"))
    if price is None:
        raise ValueError(f"No price from Yahoo for {ticker}")

    market_cap = _num(info.get("marketCap"))
    quote_time = _num(info.get("regularMarketTime"))
    return {
        "price": price,
        "change_pct": _num(info.get("regularMarketChangePercent")),
        "market_cap": round(market_cap / 1e6, 1) if market_cap is not None else None,
        "pe": _num(info.get("trailingPE")),
        # yfinance 1.x already gives the dividend yield in percent (3.04 = 3.04 %).
        "dividend_yield": _num(info.get("dividendYield")),
        "high_52w": _num(info.get("fiftyTwoWeekHigh")),
        "low_52w": _num(info.get("fiftyTwoWeekLow")),
        "currency": info.get("currency"),
        "quote_time": (
            datetime.fromtimestamp(quote_time, UTC).isoformat()
            if quote_time is not None
            else None
        ),
    }
