"""Trinidad & Tobago News Scraper - Fetches headlines from Trinidad Express and Guardian."""

import logging
from typing import Optional

import pandas as pd

from src.tt_news_scraper.data_fetching_utils import (
    fetch_express_headlines,
    fetch_guardian_headlines,
)

from src.tt_news_scraper.data_saving_utils import save_dataset

logger = logging.getLogger(__name__)

# Canonical column schema for unified output
CANONICAL_COLUMNS = ["title", "url", "author", "date", "summary"]


def _normalize_columns(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Rename columns to canonical schema based on source."""
    # Express column mapping (already uses canonical names from data_fetching_utils)
    if source == "express":
        return df.copy()

    # Guardian column mapping (already uses canonical names from _rename_guardian_columns)
    else:  # guardian
        return df.copy()


def _fetch_unified_dataset(
    mode: str, limit: Optional[int] = None, search_term: Optional[str] = None
) -> pd.DataFrame:
    """Unified entry point for fetching headlines from any supported source."""
    BASE_URL = "https://trinidadexpress.com/search/?t=article&sd=desc"

    if mode == "express":
        url = f"{BASE_URL}&l={limit or 10}&nsa=eedition"
        logger.info(f"Fetching headlines from: {url}")
        df = fetch_express_headlines(url)
    else:  # guardian
        logger.info(
            f"Fetching headlines from Guardian with search term: {search_term}"
        )
        df = fetch_guardian_headlines(
            url=None, search_term=search_term, max_pages=limit or 10
        )

    # Normalize date format to ISO string for consistency
    if not df["date"].empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")

    return _normalize_columns(df, source=mode)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Trinidad news headlines from Express or Guardian",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["express", "guardian"],
        default="express",
        help="Data source mode (default: express)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help="Number of articles/pages to fetch (default: 10)",
    )
    parser.add_argument(
        "--search-term",
        type=str,
        default=None,
        metavar="KEYWORD",
        help='Search keyword for Guardian mode (e.g., "politics")',
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tt_news_headlines.csv",
        metavar="FILE",
        help="Output CSV filename (default: tt_news_headlines.csv)",
    )

    args = parser.parse_args()

    # Fetch unified dataset using the wrapper function
    df = _fetch_unified_dataset(
        mode=args.mode,
        limit=args.limit,
        search_term=args.search_term,
    )

    # Export with unified schema
    save_dataset(df, args.output)

    if df.empty:
        logger.warning("No articles found or all entries were malformed.")
        return

    print("\n" + "=" * 80)
    print(f"Found {len(df)} article(s)")
    print("=" * 80)

    # Display as a nicely formatted table using canonical column names
    if len(df) > 0:
        print("\n")

        for idx, row in df.iterrows():
            title = str(row["title"])[:60] if pd.notna(row["title"]) else ""
            link = (
                str(row["url"])[:70] if pd.notna(row["url"]) and len(str(row["url"])) > 0 else ""
            )

            print(f"[{idx}] {title} | {link}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
