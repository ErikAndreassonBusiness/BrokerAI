"""Tests for issue #52: local CEO-letter fetch, .gitignore, validate rules for ceo_letters.

Interface assumed:
- app.backend.letters.download(url: str) -> bytes   (the only network call; mocked here)
- app.backend.letters.fetch(ticker, period, data_dir=DATA_DIR, private_dir=PRIVATE_DIR) -> Path
  raises SystemExit (non-zero, with a message) on unknown ticker/period or missing source_url
- app.backend.letters.main(argv: list[str]) -> None   (CLI: `fetch <ticker> <period>`)
- app.backend.validate.tracked_private_files(repo_root: Path = ROOT) -> list[str]
  (runs `git ls-files private` in repo_root); validate() adds an error for each path.
Errors for ceo_letters files must contain the text "ceo_letters".
"""

import copy
import importlib
import subprocess
from pathlib import Path

import pytest

from app.backend import validate as validate_module
from app.backend.storage import write_json
from app.backend.validate import LINE_ITEMS, validate

ROOT = Path(__file__).parent.parent
COMPANY = {
    "ticker": "A.ST",
    "name": "Alpha",
    "currency": "SEK",
    "report_currency": "SEK",
    "ir_url": "https://example.com/ir",
}
PERIODS = ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]


def url_for(period):
    return f"https://example.com/{period}.pdf"


def quarter(period, **overrides):
    q = {
        "period": period,
        "report_date": "2026-07-17",
        "source_url": url_for(period),
        "values": dict.fromkeys(LINE_ITEMS, 100.0),
    }
    q.update(overrides)
    return q


def write_financials(data_dir, quarters=None):
    quarters = quarters or [quarter(p) for p in PERIODS]
    write_json(data_dir / "companies.json", [COMPANY])
    write_json(
        data_dir / "financials" / "A.ST.json",
        {"ticker": "A.ST", "currency": "SEK", "quarters": quarters},
    )


def comparison(period="2026-Q2", compared_to="2026-Q1", **overrides):
    c = {
        "period": period,
        "compared_to": compared_to,
        "source_url": url_for(period),
        "tone": {"previous": "neutral", "current": "positive"},
        "dropped_topics": ["Valutan"],
        "new_topics": ["Nya order"],
        "changed_wording": [
            {"topic": "Efterfrågan", "before": "bra", "after": "mycket stark"}
        ],
        "summary": "Tonen är mer positiv och fokus flyttar till orderingången.",
    }
    c.update(overrides)
    return c


def trend(**overrides):
    t = {"from": "2026-Q2", "to": "2026-Q3", "summary": "Allt mer positiv ton."}
    t.update(overrides)
    return t


def letters_file(comparisons, **overrides):
    data = {"ticker": "A.ST", "comparisons": comparisons}
    data.update(overrides)
    return data


TWO = [comparison("2026-Q2", "2026-Q1"), comparison("2026-Q3", "2026-Q2")]


def letter_errors(tmp_path, data):
    write_financials(tmp_path)
    write_json(tmp_path / "ceo_letters" / "A.ST.json", data)
    return [e for e in validate(tmp_path) if "ceo_letters" in e]


# --- REQ-52-1: .gitignore ---


def test_req_52_1_private_folder_is_gitignored():
    """REQ-52-1"""
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert any(line.strip() in ("private/", "/private/", "/private") for line in lines)


# --- REQ-52-2 / REQ-52-3: fetch ---


@pytest.fixture
def letters():
    """Imported inside the fixture so a missing module fails each test, not the whole file."""
    return importlib.import_module("app.backend.letters")


@pytest.fixture
def downloads(monkeypatch, letters):
    """Mocks the download; returns the list of requested URLs."""
    calls = []

    def fake_download(url):
        calls.append(url)
        return b"%PDF-1.4 fake"

    monkeypatch.setattr(letters, "download", fake_download)
    return calls


def test_req_52_2_fetch_saves_the_pdf_under_private_reports(
    letters, tmp_path, downloads
):
    """REQ-52-2"""
    data_dir, private = tmp_path / "data", tmp_path / "private"
    write_financials(data_dir)

    path = letters.fetch("A.ST", "2026-Q2", data_dir=data_dir, private_dir=private)

    assert path == private / "reports" / "A.ST" / "2026-Q2.pdf"
    assert path.read_bytes() == b"%PDF-1.4 fake"
    assert downloads == [url_for("2026-Q2")]


def test_req_52_2_cli_fetch_runs_the_same_download(
    letters, tmp_path, downloads, monkeypatch
):
    """REQ-52-2"""
    data_dir, private = tmp_path / "data", tmp_path / "private"
    write_financials(data_dir)
    monkeypatch.setattr(letters, "DATA_DIR", data_dir)
    monkeypatch.setattr(letters, "PRIVATE_DIR", private)

    letters.main(["fetch", "A.ST", "2026-Q3"])

    assert (private / "reports" / "A.ST" / "2026-Q3.pdf").exists()
    assert downloads == [url_for("2026-Q3")]


