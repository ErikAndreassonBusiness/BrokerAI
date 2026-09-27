"""Fetch live key data for every stock and write data/quotes.json for GitHub Pages.

Usage: uv run python -m app.backend.export
"""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.backend import market
from app.backend.storage import DATA_DIR, read_json, write_json

log = logging.getLogger(__name__)


def export_quotes(data_dir: Path = DATA_DIR) -> bool:
    """Write quotes.json. A stock that fails keeps its previous values.

    Returns False (and leaves the file untouched) only if every stock failed.
    """
    companies = read_json(data_dir / "companies.json", [])
    path = data_dir / "quotes.json"
    old_quotes = read_json(path, {}).get("quotes", {})

    quotes = {}
    failed = 0
    for company in companies:
        ticker = company["ticker"]
        try:
            quotes[ticker] = market.fetch_quote(ticker)
        except Exception:
            failed += 1
            log.exception("Could not fetch %s, keeping the old values", ticker)
            if ticker in old_quotes:
                quotes[ticker] = old_quotes[ticker]

    if companies and failed == len(companies):
        log.error("Every stock failed; quotes.json not changed")
        return False

    updated_at = datetime.now(UTC).isoformat(timespec="seconds")
    write_json(path, {"updated_at": updated_at, "quotes": quotes})
    log.info("Wrote %s (%d ok, %d failed)", path, len(companies) - failed, failed)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(0 if export_quotes() else 1)
