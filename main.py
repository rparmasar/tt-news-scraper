"""Trinidad & Tobago News Scraper - Fetches headlines and article links from Trinidad Express."""

import logging

from src.tt_news_scraper.data_fetching_utils import fetch_express_headlines

logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Trinidad Express news headlines"
    )
    parser.add_argument(
        "url",
        nargs="?",
        default="https://trinidadexpress.com/search/?t=article&sd=desc&l=10&nsa=eedition",
        help="URL to scrape (default: latest 10 articles)",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info(f"Fetching headlines from: {args.url}")
    df = fetch_express_headlines(args.url)
    print(df)

    if df.empty:
        logger.warning("No articles found or all entries were malformed.")
        return

    print("\n" + "=" * 80)
    print(f"Found {len(df)} article(s)")
    print("=" * 80)

    # Display as a nicely formatted table
    if len(df) > 0:
        max_title_len = min(60, max(len(str(row[0])) for row in df.itertuples()))
        max_link_len = min(70, max(len(str(row[1])) for row in df.itertuples()))

        print("\n")
        for idx, (title, link, author, section_type, pub_date, summary) in enumerate(
            df.itertuples(index=False), 1
        ):
            title_display = str(title)[:max_title_len].ljust(max_title_len + 2)
            link_display = str(link)[:max_link_len] if link else ""

            print(f"[{idx}] {title_display} | {link_display}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
