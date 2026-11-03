"""Check the JSON files in data/ before they are committed.

Usage: uv run python -m app.backend.validate
"""

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from app.backend.storage import DATA_DIR, read_json

ROOT = Path(__file__).resolve().parents[2]

LINE_ITEMS = [
    "revenue",
    "gross_profit",
    "ebit",
    "depreciation",
    "net_income",
    "eps",
    "cash",
    "inventory",
    "current_assets",
    "total_assets",
    "short_term_debt",
    "long_term_debt",
    "current_liabilities",
    "total_equity",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
]
# Same quarter last year as printed in a quarter's own report; only for a currency change (see AGENT.md).
COMPARATIVE_ITEMS = ["revenue", "gross_profit", "ebit", "net_income", "eps"]
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
MAX_SUMMARY_SENTENCES = 4
MAX_SUMMARY_CHARS = 600
MAX_ITEM_CHARS = 120
MAX_SWOT_ITEMS = 4
SWOT_LISTS = ["strengths", "weaknesses", "opportunities", "threats"]
BREAKDOWN_DIMENSIONS = ("geography", "segment")
BREAKDOWN_NAME_MAX = 60
PERIOD = re.compile(r"^\d{4}-Q[1-4]$")
CURRENCY = re.compile(r"^[A-Z]{3}$")


def _is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_number_or_null(value) -> bool:
    return value is None or _is_number(value)


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


def _check_breakdown(at: str, quarter: dict) -> list[str]:
    """Optional revenue breakdown: geography/segment are null or a map of name -> number or null."""
    if "breakdown" not in quarter:
        return []
    breakdown = quarter["breakdown"]
    if not isinstance(breakdown, dict):
        return [f"{at}: breakdown must be an object"]
    errors = []
    unknown = sorted(set(breakdown) - set(BREAKDOWN_DIMENSIONS))
    if unknown:
        errors.append(
            f"{at}: unknown keys in breakdown: {', '.join(unknown)} "
            f"(allowed: {', '.join(BREAKDOWN_DIMENSIONS)})"
        )
    revenue = quarter.get("values", {}).get("revenue")
    for dimension in BREAKDOWN_DIMENSIONS:
        parts = breakdown.get(dimension)
        if parts is None:
            continue
        where = f"{at}: breakdown {dimension}"
        if not isinstance(parts, dict) or not parts:
            errors.append(f"{where} must be null or a non-empty object")
            continue
        bad = [
            n
            for n, v in parts.items()
            if len(n) > BREAKDOWN_NAME_MAX or not _is_number_or_null(v)
        ]
        if bad:
            errors.append(
                f"{where}: names max {BREAKDOWN_NAME_MAX} characters, amounts number or null"
            )
            continue
        amounts = list(parts.values())
        if None in amounts or not _is_number(revenue):
            continue
        tolerance = max(0.02 * abs(revenue), len(amounts))
        if abs(sum(amounts) - revenue) > tolerance:
            errors.append(
                f"{where} sums to {sum(amounts):g}, revenue is {revenue:g} "
                f"(allowed difference {tolerance:g})"
            )
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
        if "currency" in quarter and not CURRENCY.match(str(quarter["currency"])):
            errors.append(f"{at}: currency must be 3 capital letters, e.g. NOK")
        values = quarter.get("values", {})
        # A missing key is allowed: it hasn't been read yet and goes on the refill list (todo.py).
        unknown = sorted(set(values) - set(LINE_ITEMS))
        if unknown:
            errors.append(
                f"{at}: unknown keys in values: {', '.join(unknown)} "
                f"(allowed: {', '.join(LINE_ITEMS)})"
            )
        for item, value in values.items():
            if not _is_number_or_null(value):
                errors.append(f"{at}: {item} must be a number or null")
        errors += _check_breakdown(at, quarter)
        comparatives = quarter.get("comparatives", {})
        unknown = sorted(set(comparatives) - set(COMPARATIVE_ITEMS))
        if unknown:
            errors.append(
                f"{at}: unknown keys in comparatives: {', '.join(unknown)} "
                f"(allowed: {', '.join(COMPARATIVE_ITEMS)})"
            )
        for item, value in comparatives.items():
            if not _is_number_or_null(value):
                errors.append(f"{at}: comparatives {item} must be a number or null")
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


