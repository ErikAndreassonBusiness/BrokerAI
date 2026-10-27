"""List the missing quarters the report agent should fetch in its next run.

Usage: uv run python -m app.backend.todo --max 15
       uv run python -m app.backend.todo --refill --max 10  (stored quarters with missing line items)
"""

import argparse
from itertools import zip_longest
from pathlib import Path

from app.backend.storage import DATA_DIR, read_json
from app.backend.validate import LINE_ITEMS

HISTORY_START = "2021-Q3"


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


def refill(data_dir: Path = DATA_DIR, total: int = 10) -> list[str]:
    """Stored quarters that lack line items, newest first, with the saved report link."""
    queues = []
    for company in read_json(data_dir / "companies.json", []):
        ticker = company["ticker"]
        file = read_json(data_dir / "financials" / f"{ticker}.json", {"quarters": []})
        queue = []
        for quarter in reversed(file["quarters"]):
            keys = [k for k in LINE_ITEMS if k not in quarter.get("values", {})]
            if keys:
                queue.append(
                    f"{ticker} {quarter['period']} | {', '.join(keys)} | {quarter['source_url']}"
                )
        queues.append(queue)
    return _round_robin(queues, total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=15)
    parser.add_argument(
        "--refill", action="store_true", help="list quarters with missing line items"
    )
    args = parser.parse_args()
    items = refill(total=args.max) if args.refill else todo(total=args.max)
    print("\n".join(items))
