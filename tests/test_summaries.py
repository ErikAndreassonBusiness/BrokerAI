"""Tests for issue #42: summary + SWOT files (validate.py rules, todo.py summary-due list, AGENT.md)."""

from datetime import date
from pathlib import Path

import pytest

from app.backend import todo as todo_module
from app.backend import validate as validate_module
from app.backend.storage import write_json
from app.backend.validate import validate

ROOT = Path(__file__).parent.parent
COMPANY = {
    "ticker": "A.ST",
    "name": "Alpha",
    "currency": "SEK",
    "report_currency": "SEK",
    "ir_url": "https://example.com/ir",
}
SOURCE = "https://example.com/report"


def item(text="Steady demand.", sources=(SOURCE,)):
    return {"text": text, "sources": list(sources)}


def summary_file(ticker="A.ST", **overrides):
    data = {
        "ticker": ticker,
        "updated": "2026-11-02",
        "summary": "Alpha reported steady sales. Margins were stable.",
        "swot": {
            "strengths": [item()],
            "weaknesses": [item()],
            "opportunities": [item()],
            "threats": [item()],
        },
    }
    data.update(overrides)
    return data


def write_summary(tmp_path, data=None, name="A.ST"):
    write_json(tmp_path / "companies.json", [COMPANY])
    if data is not None:
        write_json(tmp_path / "summaries" / f"{name}.json", data)


def errors_for(tmp_path):
    return [e for e in validate(tmp_path) if "summar" in e.lower()]


def test_req_42_1_valid_summary_passes(tmp_path):
    """REQ-42-1"""
    write_summary(tmp_path, summary_file())
    assert validate(tmp_path) == []


def test_req_42_1_empty_swot_lists_are_allowed(tmp_path):
    """REQ-42-1: an empty list is fine (the page shows a dash)."""
    data = summary_file()
    data["swot"]["threats"] = []
    write_summary(tmp_path, data)
    assert validate(tmp_path) == []


def test_req_42_8_no_summaries_folder_means_no_errors(tmp_path):
    """REQ-42-8"""
    write_summary(tmp_path)
    assert validate(tmp_path) == []


@pytest.mark.parametrize("key", ["ticker", "updated", "summary", "swot"])
def test_req_42_2_missing_top_level_key(tmp_path, key):
    """REQ-42-2"""
    data = summary_file()
    del data[key]
    write_summary(tmp_path, data)
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and key in e for e in errors), errors


@pytest.mark.parametrize("key", ["strengths", "weaknesses", "opportunities", "threats"])
def test_req_42_2_missing_swot_list(tmp_path, key):
    """REQ-42-2"""
    data = summary_file()
    del data["swot"][key]
    write_summary(tmp_path, data)
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and key in e for e in errors), errors


@pytest.mark.parametrize("bad", ["02/11/2026", "2026-13-40", ""])
def test_req_42_3_date_must_be_iso(tmp_path, bad):
    """REQ-42-3"""
    write_summary(tmp_path, summary_file(updated=bad))
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "updated" in e for e in errors), errors


@pytest.mark.parametrize(
    "bad_item",
    [
        item(sources=[]),
        {"text": "Steady demand."},
        {"sources": [SOURCE]},
        item(text=""),
    ],
)
def test_req_42_4_item_needs_text_and_a_source(tmp_path, bad_item):
    """REQ-42-4"""
    data = summary_file()
    data["swot"]["strengths"] = [bad_item]
    write_summary(tmp_path, data)
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "strengths" in e for e in errors), errors


def test_req_42_5_source_must_be_https(tmp_path):
    """REQ-42-5"""
    data = summary_file()
    data["swot"]["weaknesses"] = [item(sources=["http://example.com/report"])]
    write_summary(tmp_path, data)
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "weaknesses" in e for e in errors), errors


def test_req_42_6_swot_list_max_four_items(tmp_path):
    """REQ-42-6: 4 passes, 5 fails."""
    data = summary_file()
    data["swot"]["threats"] = [item() for _ in range(4)]
    write_summary(tmp_path, data)
    assert validate(tmp_path) == []

    data["swot"]["threats"] = [item() for _ in range(5)]
    write_summary(tmp_path, data)
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "threats" in e for e in errors), errors


def test_req_42_7_ticker_must_match_file_name(tmp_path):
    """REQ-42-7"""
    write_summary(tmp_path, summary_file(ticker="B.ST"))
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "ticker" in e for e in errors), errors


def test_req_42_14_summary_limits_are_named_constants():
    """REQ-42-14"""
    assert validate_module.MAX_SUMMARY_SENTENCES == 4
    assert validate_module.MAX_SUMMARY_CHARS == 600


def test_req_42_14_summary_with_five_sentences_fails(tmp_path):
    """REQ-42-14"""
    text = " ".join(f"Sentence {n} is here." for n in range(5))
    write_summary(tmp_path, summary_file(summary=text))
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "summary" in e for e in errors), errors


