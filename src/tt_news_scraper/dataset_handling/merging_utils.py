import logging

import pandas as pd

from tt_news_scraper.fetching_utils.articles import (
    fetch_express_article_content,
    fetch_guardian_article_content,
)
from tt_news_scraper.fetching_utils.headlines import (
    fetch_express_headlines,
    fetch_guardian_headlines,
)

logger = logging.getLogger(__name__)


def fetch_unified_dataset(
    source: str,
    max_pages: int | None = None,
    search_term: str | None = None,
    fetch_content: bool = False,
) -> pd.DataFrame:
    """Unified entry point for fetching headlines from any supported source."""
    if source == "express":
        logger.info(
            f"Fetching headlines from Express with max_pages={max_pages}, search_term={search_term}"
        )
        df = fetch_express_headlines(
            url=None,  # Let the function construct URL from params
            max_pages=max_pages or 10,
            search_term=search_term,
        )
        print(df)
    else:  # guardian
        logger.info(f"Fetching headlines from Guardian with search term: {search_term}")
        df = fetch_guardian_headlines(
            url=None, search_term=search_term, max_pages=max_pages or 10
        )

    # Normalize date format to ISO string for consistency
    if "date" in df.columns and not df["date"].empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    # Fetch full article content if requested
    if fetch_content and not df.empty:
        logger.info(f"Fetching full content for {len(df)} articles...")
        urls = df["url"].tolist()

        if source == "express":
            content_df = fetch_express_article_content(urls)
        else:  # guardian
            content_df = fetch_guardian_article_content(urls)

        # Merge content back to headlines on URL column
        if not content_df.empty:
            df = pd.merge(df, content_df, on="url", how="left")

    return df
