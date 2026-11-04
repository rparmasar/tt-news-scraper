import logging
import time
import urllib.parse
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

from tt_news_scraper.const import BASE_URLS, CANONICAL_COLUMNS
from tt_news_scraper.progress import FetchingProgress

logger = logging.getLogger(__name__)


def fetch_express_headlines(
    url: str | None = None, max_pages: int | None = None, search_term: str | None = None
) -> pd.DataFrame:
    """Fetch article headlines and metadata from TT Express page.

    Args:
        url: Optional Trinidad Express search URL to scrape. Defaults to homepage.
              Supports both homepage lists and search result URLs (e.g., ?q=keyword).
        max_pages: Maximum pagination pages to fetch for search results. Only applies when scraping
                search result URLs with pagination support.
        search_term: Search keyword for Express mode (used in URL construction if url not provided).

    Returns:
        DataFrame with columns: title, url, author, date, summary
    """
    # Construct URL if not provided (supports search_term for Express q-param)
    if url is None:
        base = BASE_URLS["express"]
        params = ["&nsa=eedition"]  # Required param for TT Express
        # Always use l=100 for Express (hardcoded per requirements)
        params.append("&l=100")
        if search_term:
            from urllib.parse import quote_plus

            params.append(f"&q={quote_plus(search_term)}")
        url = base + "".join(params)

    # Handle local file paths for testing (requests doesn't support file:// scheme)
    if url.startswith("file://"):
        with open(url, "r", encoding="utf-8") as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, "html.parser")
    else:
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

    # Apply max_pages if specified (respect Guardian's pagination-style fetching)
    effective_limit = min(len(article_cards), max_pages or len(article_cards))

    # Add progress tracking for batch fetching
    with FetchingProgress(
        description=f"Extracting Express articles ({effective_limit} cards)",
        total=effective_limit,
    ) as progress:
        for idx, card in enumerate(article_cards[:effective_limit], start=1):
            task_id = progress.add_task(f"[{idx}/{effective_limit}]...", total=1)

            headline_link = card.select_one(".card-headline h3 a")
            if not headline_link:
                progress.update(task_id, advance=1)
                continue

            title_tag: Tag | None = headline_link.find_parent("h3") or headline_link

            title = (title_tag.get_text(strip=True) or "").strip()
            if not title:
                progress.update(task_id, advance=1)
                continue  # Skip entries without a title

            # Extract the partial article link from href attribute
            partial_link = str(headline_link.get("href", "")).strip()

            # Only append if we have both title and a valid link
            if not partial_link:
                progress.update(task_id, advance=1)
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

            base_domain = "https://trinidadexpress.com"
            articles.append(
                {
                    "title": title,
                    "url": base_domain + partial_link,
                    "author": author,
                    "section_type": section_type,
                    "date": published_date,
                    "summary": article_summary,
                }
            )

        # Mark all tasks as complete
        if effective_limit > 0:
            for task_id in progress.tasks.values():
                progress.finish_task(task_id)

    # Only use pagination for search result URLs (those with query params), not homepage
    if url is not None and isinstance(url, str) and "?" in url:
        articles = scrape_all_express_pages(url, max_pages or 10)

    # Log skipped entries
    total_cards = len(article_cards)
    extracted_count = len(articles)
    skipped = max(0, total_cards - extracted_count)

    if skipped > 0:
        logger.info(f"Filtered out {skipped} non-article card(s)")

    # Create DataFrame and rename columns to canonical schema before returning
    df = pd.DataFrame(articles, columns=["url", "title", "summary", "author", "date"])
    return _rename_express_columns(df)