def test_req_42_14_summary_with_four_sentences_passes(tmp_path):
    """REQ-42-14"""
    text = " ".join(f"Sentence {n} is here." for n in range(4))
    write_summary(tmp_path, summary_file(summary=text))
    assert validate(tmp_path) == []


def test_req_42_14_summary_over_max_chars_fails(tmp_path):
    """REQ-42-14: one sentence, too many characters."""
    limit = validate_module.MAX_SUMMARY_CHARS
    write_summary(tmp_path, summary_file(summary="a" * (limit + 1) + "."))
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "summary" in e for e in errors), errors


def test_req_42_15_item_limit_is_a_named_constant():
    """REQ-42-15"""
    assert validate_module.MAX_ITEM_CHARS == 120


def test_req_42_15_item_with_two_sentences_fails(tmp_path):
    """REQ-42-15"""
    data = summary_file()
    data["swot"]["strengths"] = [item(text="First one. Second one.")]
    write_summary(tmp_path, data)
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "strengths" in e for e in errors), errors


def test_req_42_15_item_over_max_chars_fails(tmp_path):
    """REQ-42-15"""
    limit = validate_module.MAX_ITEM_CHARS
    data = summary_file()
    data["swot"]["strengths"] = [item(text="a" * (limit + 1) + ".")]
    write_summary(tmp_path, data)
    errors = validate(tmp_path)
    assert any("summaries/A.ST.json" in e and "strengths" in e for e in errors), errors


# --- todo.py: summary-due list. Expected API: summary_due(data_dir, today) -> list[str] of tickers;
# the cap is the module constant SUMMARY_CAP (None = no limit), read when the function is called.


def setup_due(tmp_path, updated: dict[str, str | None]):
    write_json(tmp_path / "companies.json", [{"ticker": t} for t in updated])
    for ticker, day in updated.items():
        if day is not None:
            write_json(
                tmp_path / "summaries" / f"{ticker}.json",
                {"ticker": ticker, "updated": day},
            )


def test_req_42_9_missing_file_is_due(tmp_path):
    """REQ-42-9"""
    setup_due(tmp_path, {"A.ST": None})
    assert todo_module.summary_due(tmp_path, date(2026, 11, 2)) == ["A.ST"]


def test_req_42_10_earlier_month_is_due(tmp_path):
    """REQ-42-10"""
    setup_due(tmp_path, {"A.ST": "2026-10-26"})
    assert todo_module.summary_due(tmp_path, date(2026, 11, 1)) == ["A.ST"]


def test_req_42_10_same_month_in_an_earlier_year_is_due(tmp_path):
    """REQ-42-10"""
    setup_due(tmp_path, {"A.ST": "2025-11-05"})
    assert todo_module.summary_due(tmp_path, date(2026, 11, 8)) == ["A.ST"]


def test_req_42_11_current_month_is_not_due(tmp_path):
    """REQ-42-11"""
    setup_due(tmp_path, {"A.ST": "2026-11-01"})
    assert todo_module.summary_due(tmp_path, date(2026, 11, 8)) == []


def test_req_42_12_default_cap_is_no_limit(tmp_path):
    """REQ-42-12"""
    assert todo_module.SUMMARY_CAP is None
    setup_due(tmp_path, {f"T{n}.ST": None for n in range(12)})
    assert len(todo_module.summary_due(tmp_path, date(2026, 11, 2))) == 12


def test_req_42_12_cap_limits_the_list(tmp_path, monkeypatch):
    """REQ-42-12: 5 of 12 now; the other 7 stay due (still no file) for the next run."""
    monkeypatch.setattr(todo_module, "SUMMARY_CAP", 5)
    setup_due(tmp_path, {f"T{n}.ST": None for n in range(12)})
    first = todo_module.summary_due(tmp_path, date(2026, 11, 2))
    assert len(first) == 5

    for ticker in first:
        write_json(
            tmp_path / "summaries" / f"{ticker}.json",
            {"ticker": ticker, "updated": "2026-11-02"},
        )
    second = todo_module.summary_due(tmp_path, date(2026, 11, 9))
    assert len(second) == 5
    assert not set(first) & set(second)


# --- AGENT.md (REQ-42-13, REQ-42-16). reports.yml is under .github/ and is not read here
# beyond a text check; the wording checks are loose on purpose.


def test_req_42_13_agent_md_allows_summaries_and_forbids_hosted_data():
    """REQ-42-13"""
    text = (ROOT / "AGENT.md").read_text()
    assert "data/summaries/<ticker>.json" in text
    assert "hosted" in text.lower()
    assert "never touch" in text.lower()


def test_req_42_13_reports_yml_commits_summaries_and_passes_the_list():
    """REQ-42-13"""
    text = (ROOT / ".github" / "workflows" / "reports.yml").read_text()
    assert "data/summaries" in text
    assert "summary" in text.lower() and "app.backend.todo --summaries" in text


def test_req_42_16_agent_md_asks_for_short_statements_and_swedish_numbers():
    """REQ-42-16"""
    text = (ROOT / "AGENT.md").read_text().lower()
    assert "as short as possible" in text
    assert "sv-se" in text
