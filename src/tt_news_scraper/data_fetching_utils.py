import logging
import urllib.parse
import urllib.request
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


def scrape_guardian_news(
    url: Optional[str] = "https://www.guardian.co.tt/news-6.12.0.4f1749cb44",
    max_pages: int = 10,
) -> pd.DataFrame:
    """Scrape Trinidad Guardian news headlines and descriptions.

    Args:
        url: Optional URL to scrape. Defaults to the homepage list page.
              Supports both homepage lists and search result pages (e.g.,
              ?search_content=keyword).
        max_pages: Maximum number of pagination pages to fetch for search results.
                   Only applies when scraping search result URLs.

    Returns:
        pandas.DataFrame with columns: url, headline, description, author, date
    """
    # Fetch page with proper headers to avoid bot detection
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        html = response.read().decode("utf-8")

    soup = BeautifulSoup(html, "html.parser")

    articles = []

    # Find all list containers (contain article links)
    for container in soup.find_all(class_=lambda x: x and "_LIST" in str(x)):
        # Skip sponsored content
        if "sponsored-list" in str(container.get("class", [])):
            continue

        for link in container.find_all("a", href=True):
            # Extract headline from h1 inside the anchor
            headline_elem = link.find("h1", class_="headline")

            if not headline_elem:
                continue

            headline = headline_elem.get_text(strip=True)

            # Skip pagination links (short text, numbers/arrows only)
            link_text = link.get_text(strip=True)
            if (
                len(headline) < 20
                or headline.isdigit()
                or "→" in link_text
                or "»" in link_text
            ):
                continue

            # Get description from text before the headline (author/caption info)
            parent_div = link.find_parent("div")
            all_text = parent_div.get_text(strip=True) if parent_div else ""

            # Description is everything between container start and headline
            headline_pos = all_text.find(headline)
            description = all_text[:headline_pos].strip() if headline_pos > 0 else ""

            # Clean up description (remove extra whitespace, author names in brackets)
            description = " ".join(description.split())

            # Extract author (pattern: "byAuthorName" after headline)
            import re

            author_match = re.search(r"\bby(\S+)", all_text, re.IGNORECASE)
            author = author_match.group(1).strip() if author_match else ""

            # Extract timestamp (format: YYYYMMDDHHMMSS at end of metadata section)
            timestamp_match = re.search(r"(\d{14})\b", all_text)
            article_date = pd.NaT
            if timestamp_match and len(timestamp_match.group(1)) == 14:
                try:
                    dt = datetime.strptime(timestamp_match.group(1), "%Y%m%d%H%M%S")
                    article_date = dt.to_pydatetime()
                except ValueError:
                    pass

            articles.append(
                {
                    "url": link["href"],
                    "headline": headline,
                    "description": description[:200]
                    if len(description) > 200
                    else description,
                    "author": author,
                    "date": article_date,
                }
            )

    # If this is a search result page with pagination links, fetch all pages
    if url and soup.find(class_=lambda x: x and "ag_page_navigation" in str(x)):
        articles = scrape_all_guardian_pages(url, max_pages)

    # Convert URLs to absolute format for consistency
    base_domain = "https://www.guardian.co.tt"
    df = pd.DataFrame(articles).copy()
    if not df.empty:
        df["url"] = [
            base_domain + url if not url.startswith("http") else url
            for url in df["url"]
        ]

    return df


