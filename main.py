"""Trinidad & Tobago News Scraper - Fetches headlines from Trinidad Express and Guardian by source."""

import logging

import pandas as pd

from tt_news_scraper.dataset_handling.data_saving_utils import save_dataset
from tt_news_scraper.dataset_handling.merging_utils import fetch_unified_dataset

logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Trinidad news headlines from Express or Guardian by source",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=["express", "guardian"],
        default="express",
        help="Data source to fetch from (default: express)",
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
        help='Search keyword for Express (q param) or Guardian mode (e.g., "politics")',
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tt_news_headlines.csv",
        metavar="FILE",
        help="Output CSV filename (default: tt_news_headlines.csv)",
    )
    parser.add_argument(
        "--content",
        action="store_true",
        default=False,
        help="Fetch full article content in addition to headlines (slower, ~3x fetch time per article)",
    )

    args = parser.parse_args()

    # Fetch unified dataset using the wrapper function
    df = fetch_unified_dataset(
        source=args.source,
        limit=args.limit,
        search_term=args.search_term,
        fetch_content=args.content,
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
                str(row["url"])[:70]
                if pd.notna(row["url"]) and len(str(row["url"])) > 0
                else ""
            )

            print(f"[{idx}] {title} | {link}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