def scrape_all_express_pages(base_url: str, max_pages: int | None = 10) -> list[dict]:
    """Fetch all pagination pages for a search result URL.

    Uses iterative link-following instead of URL construction to handle
    Express's dynamic pagination structure correctly.

    Args:
        base_url: The original search result URL (e.g., with ?q=...)
        max_pages: Maximum number of pagination pages to fetch

    Returns:
        list of article dicts from all pages
    """

    all_articles = []
    visited_urls = set()
    page_queue = [base_url]  # Queue for iterative BFS-style traversal

    # Track pages fetched (including base URL)
    pages_fetched = 0

    total_expected = float("inf")  # No article cap
    with FetchingProgress(
        description=f"Scraping Express pagination (--max-pages {max_pages})",
        total=total_expected,
    ) as progress:
        while page_queue and len(all_articles) < total_expected:
            current_url = page_queue.pop(0)

            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            pages_fetched += 1

            # Enforce max_pages limit (counts all pages including base URL)
            if pages_fetched > max_pages and len(all_articles) < total_expected:
                logger.info(f"Reached max_pages limit ({max_pages})")
                break

            task_id = progress.add_task(f"{current_url[:50]}...", total=1)

            try:
                import time

                time.sleep(1)  # Polite delay between requests

                response = requests.get(
                    current_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        ),
                    },
                    timeout=30,
                )

                if not response.ok:
                    logger.error(
                        f"Failed to fetch Express page {current_url}: HTTP {response.status_code}"
                    )
                    progress.update(task_id, advance=1)
                    continue

                html = (response.text or "").strip()

                soup = BeautifulSoup(html, "html.parser")

                # Scrape articles from current page and extend the list
                scraped_df = _scrape_single_express_page(current_url, visited_urls)
                all_articles.extend(scraped_df.to_dict(orient="records"))

                # Extract pagination links - EXPRESS-SPECIFIC STRUCTURE:
                for nav_elem in soup.find_all(
                    class_=lambda x: x and "pagination" in str(x)
                ):
                    for a in nav_elem.find_all(
                        "a", href=True
                    ):  # Only follow links with href
                        link_text = a.get_text(strip=True)

                        # Detect pagination-style links (Next/Prev, page numbers, or SVG-only icons)
                        is_pagination = (
                            any(
                                word in link_text.lower()
                                for word in ["next", "prev", "previous"]
                            )
                            or len(link_text) > 2
                            and link_text[0].isdigit()
                        )

                        # Also detect icon-based pagination links (Font Awesome, SVG icons)
                        has_icon_class = False  # Initialize before try block
                        svg = None

                        if not is_pagination:
                            # Check for Font Awesome or similar icon classes in descendants
                            try:
                                # Convert to list first to avoid iterator issues with BeautifulSoup versions
                                nodes = list(a.descendants)
                                has_icon_class = any(
                                    "fas" in str(c).lower()
                                    or "tnt-chevron" in str(c).lower()
                                    for node in nodes
                                    if hasattr(node, "get")
                                    and (c := node.get("class", []))
                                )
                            except (
                                Exception
                            ) as e:  # Handle edge cases with BeautifulSoup versions
                                logger.debug(
                                    f"Error checking icon class for link {a['href']}: {e}"
                                )

                        # Check for SVG elements inside the link
                        if svg is None:
                            svg = a.find("svg")

                        # Set is_pagination if we found icon classes or SVG
                        if has_icon_class or svg:
                            is_pagination = True

                        if is_pagination:
                            new_url = urllib.parse.urljoin(current_url, a["href"])

                            # Normalize URL to use l=100 (reduces total HTTP requests)
                            normalized_url = normalize_express_pagination_url(new_url)

                            if normalized_url not in visited_urls:
                                page_queue.append(normalized_url)

                progress.update(task_id, advance=1)

            except Exception as e:
                logger.error(f"Error fetching {current_url}: {e}")
                progress.update(task_id, advance=1)

        # Mark all tasks as complete
        if page_queue or all_articles:
            for task_id in progress.tasks.values():
                progress.finish_task(task_id)

        return all_articles


def _scrape_single_express_page(url: str, visited_urls: set[str]) -> pd.DataFrame:
    """Scrape articles from a single Express page.

    Args:
        url: The page URL to scrape
        visited_urls: Set of already-visited URLs (for deduplication)

    Returns:
        list of article dicts
    """
    import time

    articles = []

    try:
        time.sleep(1)  # Polite delay between requests

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
            logger.error(
                f"Failed to fetch Express page {url}: HTTP {response.status_code}"
            )
            return pd.DataFrame(columns=["url", "title", "summary", "author", "date"])

        html = (response.text or "").strip()
        soup = BeautifulSoup(html, "html.parser")

        # Find all article cards first (each is a <article> element)
        article_cards = soup.select("article.tnt-asset-type-article")

        for card in article_cards:
            headline_link = card.select_one(".card-headline h3 a")
            if not headline_link:
                continue

            title_tag: Tag | None = headline_link.find_parent("h3") or headline_link

            title = (title_tag.get_text(strip=True) or "").strip()
            if not title:
                continue  # Skip entries without a title

            # Extract the partial article link from href attribute
            partial_link = str(headline_link.get("href", "")).strip()
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

            base_domain = "https://trinidadexpress.com"
            articles.append(
                {
                    "url": base_domain + partial_link,
                    "title": title,
                    "author": author,
                    "section_type": section_type,
                    "date": published_date,
                    "summary": article_summary,
                }
            )

    except Exception as e:
        logger.error(f"Error scraping Express page {url}: {e}")

    return pd.DataFrame(articles, columns=["url", "title", "summary", "author", "date"])


