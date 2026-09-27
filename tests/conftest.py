from typing import ClassVar

import pytest

from backend import market


class FakeTicker:
    """Stands in for yfinance.Ticker so tests never touch the network."""

    infos: ClassVar[dict] = {}

    def __init__(self, ticker):
        if ticker not in self.infos:
            raise RuntimeError(f"network error for {ticker}")
        self.info = self.infos[ticker]


@pytest.fixture
def fake_yahoo(monkeypatch):
    """Returns a dict: ticker -> yfinance info. Tickers not in it raise."""
    infos = {}
    FakeTicker.infos = infos
    monkeypatch.setattr(market.yf, "Ticker", FakeTicker)
    return infos


def yahoo_info(**overrides):
    info = {
        "regularMarketPrice": 181.1,
        "regularMarketChangePercent": 1.06,
        "marketCap": 10498825216,
        "trailingPE": 19.92,
        "dividendYield": 3.04,
        "fiftyTwoWeekHigh": 187.0,
        "fiftyTwoWeekLow": 135.1,
        "currency": "SEK",
        "regularMarketTime": 1790350197,
    }
    info.update(overrides)
    return info