def _sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def _check_swot_item(at: str, item) -> list[str]:
    if not isinstance(item, dict):
        return [f"{at}: must be an object"]
    errors = []
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append(f"{at}: missing text")
    elif _sentences(text) > 1 or len(text) > MAX_ITEM_CHARS:
        errors.append(
            f"{at}: text must be one sentence of at most {MAX_ITEM_CHARS} characters"
        )
    sources = item.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{at}: needs at least one source")
    elif not all(str(s).startswith("https://") for s in sources):
        errors.append(f"{at}: sources must start with https://")
    return errors


def _check_summary(path: Path, summary_file) -> list[str]:
    name = f"summaries/{path.name}"
    if not isinstance(summary_file, dict):
        return [f"{name}: must be an object"]
    errors = []
    if "ticker" not in summary_file:
        errors.append(f"{name}: missing ticker")
    elif summary_file["ticker"] != path.stem:
        errors.append(f"{name}: ticker must match the file name")
    if "updated" not in summary_file:
        errors.append(f"{name}: missing updated")
    elif not _is_date(summary_file["updated"]):
        errors.append(f"{name}: updated must be YYYY-MM-DD")
    summary = summary_file.get("summary")
    if summary is None:
        errors.append(f"{name}: missing summary")
    elif (
        not isinstance(summary, str)
        or _sentences(summary) > MAX_SUMMARY_SENTENCES
        or len(summary) > MAX_SUMMARY_CHARS
    ):
        errors.append(
            f"{name}: summary must be at most {MAX_SUMMARY_SENTENCES} sentences "
            f"and {MAX_SUMMARY_CHARS} characters"
        )
    swot = summary_file.get("swot")
    if not isinstance(swot, dict):
        return errors + [f"{name}: missing swot"]
    for key in SWOT_LISTS:
        items = swot.get(key)
        if not isinstance(items, list):
            errors.append(f"{name}: swot {key} must be a list")
            continue
        if len(items) > MAX_SWOT_ITEMS:
            errors.append(f"{name}: swot {key} has more than {MAX_SWOT_ITEMS} items")
        for i, item in enumerate(items):
            errors += _check_swot_item(f"{name} swot {key}[{i}]", item)
    return errors


TONES = {"negative", "neutral", "positive"}
MAX_TOPICS = 6
MAX_TOPIC_CHARS = 40
MAX_WORDING_WORDS = 6
MAX_LETTER_SUMMARY_CHARS = 300


