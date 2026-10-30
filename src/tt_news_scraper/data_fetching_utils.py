import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def fetch_express_headlines(url: str) -> pd.DataFrame:
    """Fetch article headlines and metadata from TT Express page.

    Args:
        url: The Trinidad Express search URL to scrape.

    Returns:
        DataFrame with columns: title, partial_link_to_full_article, author,
        section_type, published_date, article_summary
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        raise

    soup = BeautifulSoup(response.text, "html.parser")
    articles = []

    # Find all article cards first (each is a <article> element)
    article_cards = soup.select("article.tnt-asset-type-article")

    for card in article_cards:
        headline_link = card.select_one(".card-headline h3 a")
        if not headline_link:
            continue

        title_tag: Optional[Tag] = headline_link.find_parent("h3") or headline_link

        title = (title_tag.get_text(strip=True) or "").strip()
        if not title:
            continue  # Skip entries without a title

        # Extract the partial article link from href attribute
        partial_link = str(headline_link.get("href", "")).strip()

        # Only append if we have both title and a valid link
        if not partial_link:
            continue  # Skip entries without a link

        # Extract author (blank if missing)
        author_elem = card.select_one(".card-byline span.tnt-byline.asset-byline")
        author = author_elem.get_text(strip=True) if author_elem else ""

        # Extract section type ("General" if missing, preserve exact text when present)
        section_elem = card.select_one(".card-label-section a.tnt-section-tag")
        section_type = section_elem.text.strip() if section_elem else "General"

        # Extract published_date (ISO format from datetime attribute)
        time_tag = card.select_one("time[datetime]")
        published_date = ""
        if time_tag and time_tag.has_attr("datetime"):
            try:
                dt_str = time_tag["datetime"]
                parsed_dt = datetime.fromisoformat(dt_str)
                published_date = parsed_dt.isoformat()
            except ValueError:
                pass  # Keep empty on parse failure

        # Extract article summary (full paragraph, not truncated)
        lead_p = card.select_one(".card-lead p.tnt-summary")
        article_summary = lead_p.get_text(strip=True) if lead_p else ""

        articles.append(
            {
                "title": title,
                "partial_link_to_full_article": partial_link,
                "author": author,
                "section_type": section_type,
                "published_date": published_date,
                "article_summary": article_summary,
            }
        )

    # Log skipped entries
    total_cards = len(article_cards)
    extracted_count = len(articles)
    skipped = max(0, total_cards - extracted_count)

    if skipped > 0:
        logger.info(f"Filtered out {skipped} non-article card(s)")

    return pd.DataFrame(
        articles,
        columns=[
            "title",
            "partial_link_to_full_article",
            "author",
            "section_type",
            "published_date",
            "article_summary",
        ],
    )
