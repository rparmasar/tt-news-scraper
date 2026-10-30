import logging

import pandas as pd

from tt_news_scraper.fetching_utils.headlines import (
    fetch_express_headlines,
    fetch_guardian_headlines,
)

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


def fetch_unified_dataset(
    source: str, limit: int | None = None, search_term: str | None = None
) -> pd.DataFrame:
    """Unified entry point for fetching headlines from any supported source."""
    BASE_URL = "https://trinidadexpress.com/search/?t=article&sd=desc"

    if source == "express":
        url_params = [f"&l={limit or 10}", "&nsa=eedition"]
        if search_term:
            from urllib.parse import quote_plus

            url_params.append(f"&q={quote_plus(search_term)}")
        url = BASE_URL + "".join(url_params)
        logger.info(f"Fetching headlines from: {url}")
        df = fetch_express_headlines(url)
    else:  # guardian
        logger.info(f"Fetching headlines from Guardian with search term: {search_term}")
        df = fetch_guardian_headlines(
            url=None, search_term=search_term, max_pages=limit or 10
        )

    # Normalize date format to ISO string for consistency
    if not df["date"].empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    return _normalize_columns(df, source=source)