def _rename_express_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename Express-specific column names to canonical schema."""
    col_map = {
        "section_type": None,  # Drop unused column
    }
    df = df.drop(
        columns=[col for col in col_map if col_map[col] is not None], errors="ignore"
    )
    return _rename_guardian_columns(df)


def fetch_guardian_headlines(
    url: str | None = None,
    search_term: str | None = None,
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
    # Construct URL if search_content param is provided (Guardian-specific format)
    if search_term and url is None:
        url = f"{BASE_URLS['guardian']}/search-6.14.22d8842fe3"
        params = urllib.parse.urlencode({"search_content": search_term})
        url += "?" + params
    elif url is None:
        url = BASE_URLS["guardian"]

    # Fetch page with proper headers to avoid bot detection

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
        logger.warning(f"Got HTTP {response.status_code} for {url}, retrying in 2s...")

        time.sleep(2)
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)

    if not response.ok:
        logger.error(
            f"Failed to fetch Guardian page {url}: HTTP {response.status_code}"
        )
        raise requests.HTTPError(
            f"Guardian returned {response.status_code}", response=response
        )

    try:
        # Use response.text directly (requests handles decoding for us)
        html_content = (response.text or "").strip()
        if not html_content:
            logger.warning(f"Empty response from Guardian page {url}")
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

        soup = BeautifulSoup(html_content, "html.parser")
    except Exception as e:
        logger.error(f"Failed to parse HTML for {url}: {e}")
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    articles = []

    # Find all list containers - support both real Guardian structure and simpler formats
    def is_list_container(tag):
        if tag is None:
            return False
        classes = str(tag.get("class", []))
        return (
            "BT_SQLSTATEMENTS_978_LIST aghor agwrp agjcfe agaifs search-list" in classes
            or "_LIST" in classes
        )

    # Use CSS selector for better compatibility with BeautifulSoup's progress tracking
    container_selectors = [
        ".BT_SQLSTATEMENTS_978_LIST",
        "[class*='_LIST']",
    ]
    
    all_containers = []
    total = 0
    for sel in container_selectors:
        containers = soup.select(sel)
        # Filter by our pattern to avoid duplicates
        unique = [c for c in containers if is_list_container(c)]
        all_containers.extend(unique)
        total += len(unique)

    with FetchingProgress(
        description=f"Scraping Guardian page {url}",
        total=total,
    ) as progress:
        for container_idx, container in enumerate(all_containers, start=1):
            task_id = progress.add_task(f"[{container_idx}]...", total=1)

            # Skip sponsored content
            if "sponsored-list" in str(container.get("class", [])):
                progress.update(task_id, advance=1)
                continue

            for link in container.find_all("a", href=True):
                # Extract headline - Guardian uses direct text or h1 with headline class
                headline_elem = link.select_one("h1.headline") or link

                if not headline_elem:
                    progress.update(task_id, advance=1)
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
                    progress.update(task_id, advance=1)
                    continue

                # Extract author using specific class, fallback to empty string if missing
                author_elem = link.select_one("span.text-editor.string")
                author = author_elem.get_text(strip=True) if author_elem else ""

                # Extract date using multiple possible Guardian selectors and formats
                article_date = pd.NaT

                # Try primary selector first (Guardian's native date format)
                for selector in [
                    "span.textelement-publishing.date",
                    "time[datetime]",
                    "div.publish-date",
                ]:
                    date_elem = link.select_one(selector)
                    if date_elem and date_elem.get_text(strip=True):
                        try:
                            dt_str = date_elem.get_text(strip=True)

                            # Try Guardian's native format: "Sat Oct 31 2026"
                            parsed_dt = datetime.strptime(dt_str, "%a %b %d %Y")
                            article_date = parsed_dt.date()
                            break

                        except ValueError:
                            pass

                    elif date_elem and date_elem.has_attr("datetime"):
                        # Try ISO format from time tag (fallback)
                        try:
                            dt_str = date_elem["datetime"]
                            parsed_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                            article_date = parsed_dt.date()
                            break
                        except (ValueError, KeyError):
                            pass

                # If no date found via selectors, try meta tag parsing
                if pd.isna(article_date):
                    meta_tag = link.find("meta")
                    if meta_tag and meta_tag.has_attr("name"):
                        name = meta_tag["name"].lower()
                        content = meta_tag.get("content", "")

                        # Handle article:published_time or datePublished
                        if "date" in name or "publish" in name:
                            try:
                                # Try ISO format from meta content
                                parsed_dt = datetime.fromisoformat(
                                    content.replace("Z", "+00:00")
                                )
                                article_date = parsed_dt.date()
                            except (ValueError, AttributeError):
                                pass

                # If still no date, try to extract from link text as last resort
                if pd.isna(article_date) and link.get_text(strip=True):
                    # Look for patterns like "2026-10-31" or "Oct 31, 2026" in surrounding text
                    import re

                    text = link.get_text(strip=True)
                    match = re.search(r"\b(\d{4})\-(\d{2})\-(\d{2})\b", text)
                    if match:
                        try:
                            year, month, day = match.groups()
                            article_date = datetime(
                                int(year), int(month), int(day)
                            ).date()
                        except ValueError:
                            pass

                articles.append(
                    {
                        "url": link["href"],
                        "headline": headline,
                        "description": "",  # Will be fetched later for full content
                        "author": author,
                        "date": article_date,
                    }
                )

            progress.update(task_id, advance=1)

    # Only use pagination for search result URLs (those with query params), not homepage
    if url is not None and isinstance(url, str) and "?" in url:
        if soup.find(class_=lambda x: x and "ag_page_navigation" in str(x)):
            articles = scrape_all_guardian_pages(url, max_pages)

    # Convert URLs to absolute format for consistency
    base_domain = "https://www.guardian.co.tt"
    df = pd.DataFrame(articles).copy()
    if not df.empty:
        df["url"] = [
            base_domain + url if not url.startswith("http") else url
            for url in df["url"]
        ]

    # Rename columns to canonical schema before returning
    return _rename_guardian_columns(df)


def _rename_guardian_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename Guardian-specific column names to canonical schema."""
    col_map = {
        "headline": "title",
        "description": "summary",
    }
    df.rename(columns=col_map, inplace=True)
    return df