def test_req_52_3_default_private_dir_is_the_gitignored_folder(
    letters,
):
    """REQ-52-3 / REQ-52-1: the default save location is <repo>/private"""
    assert Path(letters.PRIVATE_DIR) == ROOT / "private"


@pytest.mark.parametrize(
    ("ticker", "period"),
    [("X.ST", "2026-Q2"), ("A.ST", "2019-Q1")],
    ids=["unknown-ticker", "unknown-period"],
)
def test_req_52_3_unknown_ticker_or_period_exits_without_download(
    letters, tmp_path, downloads, ticker, period
):
    """REQ-52-3"""
    data_dir, private = tmp_path / "data", tmp_path / "private"
    write_financials(data_dir)

    with pytest.raises(SystemExit) as exc:
        letters.fetch(ticker, period, data_dir=data_dir, private_dir=private)

    assert exc.value.code not in (0, None)
    assert downloads == []
    assert not private.exists() or not list(private.rglob("*.pdf"))


@pytest.mark.parametrize("missing", ["absent", "empty"])
def test_req_52_3_missing_source_url_exits_without_download(
    letters, tmp_path, downloads, missing
):
    """REQ-52-3"""
    data_dir, private = tmp_path / "data", tmp_path / "private"
    q = quarter("2026-Q2")
    if missing == "absent":
        del q["source_url"]
    else:
        q["source_url"] = ""
    write_financials(data_dir, [quarter("2026-Q1"), q])

    with pytest.raises(SystemExit) as exc:
        letters.fetch("A.ST", "2026-Q2", data_dir=data_dir, private_dir=private)

    assert exc.value.code not in (0, None)
    assert downloads == []
    assert not private.exists() or not list(private.rglob("*.pdf"))


# --- REQ-52-4: valid files, enums and limits ---


def test_req_52_4_valid_file_with_trend_passes(tmp_path):
    """REQ-52-4"""
    write_financials(tmp_path)
    write_json(tmp_path / "ceo_letters" / "A.ST.json", letters_file(TWO, trend=trend()))
    assert validate(tmp_path) == []


def test_req_52_4_no_letters_file_passes(tmp_path):
    """REQ-52-4"""
    write_financials(tmp_path)
    assert validate(tmp_path) == []


def test_req_52_4_empty_comparisons_passes(tmp_path):
    """REQ-52-4 / REQ-52-10"""
    assert letter_errors(tmp_path, letters_file([])) == []


def test_req_52_4_ticker_must_match_the_file_name(tmp_path):
    """REQ-52-4"""
    data = letters_file([comparison()], ticker="B.ST")
    assert letter_errors(tmp_path, data)


@pytest.mark.parametrize("tone", ["negative", "neutral", "positive"])
def test_req_52_4_allowed_tones_pass(tmp_path, tone):
    """REQ-52-4"""
    c = comparison(tone={"previous": tone, "current": tone})
    assert letter_errors(tmp_path, letters_file([c])) == []


@pytest.mark.parametrize(
    "tone",
    [
        {"previous": "happy", "current": "positive"},
        {"previous": "neutral", "current": "Positive"},
        {"previous": "neutral"},
        "positive",
    ],
    ids=["bad-previous", "bad-current", "missing-current", "not-an-object"],
)
def test_req_52_4_bad_tone_is_an_error(tmp_path, tone):
    """REQ-52-4"""
    c = comparison(tone=tone)
    assert letter_errors(tmp_path, letters_file([c]))


@pytest.mark.parametrize("key", ["dropped_topics", "new_topics"])
def test_req_52_4_six_topics_of_40_chars_pass(tmp_path, key):
    """REQ-52-4"""
    c = comparison(**{key: ["x" * 40] * 6})
    assert letter_errors(tmp_path, letters_file([c])) == []


@pytest.mark.parametrize("key", ["dropped_topics", "new_topics"])
@pytest.mark.parametrize(
    "topics", [["t"] * 7, ["x" * 41], "not a list"], ids=["seven", "long", "string"]
)
def test_req_52_4_too_many_or_too_long_topics_is_an_error(tmp_path, key, topics):
    """REQ-52-4"""
    c = comparison(**{key: topics})
    assert letter_errors(tmp_path, letters_file([c]))


def test_req_52_4_six_wording_changes_pass(tmp_path):
    """REQ-52-4"""
    change = {"topic": "T", "before": "a b c d e f", "after": "a b c d e f"}
    c = comparison(changed_wording=[change] * 6)
    assert letter_errors(tmp_path, letters_file([c])) == []


