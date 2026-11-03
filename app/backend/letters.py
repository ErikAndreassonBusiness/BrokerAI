"""Download a stored quarter's report to the gitignored private/ folder.

Usage: uv run python -m app.backend.letters fetch <ticker> <period>
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.backend.storage import DATA_DIR, read_json

PRIVATE_DIR = Path(__file__).resolve().parents[2] / "private"


def download(url: str) -> bytes:
    response = httpx.get(url, follow_redirects=True, timeout=60)
    response.raise_for_status()
    return response.content


def fetch(
    ticker: str, period: str, data_dir: Path = DATA_DIR, private_dir: Path = PRIVATE_DIR
) -> Path:
    financials = read_json(data_dir / "financials" / f"{ticker}.json")
    if financials is None:
        raise SystemExit(f"Unknown ticker {ticker}")
    quarter = next((q for q in financials["quarters"] if q["period"] == period), None)
    if quarter is None:
        raise SystemExit(f"{ticker} has no stored quarter {period}")
    url = quarter.get("source_url")
    if not url:
        raise SystemExit(f"{ticker} {period} has no source_url")

    suffix = Path(urlparse(url).path).suffix or ".pdf"
    path = private_dir / "reports" / ticker / f"{period}{suffix}"
    content = download(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def main(argv: list[str]) -> None:
    if len(argv) != 3 or argv[0] != "fetch":
        raise SystemExit("Usage: python -m app.backend.letters fetch <ticker> <period>")
    print(f"Saved {fetch(argv[1], argv[2], DATA_DIR, PRIVATE_DIR)}")


if __name__ == "__main__":
    main(sys.argv[1:])
