import pytest

from app.backend.storage import write_json
from app.backend.validate import LINE_ITEMS, validate

COMPANY = {
    "ticker": "INWI.ST",
    "name": "Inwido",
    "currency": "SEK",
    "report_currency": "SEK",
    "ir_url": "https://www.inwido.com/financials",
}


def quarter(period, **overrides):
    q = {
        "period": period,
        "report_date": "2026-07-17",
        "source_url": "https://example.com/report.pdf",
        "values": dict.fromkeys(LINE_ITEMS, 100.0),
    }
    q.update(overrides)
    return q


def write_data(tmp_path, quarters, ticker="INWI.ST"):
    write_json(tmp_path / "companies.json", [COMPANY])
    write_json(
        tmp_path / "financials" / f"{ticker}.json",
        {"ticker": ticker, "currency": "SEK", "quarters": quarters},
    )


def test_valid_data_passes(tmp_path):
    q2 = quarter("2026-Q2")
    q2["values"]["gross_profit"] = None
    write_data(tmp_path, [quarter("2026-Q1"), q2])

    assert validate(tmp_path) == []


def test_real_data_folder_is_valid():
    assert validate() == []


@pytest.mark.parametrize(
    ("quarters", "expected"),
    [
        ([quarter("2026-Q1"), quarter("2026-Q1")], "duplicate period"),
        ([quarter("2026-06")], "period must look like"),
        ([quarter("2026-Q2"), quarter("2026-Q1")], "sorted oldest first"),
        ([quarter("2026-Q1", source_url="")], "source_url"),
        ([quarter("2026-Q1", report_date="17/07/2026")], "report_date"),
        ([quarter("2026-Q1", values={"revenue": 1.0})], "values must have exactly"),
        (
            [
                quarter(
                    "2026-Q1", values={**dict.fromkeys(LINE_ITEMS, 1.0), "ebitda": 1.0}
                )
            ],
            "values must have exactly",
        ),
        (
            [
                quarter(
                    "2026-Q1",
                    values={**dict.fromkeys(LINE_ITEMS, 1.0), "revenue": "1 234"},
                )
            ],
            "revenue must be a number or null",
        ),
    ],
)
def test_bad_financials_fail(tmp_path, quarters, expected):
    write_data(tmp_path, quarters)

    errors = validate(tmp_path)

    assert any(expected in e for e in errors), errors


def test_quarter_may_have_its_own_currency(tmp_path):
    write_data(tmp_path, [quarter("2024-Q1", currency="NOK"), quarter("2024-Q2")])

    assert validate(tmp_path) == []


@pytest.mark.parametrize("currency", ["nok", "NOKK", "", None])
def test_bad_quarter_currency_fails(tmp_path, currency):
    write_data(tmp_path, [quarter("2024-Q1", currency=currency)])

    assert any("currency must be" in e for e in validate(tmp_path))


def test_unknown_ticker_fails(tmp_path):
    write_data(tmp_path, [quarter("2026-Q1")], ticker="XYZ.ST")

    assert any("not in companies.json" in e for e in validate(tmp_path))


def update(date, **item_overrides):
    item = {"ticker": "INWI.ST", "text": "Q2 report", "url": "https://example.com/pr"}
    item.update(item_overrides)
    return {"date": date, "summary": "Inwido reported Q2.", "items": [item]}


def write_updates(tmp_path, updates):
    write_json(tmp_path / "companies.json", [COMPANY])
    write_json(tmp_path / "updates.json", updates)


def test_valid_updates_pass(tmp_path):
    write_updates(tmp_path, [update("2026-09-27"), update("2026-09-20")])

    assert validate(tmp_path) == []


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ([update("2026-09-20"), update("2026-09-27")], "sorted newest first"),
        ([update("27 Sept")], "date must be"),
        ([update("2026-09-27", ticker="XYZ.ST")], "ticker not in companies.json"),
        ([update("2026-09-27", url="http://example.com")], "url must start with"),
        ([{"date": "2026-09-27", "items": []}], "missing summary"),
    ],
)
def test_bad_updates_fail(tmp_path, updates, expected):
    write_updates(tmp_path, updates)

    errors = validate(tmp_path)

    assert any(expected in e for e in errors), errors
