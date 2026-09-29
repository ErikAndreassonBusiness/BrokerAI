"""List the missing quarters the report agent should fetch in its next run.

Usage: uv run python -m app.backend.todo --max 15
"""

import argparse
from itertools import zip_longest
from pathlib import Path

from app.backend.storage import DATA_DIR, read_json

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


def todo(data_dir: Path = DATA_DIR, total: int = 15, per_company: int = 3) -> list[str]:
    """Round-robin over the companies so every company makes progress in every run."""
    missing = missing_quarters(data_dir)
    queues = [
        [f"{ticker} {period}" for period in periods[:per_company]]
        for ticker, periods in missing.items()
    ]
    rounds = zip_longest(*queues)
    return [item for round_ in rounds for item in round_ if item][:total]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=15)
    args = parser.parse_args()
    print("\n".join(todo(total=args.max)))