def normalize_express_pagination_url(url: str) -> str:
    """Normalize Express pagination URL to use l=100 parameter."""
    if not url.startswith("http"):
        # Relative URL - prepend base domain
        from tt_news_scraper.const import BASE_URLS

        url = BASE_URLS["express"] + url

    # Parse query params
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    parsed = urlparse(url)

    # Extract existing params
    params = parse_qs(parsed.query)

    # Force l=100 (reduces pagination overhead)
    if "l" in params:
        params["l"] = ["100"]
    else:
        params["l"] = ["100"]

    # Rebuild URL with normalized params
    new_query = urlencode(params, doseq=True)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


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

    total_expected = max_pages * 20  # ~20 articles per page
    with FetchingProgress(
        description=f"Scraping Guardian pagination ({max_pages} pages)",
        total=total_expected,
    ) as progress:
        while page_queue and len(all_articles) < total_expected:
            current_url = page_queue.pop(0)

            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            task_id = progress.add_task(f"{current_url[:50]}...", total=1)

            try:
                import time

                time.sleep(1)  # Polite delay between pagination requests

                response = requests.get(
                    current_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        ),
                    },
                    timeout=30,
                )

                if not response.ok:
                    logger.error(
                        f"Failed to fetch Guardian page {current_url}: HTTP {response.status_code}"
                    )
                    progress.update(task_id, advance=1)
                    continue

                html = (response.text or "").strip()

                soup = BeautifulSoup(html, "html.parser")

                # Scrape articles from current page and extend the list
                scraped_df = _scrape_single_guardian_page(current_url, visited_urls)
                all_articles.extend(scraped_df.to_dict(orient="records"))

                # Extract pagination links - look for Next/» arrow link
                next_link_elem = soup.select_one(
                    "div.ag_page_navigation_top a:contains('Next') or a[title*='Next']"
                )

                if not next_link_elem and "›" in str(soup):
                    # Fallback: find the › arrow link directly
                    for nav in soup.find_all(class_=lambda x: "ag_page_navigation_top" in str(x)):
                        arrow_link = nav.select_one("a:contains('Next') or a[title*='Next']")
                        if arrow_link and "›" in arrow_link.get_text(strip=True):
                            next_link_elem = arrow_link
                            break

                if not next_link_elem:
                    # Last resort: find any link with › character that's not a page number
                    for nav in soup.find_all(class_=lambda x: "ag_page_navigation_top" in str(x)):
                        for a in nav.find_all("a", href=True):
                            text = a.get_text(strip=True)
                            if "›" in text and len(text.strip()) <= 3:
                                next_link_elem = a
                                break
                        if next_link_elem:
                            break

                if next_link_elem:
                    new_url = urllib.parse.urljoin(current_url, next_link_elem["href"])
                    if new_url not in visited_urls:
                        page_queue.append(new_url)

                progress.update(task_id, advance=1)

            except Exception as e:
                logger.error(f"Error fetching {current_url}: {e}")
                progress.update(task_id, advance=1)

        # Mark all tasks as complete
        if page_queue or all_articles:
            for task_id in progress.tasks.values():
                progress.finish_task(task_id)

        return all_articles