def test_req_52_4_seven_wording_changes_is_an_error(tmp_path):
    """REQ-52-4"""
    change = {"topic": "T", "before": "bra", "after": "bättre"}
    c = comparison(changed_wording=[change] * 7)
    assert letter_errors(tmp_path, letters_file([c]))


@pytest.mark.parametrize("side", ["before", "after"])
def test_req_52_4_wording_over_six_words_is_an_error(tmp_path, side):
    """REQ-52-4"""
    change = {"topic": "T", "before": "bra", "after": "bättre"}
    change[side] = "ett två tre fyra fem sex sju"
    c = comparison(changed_wording=[change])
    assert letter_errors(tmp_path, letters_file([c]))


@pytest.mark.parametrize("missing", ["topic", "before", "after"])
def test_req_52_4_wording_entry_needs_topic_before_after(tmp_path, missing):
    """REQ-52-4"""
    change = {"topic": "T", "before": "bra", "after": "bättre"}
    del change[missing]
    c = comparison(changed_wording=[change])
    assert letter_errors(tmp_path, letters_file([c]))


def test_req_52_4_summary_limit_is_300_chars(tmp_path):
    """REQ-52-4"""
    ok = comparison(summary="x" * 300)
    assert letter_errors(tmp_path, letters_file([ok])) == []
    too_long = comparison(summary="x" * 301)
    assert letter_errors(tmp_path, letters_file([too_long]))


def test_req_52_4_summary_is_required(tmp_path):
    """REQ-52-4"""
    c = comparison()
    del c["summary"]
    assert letter_errors(tmp_path, letters_file([c]))


# --- REQ-52-5: periods exist and are ordered ---


@pytest.mark.parametrize("field", ["period", "compared_to"])
def test_req_52_5_period_not_in_financials_is_an_error(tmp_path, field):
    """REQ-52-5"""
    c = comparison(**{field: "2019-Q1"})
    c["source_url"] = url_for(c["period"])
    assert letter_errors(tmp_path, letters_file([c]))


@pytest.mark.parametrize(
    ("period", "compared_to"),
    [("2026-Q2", "2026-Q2"), ("2026-Q1", "2026-Q2")],
    ids=["same", "later"],
)
def test_req_52_5_compared_to_must_be_earlier(tmp_path, period, compared_to):
    """REQ-52-5"""
    c = comparison(period, compared_to)
    assert letter_errors(tmp_path, letters_file([c]))


def test_req_52_5_compared_to_across_a_year_boundary_passes(tmp_path):
    """REQ-52-5"""
    c = comparison("2026-Q1", "2025-Q4")
    assert letter_errors(tmp_path, letters_file([c])) == []


# --- REQ-52-6: source link ---


def test_req_52_6_source_url_must_match_the_stored_quarter(tmp_path):
    """REQ-52-6"""
    c = comparison(source_url="https://example.com/other.pdf")
    assert letter_errors(tmp_path, letters_file([c]))


# --- REQ-52-7 / 10 / 11: trend ---


def test_req_52_7_trend_from_not_a_comparison_period_is_an_error(tmp_path):
    """REQ-52-7: 2026-Q1 is in the financials but is not a comparison's period"""
    t = trend(**{"from": "2026-Q1"})
    assert letter_errors(tmp_path, letters_file(TWO, trend=t))


def test_req_52_7_trend_to_not_a_comparison_period_is_an_error(tmp_path):
    """REQ-52-7"""
    t = trend(to="2025-Q4")
    assert letter_errors(tmp_path, letters_file(TWO, trend=t))


@pytest.mark.parametrize(
    ("from_", "to"),
    [("2026-Q3", "2026-Q2"), ("2026-Q2", "2026-Q2")],
    ids=["reversed", "equal"],
)
def test_req_52_7_trend_from_must_be_strictly_before_to(tmp_path, from_, to):
    """REQ-52-7"""
    t = trend(**{"from": from_, "to": to})
    assert letter_errors(tmp_path, letters_file(TWO, trend=t))


def test_req_52_7_trend_summary_limit_is_300_chars(tmp_path):
    """REQ-52-7"""
    assert (
        letter_errors(tmp_path, letters_file(TWO, trend=trend(summary="x" * 300))) == []
    )
    assert letter_errors(tmp_path, letters_file(TWO, trend=trend(summary="x" * 301)))


@pytest.mark.parametrize("n", [0, 1])
def test_req_52_10_trend_is_optional_below_two_comparisons(tmp_path, n):
    """REQ-52-10"""
    assert letter_errors(tmp_path, letters_file(copy.deepcopy(TWO[:n]))) == []


