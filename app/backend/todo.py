"""List the missing quarters the report agent should fetch in its next run.

Usage: uv run python -m app.backend.todo --max 15
       uv run python -m app.backend.todo --refill --max 10  (stored quarters with missing line items)
       uv run python -m app.backend.todo --summaries  (tickers whose AI summary is due this month)
"""

import argparse
from datetime import UTC, date, datetime
from itertools import zip_longest
from pathlib import Path

from app.backend.storage import DATA_DIR, read_json
from app.backend.validate import BREAKDOWN_DIMENSIONS, LINE_ITEMS

HISTORY_START = "2021-Q3"
BREAKDOWN_DEPTH = 8  # newest quarters per ticker asked for a breakdown
SUMMARY_CAP = None  # max summaries per run; None = no limit


def _parse(period: str) -> tuple[int, int]:
    year, quarter = period.split("-Q")
    return int(year), int(quarter)


def _periods(first: str, last: str) -> list[str]:
    """All quarters from first to last, inclusive, oldest first."""
    year, quarter = _parse(first)
    end = _parse(last)
    periods = []
    while (year, quarter) <= end:
        periods.append(f"{year}-Q{quarter}")
        year, quarter = (year + 1, 1) if quarter == 4 else (year, quarter + 1)
    return periods


def missing_quarters(data_dir: Path = DATA_DIR) -> dict[str, list[str]]:
    """Per ticker: quarters from HISTORY_START up to the latest stored quarter that are missing,
    newest first."""
    companies = read_json(data_dir / "companies.json", [])
    stored = {}
    for company in companies:
        ticker = company["ticker"]
        file = read_json(data_dir / "financials" / f"{ticker}.json", {"quarters": []})
        stored[ticker] = {q["period"] for q in file["quarters"]}

    all_stored = [p for periods in stored.values() for p in periods]
    if not all_stored:
        return {}
    latest = max(all_stored, key=_parse)
    wanted = _periods(HISTORY_START, latest)
    return {
        ticker: [p for p in reversed(wanted) if p not in periods]
        for ticker, periods in stored.items()
    }


def _round_robin(queues: list[list[str]], total: int) -> list[str]:
    """Round-robin over the companies so every company makes progress in every run."""
    rounds = zip_longest(*queues)
    return [item for round_ in rounds for item in round_ if item][:total]


def todo(data_dir: Path = DATA_DIR, total: int = 15, per_company: int = 3) -> list[str]:
    missing = missing_quarters(data_dir)
    queues = [
        [f"{ticker} {period}" for period in periods[:per_company]]
        for ticker, periods in missing.items()
    ]
    return _round_robin(queues, total)


def _missing_breakdown(quarter: dict) -> list[str]:
    """Pseudo keys for the breakdown dimensions that are absent (null means "not reported")."""
    stored = quarter.get("breakdown", {})
    return [f"breakdown.{d}" for d in BREAKDOWN_DIMENSIONS if d not in stored]


def refill(data_dir: Path = DATA_DIR, total: int = 10) -> list[str]:
    """Stored quarters that lack line items, newest first, with the saved report link."""
    queues = []
    for company in read_json(data_dir / "companies.json", []):
        ticker = company["ticker"]
        file = read_json(data_dir / "financials" / f"{ticker}.json", {"quarters": []})
        queue = []
        for age, quarter in enumerate(reversed(file["quarters"])):
            keys = [k for k in LINE_ITEMS if k not in quarter.get("values", {})]
            if age < BREAKDOWN_DEPTH:
                keys += _missing_breakdown(quarter)
            if keys:
                queue.append(
                    f"{ticker} {quarter['period']} | {', '.join(keys)} | {quarter['source_url']}"
                )
        queues.append(queue)
    return _round_robin(queues, total)


def summary_due(data_dir: Path, today: date) -> list[str]:
    """Tickers whose summary file is missing or last updated in an earlier calendar month."""
    due = []
    for company in read_json(data_dir / "companies.json", []):
        ticker = company["ticker"]
        updated = (read_json(data_dir / "summaries" / f"{ticker}.json") or {}).get(
            "updated"
        )
        if not updated or updated[:7] < today.isoformat()[:7]:
            due.append(ticker)
    return due[:SUMMARY_CAP]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=15)
    parser.add_argument(
        "--refill", action="store_true", help="list quarters with missing line items"
    )
    parser.add_argument(
        "--summaries", action="store_true", help="list tickers due a new summary"
    )
    args = parser.parse_args()
    if args.summaries:
        items = summary_due(DATA_DIR, datetime.now(UTC).date())
    else:
        items = refill(total=args.max) if args.refill else todo(total=args.max)
    print("\n".join(items))
