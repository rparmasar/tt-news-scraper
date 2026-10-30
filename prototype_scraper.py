import urllib.request
from bs4 import BeautifulSoup
import pandas as pd


def scrape_guardian_news(url=None, max_pages=10):
    """Scrape Trinidad Guardian news headlines and descriptions.

    Args:
        url: Optional URL to scrape. If None, uses the homepage list page.
              Supports both homepage lists and search result pages (e.g.,
              ?search_content=keyword).
        max_pages: Maximum number of pagination pages to fetch for search results.
                   Only applies when scraping search result URLs.

    Returns:
        pandas.DataFrame with columns: url, headline, description
    """

    # Use provided URL or default homepage list page
    target_url = url if url else "https://www.guardian.co.tt/news-6.12.0.4f1749cb44"

    # Fetch page with proper headers to avoid bot detection
    req = urllib.request.Request(
        target_url,
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

            articles.append(
                {
                    "url": link["href"],
                    "headline": headline,
                    "description": description[:200]
                    if len(description) > 200
                    else description,
                }
            )

    # If this is a search result page with pagination links, fetch all pages
    if url and soup.find(class_=lambda x: x and "ag_page_navigation" in str(x)):
        articles = scrape_all_pages(url, max_pages)

    return pd.DataFrame(articles)


def scrape_all_pages(base_url, max_pages=10):
    """Fetch all pagination pages for a search result URL.

    Args:
        base_url: The original search result URL (e.g., with ?search_content=...)
        max_pages: Maximum number of pages to fetch

    Returns:
        list of article dicts from all pages
    """
    all_articles = []
    visited_urls = set()

    # Queue contains tuples of (page_url, page_number)
    queue = [(base_url, 0)]

    while queue and len(all_articles) < max_pages * 15:  # ~15 articles per page
        current_url, _ = queue.pop(0)

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

            # Find pagination links and add new pages to queue
            for nav_elem in soup.find_all(class_=lambda x: x and "ag_page_navigation" in str(x)):
                for a in nav_elem.find_all("a", href=True):
                    link_text = a.get_text(strip=True)
                    if any(c.isdigit() for c in link_text) and len(link_text) > 1:
                        new_url = urllib.parse.urljoin(current_url, a["href"])
                        if new_url not in visited_urls:
                            queue.append((new_url, int(link_text)))

            # Scrape articles from current page
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
                        all_text[:headline_pos].strip()
                        if headline_pos > 0
                        else ""
                    )
                    description = " ".join(description.split())

                    all_articles.append(
                        {
                            "url": link["href"],
                            "headline": headline,
                            "description": description[:200]
                            if len(description) > 200
                            else description,
                        }
                    )

        except Exception as e:
            print(f"Error fetching {current_url}: {e}")
            continue

    return all_articles


if __name__ == "__main__":
    # Example usage:
    # Homepage list page: scrape_guardian_news()
    # Search results: scrape_guardian_news("https://www.guardian.co.tt/search-6.14.0.3.40.dd56412694?search_content=longdenville")

    df = scrape_guardian_news(
        "https://www.guardian.co.tt/search-6.14.0.3.1.1478c24e3f?search_content=longdenville"
    )
    print(f"Scraped {len(df)} articles from: {df['url'].iloc[0]}")
    # print("\nFirst 5 rows:")
    # print(df.head())
    print(df)
