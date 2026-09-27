from app.backend.export import export_quotes
from app.backend.storage import read_json, write_json
from tests.conftest import yahoo_info


def setup_data(tmp_path, tickers, old_quotes=None):
    write_json(tmp_path / "companies.json", [{"ticker": t, "name": t} for t in tickers])
    if old_quotes is not None:
        write_json(
            tmp_path / "quotes.json", {"updated_at": "old", "quotes": old_quotes}
        )


def test_writes_all_quotes(tmp_path, fake_yahoo):
    setup_data(tmp_path, ["INWI.ST", "AQ.ST"])
    fake_yahoo["INWI.ST"] = yahoo_info()
    fake_yahoo["AQ.ST"] = yahoo_info(regularMarketPrice=234.0)

    assert export_quotes(tmp_path) is True

    saved = read_json(tmp_path / "quotes.json")
    assert set(saved["quotes"]) == {"INWI.ST", "AQ.ST"}
    assert saved["quotes"]["AQ.ST"]["price"] == 234.0
    assert saved["updated_at"] != "old"


def test_failing_stock_keeps_old_values(tmp_path, fake_yahoo):
    old = {"AQ.ST": {"price": 200.0}}
    setup_data(tmp_path, ["INWI.ST", "AQ.ST"], old_quotes=old)
    fake_yahoo["INWI.ST"] = yahoo_info()  # AQ.ST is missing, so it raises

    assert export_quotes(tmp_path) is True

    saved = read_json(tmp_path / "quotes.json")
    assert saved["quotes"]["AQ.ST"] == {"price": 200.0}
    assert saved["quotes"]["INWI.ST"]["price"] == 181.1


def test_all_failing_leaves_file_untouched(tmp_path, fake_yahoo):
    old = {"AQ.ST": {"price": 200.0}}
    setup_data(tmp_path, ["AQ.ST"], old_quotes=old)
    before = (tmp_path / "quotes.json").read_text()

    assert export_quotes(tmp_path) is False
    assert (tmp_path / "quotes.json").read_text() == before