def _scrape_single_guardian_page(url: str, visited_urls: set[str]) -> pd.DataFrame:
    """Fetch and extract articles from a single Guardian page.

    Args:
        url: The page URL to scrape
        visited_urls: Set of already-visited URLs (for deduplication)

    Returns:
        DataFrame with columns: url, headline, description, author, date
    """
    try:
        import time

        time.sleep(1)  # Polite delay between requests

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
            logger.error(
                f"Failed to fetch Guardian page {url}: HTTP {response.status_code}"
            )
            return pd.DataFrame(columns=["url", "headline", "description", "author", "date"])
        html = (response.text or "").strip()

        soup = BeautifulSoup(html, "html.parser")

        # Extract articles using centralized helper
        articles = _extract_guardian_articles_from_html(soup, url)

    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return pd.DataFrame(columns=["url", "headline", "description", "author", "date"])

    # Convert to DataFrame and normalize URLs
    df = pd.DataFrame(articles).copy()
    if not df.empty:
        base_domain = "https://www.guardian.co.tt"
        df["url"] = [
            base_domain + url if not url.startswith("http") else url
            for url in df["url"]
        ]

    return _rename_guardian_columns(df)



def _extract_guardian_articles_from_html(soup, url: str) -> list[dict]:
    """Extract article data from Guardian HTML using centralized selectors.

    Args:
        soup: BeautifulSoup parsed HTML object
        url: The page URL (for logging/debugging)

    Returns:
        List of dicts with keys: url, headline, description, author, date
    """
    articles = []

    # Main container for search results per requirements
    main_container = soup.select_one(
        'div.BT_SQLSTATEMENTS_978_LIST.aghor.agwrp.agjcfe.agaifs.search-list'
    )

    if not main_container:
        logger.debug(f"No main container found in {url}")
        return articles

    # Extract all article links from the main container
    for link in main_container.find_all('a', href=True):
        headline_elem = link.select_one('h1.headline')

        if not headline_elem:
            continue

        headline = headline_elem.get_text(strip=True)

        # Skip pagination links and short/numeric text
        link_text = link.get_text(strip=True)
        if len(headline) < 20 or headline.isdigit() or '→' in link_text or '»' in link_text:
            continue

        # Extract author using specific class per requirements
        author_elem = link.select_one('span.text-editor.string')
        author = author_elem.get_text(strip=True) if author_elem else ''

        # Extract date using Guardian TT's actual HTML structure
        article_date = pd.NaT

        # Try primary selector: span with both classes
        for selector in ['span.textelement-publishing.date', 'span.datetime']:
            date_elem = link.select_one(selector)
            if date_elem and date_elem.get_text(strip=True):
                try:
                    dt_str = date_elem.get_text(strip=True).strip()

                    # Guardian TT uses "Sat Oct 31 2026" format or YYYYMMDD
                    if len(dt_str) == 8 and dt_str.isdigit():
                        year, month, day = int(dt_str[0:4]), int(dt_str[4:6]), int(dt_str[6:8])
                        article_date = datetime(year, month, day).date()
                        break
                    else:
                        parsed_dt = datetime.strptime(dt_str, '%a %b %d %Y')
                        article_date = parsed_dt.date()
                        break

                except ValueError as e:
                    logger.debug(f"Date parse error for {dt_str}: {e}")

        # If no date found via selectors, try meta tag parsing
        if pd.isna(article_date):
            meta_tag = link.find('meta')
            if meta_tag and meta_tag.has_attr('name'):
                name = meta_tag['name'].lower()
                content = meta_tag.get('content', '')

                # Handle article:published_time or datePublished
                if 'date' in name or 'publish' in name:
                    try:
                        parsed_dt = datetime.fromisoformat(content.replace('Z', '+00:00'))
                        article_date = parsed_dt.date()
                    except (ValueError, AttributeError):
                        pass

        # If still no date, try to extract from link text as last resort
        if pd.isna(article_date) and link.get_text(strip=True):
            import re

            text = link.get_text(strip=True)
            match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
            if match:
                try:
                    year, month, day = match.groups()
                    article_date = datetime(int(year), int(month), int(day)).date()
                except ValueError:
                    pass

        # Build article dict with canonical column names
        article = {
            'url': link['href'],
            'headline': headline,
            'description': '',  # Will be fetched later for full content
            'author': author,
            'date': article_date,
        }

        articles.append(article)

    return articles


