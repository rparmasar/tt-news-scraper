import logging
from collections.abc import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Base domain for URL normalization
BASE_DOMAINS = {
    "express": "https://trinidadexpress.com",
    "guardian": "https://www.guardian.co.tt",
}


def fetch_express_article_content(urls: Iterable[str]) -> pd.DataFrame:
    """Fetch full article content from Trinidad Express URLs.

    Args:
        urls: Iterable of article URLs to fetch.

    Returns:
        DataFrame with columns: url, content
    """
    articles = []

    # Convert input to list to handle pandas Series/DataFrame correctly
    if hasattr(urls, "__iter__") and not isinstance(urls, str):
        url_list = [str(u).strip() for u in urls]
    else:
        url_list = [urls] if urls else []

    for url in url_list:
        if not url:
            continue

        logger.debug(f"Fetching Express article: {url}")

        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
                timeout=30,
            )

            if not response.ok:
                logger.warning(f"Failed to fetch Express article {url}: HTTP {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract article content from main article body
            # TT Express uses .tnt-article-content or similar selectors
            content_divs = soup.select(".tnt-article-content, .article-body, article p")
            if not content_divs:
                logger.debug(f"No content found in Express article {url}")
                continue

            # Join all paragraphs into a single content string
            content_parts = [div.get_text(strip=True) for div in content_divs]
            content = "\n".join(content_parts).strip()

            if not content:
                logger.debug(f"Empty content extracted from Express article {url}")
                continue

            articles.append({"url": url, "content": content})

        except requests.RequestException as e:
            logger.error(f"Request failed for Express article {url}: {e}")
        except Exception as e:
            logger.error(f"Error processing Express article {url}: {e}")

    if not articles:
        logger.warning("No articles were successfully fetched from Express.")

    return pd.DataFrame(articles, columns=["url", "content"])


def fetch_guardian_article_content(urls: Iterable[str]) -> pd.DataFrame:
    """Fetch full article content from Trinidad Guardian URLs.

    Args:
        urls: Iterable of article URLs to fetch.

    Returns:
        DataFrame with columns: url, content
    """
    articles = []

    # Convert input to list to handle pandas Series/DataFrame correctly
    if hasattr(urls, "__iter__") and not isinstance(urls, str):
        url_list = [str(u).strip() for u in urls]
    else:
        url_list = [urls] if urls else []

    for url in url_list:
        if not url:
            continue

        logger.debug(f"Fetching Guardian article: {url}")

        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
                timeout=30,
            )

            if not response.ok:
                logger.warning(f"Failed to fetch Guardian article {url}: HTTP {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract article content from main body
            # Guardian uses .article-body or similar selectors
            content_divs = soup.select(".article-body p, .story-content p, article p")
            if not content_divs:
                logger.debug(f"No content found in Guardian article {url}")
                continue

            # Join all paragraphs into a single content string
            content_parts = [div.get_text(strip=True) for div in content_divs]
            content = "\n".join(content_parts).strip()

            if not content:
                logger.debug(f"Empty content extracted from Guardian article {url}")
                continue

            articles.append({"url": url, "content": content})

        except requests.RequestException as e:
            logger.error(f"Request failed for Guardian article {url}: {e}")
        except Exception as e:
            logger.error(f"Error processing Guardian article {url}: {e}")

    if not articles:
        logger.warning("No articles were successfully fetched from Guardian.")

    return pd.DataFrame(articles, columns=["url", "content"])
