import pytest

from backend.market import fetch_quote
from tests.conftest import yahoo_info


def test_fetch_quote_maps_fields(fake_yahoo):
    fake_yahoo["INWI.ST"] = yahoo_info()

    quote = fetch_quote("INWI.ST")

    assert quote == {
        "price": 181.1,
        "change_pct": 1.06,
        "market_cap": 10498.8,
        "pe": 19.92,
        "dividend_yield": 3.04,
        "high_52w": 187.0,
        "low_52w": 135.1,
        "currency": "SEK",
        "quote_time": "2026-09-25T15:29:57+00:00",
    }


def test_missing_and_nan_values_become_none(fake_yahoo):
    info = yahoo_info(trailingPE=float("nan"), marketCap=None)
    del info["dividendYield"]
    fake_yahoo["WAYS.ST"] = info

    quote = fetch_quote("WAYS.ST")

    assert quote["pe"] is None
    assert quote["market_cap"] is None
    assert quote["dividend_yield"] is None


def test_no_price_raises(fake_yahoo):
    fake_yahoo["BAD.ST"] = {}

    with pytest.raises(ValueError):
        fetch_quote("BAD.ST")