def test_req_52_10_a_given_trend_is_still_checked_with_one_comparison(tmp_path):
    """REQ-52-10: optional, but not unchecked (from/to cannot be strictly ordered here)"""
    data = letters_file(
        copy.deepcopy(TWO[:1]), trend=trend(**{"from": "2026-Q2", "to": "2026-Q2"})
    )
    assert letter_errors(tmp_path, data)


def test_req_52_11_trend_is_required_from_two_comparisons(tmp_path):
    """REQ-52-11"""
    assert letter_errors(tmp_path, letters_file(TWO))


def test_req_52_11_three_comparisons_also_need_a_trend(tmp_path):
    """REQ-52-11"""
    three = [
        comparison("2026-Q1", "2025-Q4"),
        comparison("2026-Q2", "2026-Q1"),
        comparison("2026-Q3", "2026-Q2"),
    ]
    assert letter_errors(tmp_path, letters_file(three))
    assert letter_errors(tmp_path, letters_file(three, trend=trend())) == []


# --- REQ-52-8: tracked private files ---


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_req_52_8_tracked_private_file_is_reported_in_a_git_repo(tmp_path):
    """REQ-52-8"""
    git(tmp_path, "init", "-q")
    (tmp_path / "private" / "ceo-letters").mkdir(parents=True)
    (tmp_path / "private" / "ceo-letters" / "A.txt").write_text("secret")
    git(tmp_path, "add", "-f", "private/ceo-letters/A.txt")

    assert validate_module.tracked_private_files(tmp_path) == [
        "private/ceo-letters/A.txt"
    ]


def test_req_52_8_untracked_private_file_is_fine(tmp_path):
    """REQ-52-8"""
    git(tmp_path, "init", "-q")
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "A.txt").write_text("secret")
    (tmp_path / ".gitignore").write_text("private/\n")
    git(tmp_path, "add", ".gitignore")

    assert validate_module.tracked_private_files(tmp_path) == []


def test_req_52_8_validate_reports_each_tracked_private_path(tmp_path, monkeypatch):
    """REQ-52-8"""
    write_financials(tmp_path)
    monkeypatch.setattr(
        validate_module, "tracked_private_files", lambda *a, **k: ["private/a.txt"]
    )

    errors = validate(tmp_path)

    assert any("private/a.txt" in e for e in errors)


def test_req_52_8_validate_is_clean_when_nothing_private_is_tracked(
    tmp_path, monkeypatch
):
    """REQ-52-8"""
    write_financials(tmp_path)
    monkeypatch.setattr(validate_module, "tracked_private_files", lambda *a, **k: [])

    assert validate(tmp_path) == []


def test_req_52_8_nothing_under_private_is_tracked_in_this_repo():
    """REQ-52-8: the real repo is clean"""
    assert validate_module.tracked_private_files() == []


# --- review fixes: safe ticker, https only, malformed items ---


@pytest.mark.parametrize("ticker", ["../../x", "a.st", "A/B", ""])
def test_req_52_3_unsafe_ticker_exits_without_download(
    letters, tmp_path, downloads, ticker
):
    data_dir, private = tmp_path / "data", tmp_path / "private"
    write_financials(data_dir)

    with pytest.raises(SystemExit) as exc:
        letters.fetch(ticker, "2026-Q2", data_dir=data_dir, private_dir=private)

    assert exc.value.code not in (0, None)
    assert downloads == []


def test_req_52_3_non_https_source_url_exits_without_download(
    letters, tmp_path, downloads
):
    data_dir, private = tmp_path / "data", tmp_path / "private"
    q = quarter("2026-Q2", source_url="http://example.com/2026-Q2.pdf")
    write_financials(data_dir, [quarter("2026-Q1"), q])

    with pytest.raises(SystemExit) as exc:
        letters.fetch("A.ST", "2026-Q2", data_dir=data_dir, private_dir=private)

    assert exc.value.code not in (0, None)
    assert downloads == []


def test_req_52_3_download_rejects_a_redirect_to_http(letters, monkeypatch):
    import httpx

    def fake_get(url, **kwargs):
        return httpx.Response(
            200, content=b"x", request=httpx.Request("GET", "http://evil.test/a.pdf")
        )

    monkeypatch.setattr(letters.httpx, "get", fake_get)

    with pytest.raises(SystemExit):
        letters.download("https://example.com/a.pdf")


@pytest.mark.parametrize(
    "bad",
    [
        {"comparisons": ["not an object"]},
        {"comparisons": [comparison(changed_wording=["not an object"])]},
        {"comparisons": [comparison()], "trend": "not an object"},
    ],
    ids=["comparison-item", "wording-item", "trend"],
)
def test_req_52_4_malformed_items_give_an_error_not_a_crash(tmp_path, bad):
    data = letters_file([])
    data.update(bad)
    assert letter_errors(tmp_path, data)