def tracked_private_files(repo_root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "private"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def _check_topics(at: str, key: str, topics) -> list[str]:
    if not isinstance(topics, list):
        return [f"{at}: {key} must be a list"]
    errors = []
    if len(topics) > MAX_TOPICS:
        errors.append(f"{at}: {key} has more than {MAX_TOPICS} topics")
    if any(not isinstance(t, str) or len(t) > MAX_TOPIC_CHARS for t in topics):
        errors.append(
            f"{at}: topics in {key} must be text of max {MAX_TOPIC_CHARS} chars"
        )
    return errors


def _check_wording(at: str, changes) -> list[str]:
    if not isinstance(changes, list):
        return [f"{at}: changed_wording must be a list"]
    errors = []
    if len(changes) > MAX_TOPICS:
        errors.append(f"{at}: changed_wording has more than {MAX_TOPICS} entries")
    for change in changes:
        if not isinstance(change, dict):
            errors.append(f"{at}: each changed_wording entry must be an object")
            continue
        for field in ("topic", "before", "after"):
            text = change.get(field)
            if not isinstance(text, str) or not text:
                errors.append(f"{at}: changed_wording needs text in {field}")
            elif field != "topic" and len(text.split()) > MAX_WORDING_WORDS:
                errors.append(
                    f"{at}: changed_wording {field} is over {MAX_WORDING_WORDS} words"
                )
    return errors


def _check_letter_summary(at: str, summary) -> list[str]:
    if not isinstance(summary, str) or not summary:
        return [f"{at}: summary must be text"]
    if len(summary) > MAX_LETTER_SUMMARY_CHARS:
        return [f"{at}: summary is over {MAX_LETTER_SUMMARY_CHARS} chars"]
    return []


def _check_comparison(at: str, comparison, quarters: dict) -> list[str]:
    errors = []
    period, compared_to = comparison.get("period"), comparison.get("compared_to")
    for field, value in (("period", period), ("compared_to", compared_to)):
        if value not in quarters:
            errors.append(f"{at}: {field} {value!r} not in financials")
    if period in quarters and compared_to in quarters and not compared_to < period:
        errors.append(f"{at}: compared_to must be earlier than period")
    if period in quarters and comparison.get("source_url") != quarters[period]:
        errors.append(f"{at}: source_url differs from the stored quarter")
    tone = comparison.get("tone")
    if not isinstance(tone, dict) or any(
        tone.get(k) not in TONES for k in ("previous", "current")
    ):
        errors.append(f"{at}: tone previous/current must be one of {sorted(TONES)}")
    errors += _check_topics(at, "dropped_topics", comparison.get("dropped_topics"))
    errors += _check_topics(at, "new_topics", comparison.get("new_topics"))
    errors += _check_wording(at, comparison.get("changed_wording"))
    return errors + _check_letter_summary(at, comparison.get("summary"))


def _check_trend(at: str, trend, periods: set) -> list[str]:
    if not isinstance(trend, dict):
        return [f"{at}: trend must be an object"]
    errors = []
    start, end = trend.get("from"), trend.get("to")
    for field, value in (("from", start), ("to", end)):
        if value not in periods:
            errors.append(f"{at}: trend {field} {value!r} is not a comparison period")
    if start in periods and end in periods and not start < end:
        errors.append(f"{at}: trend from must be strictly before to")
    return errors + _check_letter_summary(f"{at} trend", trend.get("summary"))


def _check_ceo_letters(path: Path, letters, financials) -> list[str]:
    name = f"ceo_letters/{path.name}"
    errors = []
    if letters.get("ticker") != path.stem:
        errors.append(f"{name}: ticker must match the file name")
    quarters = {
        q.get("period"): q.get("source_url")
        for q in (financials or {}).get("quarters", [])
    }
    comparisons = letters.get("comparisons")
    if not isinstance(comparisons, list):
        return errors + [f"{name}: comparisons must be a list"]
    for i, c in enumerate(comparisons):
        if not isinstance(c, dict):
            errors.append(f"{name}: comparison {i} must be an object")
            continue
        errors += _check_comparison(f"{name} {c.get('period')}", c, quarters)
    trend = letters.get("trend")
    if trend is not None:
        periods = {c.get("period") for c in comparisons if isinstance(c, dict)}
        errors += _check_trend(name, trend, periods)
    elif len(comparisons) >= 2:
        errors.append(f"{name}: trend is required from 2 comparisons")
    return errors


def _check_all_ceo_letters(data_dir: Path) -> list[str]:
    errors = []
    for path in sorted((data_dir / "ceo_letters").glob("*.json")):
        financials = read_json(data_dir / "financials" / path.name)
        errors += _check_ceo_letters(path, read_json(path), financials)
    return errors + [
        f"{p}: ceo_letters text must not be tracked by git (private/)"
        for p in tracked_private_files()
    ]


def validate(data_dir: Path = DATA_DIR) -> list[str]:
    """Returns a list of problems; empty means everything is valid."""
    errors, tickers = _check_companies(read_json(data_dir / "companies.json", []))
    quotes_file = read_json(data_dir / "quotes.json")
    if quotes_file is not None:
        errors += _check_quotes(quotes_file, tickers)
    for path in sorted((data_dir / "financials").glob("*.json")):
        errors += _check_financials(path, read_json(path), tickers)
    for path in sorted((data_dir / "summaries").glob("*.json")):
        errors += _check_summary(path, read_json(path))
    errors += _check_updates(read_json(data_dir / "updates.json", []), tickers)
    errors += _check_all_ceo_letters(data_dir)
    return errors


if __name__ == "__main__":
    problems = validate()
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)" if problems else "All data files are valid")
    sys.exit(1 if problems else 0)