def scrape_all_guardian_pages(base_url: str, max_pages: int = 10) -> list[dict]:
    """Fetch all pagination pages for a search result URL.

    Uses iterative link-following instead of URL construction to handle
    Guardian's dynamic pagination structure correctly.

    Args:
        base_url: The original search result URL (e.g., with ?search_content=...)
        max_pages: Maximum number of pagination pages to fetch

    Returns:
        list of article dicts from all pages
    """
    all_articles = []
    visited_urls = set()
    page_queue = [base_url]  # Queue for iterative BFS-style traversal

    while page_queue and len(all_articles) < max_pages * 20:  # ~20 articles per page
        current_url = page_queue.pop(0)

        if current_url in visited_urls:
            continue
        visited_urls.add(current_url)

        try:
            req = urllib.request.Request(
                current_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )

            with urllib.request.urlopen(req, timeout=20) as response:
                html = response.read().decode("utf-8")

            soup = BeautifulSoup(html, "html.parser")

            # Scrape articles from current page and extend the list
            scraped_df = _scrape_single_guardian_page(current_url, visited_urls)
            all_articles.extend(scraped_df.to_dict(orient="records"))

            # Extract pagination links and add new pages to queue
            for nav_elem in soup.find_all(
                class_=lambda x: x and "ag_page_navigation" in str(x)
            ):
                for a in nav_elem.find_all("a", href=True):
                    link_text = a.get_text(strip=True)
                    if any(c.isdigit() for c in link_text) and len(link_text) > 1:
                        new_url = urllib.parse.urljoin(current_url, a["href"])
                        if new_url not in visited_urls:
                            page_queue.append(new_url)

        except Exception as e:
            logger.error(f"Error fetching {current_url}: {e}")

    # Convert URLs to absolute format for consistency
    base_domain = "https://www.guardian.co.tt"
    df = pd.DataFrame(all_articles).copy()
    if not df.empty:
        df["url"] = [
            base_domain + url if not url.startswith("http") else url
            for url in df["url"]
        ]

    return df


def _scrape_single_guardian_page(url: str, visited_urls: set[str]) -> pd.DataFrame:
    """Scrape articles from a single page.

    Args:
        url: The page URL to scrape
        visited_urls: Set of already-visited URLs (for deduplication)

    Returns:
        list of article dicts
    """
    articles = []

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode("utf-8")

        soup = BeautifulSoup(html, "html.parser")

        # Scrape articles from list containers
        for container in soup.find_all(class_=lambda x: x and "_LIST" in str(x)):
            if "sponsored-list" in str(container.get("class", [])):
                continue

            for link in container.find_all("a", href=True):
                headline_elem = link.find("h1", class_="headline")

                if not headline_elem:
                    continue

                headline = headline_elem.get_text(strip=True)
                link_text = link.get_text(strip=True)

                # Skip pagination links and short/numeric text
                if (
                    len(headline) < 20
                    or headline.isdigit()
                    or "→" in link_text
                    or "»" in link_text
                ):
                    continue

                parent_div = link.find_parent("div")
                all_text = parent_div.get_text(strip=True) if parent_div else ""
                headline_pos = all_text.find(headline)
                description = (
                    all_text[:headline_pos].strip() if headline_pos > 0 else ""
                )
                description = " ".join(description.split())

                # Extract author and date from metadata section
                import re

                parent_div = link.find_parent("div")
                all_text = parent_div.get_text(strip=True) if parent_div else ""

                author_match = re.search(r"\bby\s+(\S+)", all_text, re.IGNORECASE)
                author = author_match.group(1).strip() if author_match else ""

                timestamp_match = re.search(r"(\d{14})\b", all_text)
                article_date = pd.NaT
                if timestamp_match and len(timestamp_match.group(1)) == 14:
                    try:
                        dt = datetime.strptime(timestamp_match.group(1), "%Y%m%d%H%M%S")
                        article_date = dt.to_pydatetime()
                    except ValueError:
                        pass

                article = {
                    "url": link["href"],
                    "headline": headline,
                    "description": description[:200]
                    if len(description) > 200
                    else description,
                    "author": author,
                    "date": article_date,
                }

                # Only add if URL not already visited (prevents duplicates across pages)
                if article["url"] not in visited_urls:
                    articles.append(article)
                    visited_urls.add(article["url"])

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")

    # Convert URLs to absolute format for consistency
    base_domain = "https://www.guardian.co.tt"
    df = pd.DataFrame(articles).copy()
    if not df.empty:
        df["url"] = [
            base_domain + url if not url.startswith("http") else url
            for url in df["url"]
        ]

    return df
