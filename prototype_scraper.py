import urllib.request

import pandas as pd
from bs4 import BeautifulSoup


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

    # Fetch initial page to detect pagination structure
    try:
        req = urllib.request.Request(
            base_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode("utf-8")

        soup = BeautifulSoup(html, "html.parser")

        # Find the last page number in pagination bar
        last_page_num = 1
        for nav_elem in soup.find_all(class_=lambda x: x and "ag_page_navigation" in str(x)):
            for a in nav_elem.find_all("a", href=True):
                link_text = a.get_text(strip=True)
                if any(c.isdigit() for c in link_text) and len(link_text) > 1:
                    try:
                        page_num = int(link_text)
                        last_page_num = max(last_page_num, page_num)
                    except ValueError:
                        continue

        # Scrape initial page (page 1)
        all_articles.extend(_scrape_single_page(base_url, visited_urls))

        # Fetch remaining pages iteratively using for loop
        if last_page_num > 1 and max_pages >= last_page_num:
            for page in range(2, min(max_pages + 1, last_page_num + 1)):
                # Guardian pagination pattern: /search-6.14.0.3.XX.YYYY...
                # The 4th segment (index 3) is the page number
                parsed = urllib.parse.urlparse(base_url)
                path_parts = parsed.path.split("/")
                
                if len(path_parts) >= 5:
                    # Replace segment at index 3 with new page number
                    new_path = "/".join(path_parts[:4] + [str(page)] + path_parts[5:])
                    page_url = urllib.parse.urlunparse((
                        parsed.scheme, parsed.netloc, new_path,
                        parsed.params, parsed.query, parsed.fragment
                    ))
                else:
                    # Fallback for non-search URLs
                    page_url = f"{base_url}&page={page}"

                if page_url not in visited_urls:
                    all_articles.extend(_scrape_single_page(page_url, visited_urls))

    except Exception as e:
        print(f"Error during pagination scraping: {e}")

    return all_articles


def _scrape_single_page(url, visited_urls):
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
                    all_text[:headline_pos].strip()
                    if headline_pos > 0
                    else ""
                )
                description = " ".join(description.split())

                article = {
                    "url": link["href"],
                    "headline": headline,
                    "description": description[:200]
                    if len(description) > 200
                    else description,
                }

                # Only add if URL not already visited (prevents duplicates across pages)
                if article["url"] not in visited_urls:
                    articles.append(article)
                    visited_urls.add(article["url"])

    except Exception as e:
        print(f"Error scraping {url}: {e}")

    return articles


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        search_term = " ".join(sys.argv[1:])
        url = f"https://www.guardian.co.tt/search-6.14.0.3.40.dd56412694?search_content={search_term}"
    else:
        # Default to homepage list page for demo
        url = None

    print(f"Scraping from: {url or 'Homepage'}")
    df = scrape_guardian_news(url, max_pages=10)

    if len(df) > 0:
        print(f"\n✓ Scraped {len(df)} articles\n")
        print("First 5 rows:")
        for i, row in df.head(5).iterrows():
            print(f"{i + 1}. {row['headline']}")
            print(f"   URL: {row['url'][:70]}...")
            print(f"   Desc: {row['description'][:80]}...\n")

        # Show sample from later pages if available
        if len(df) > 15:
            print("-" * 60)
            print("Sample from page 3:")
            for i in range(15, min(20, len(df))):
                row = df.iloc[i]
                print(f"{i + 1}. {row['headline']}")

        # Save to CSV (optional)
        csv_path = (
            "tt_guardian_articles.csv" if url else "tt_guardian_homepage_articles.csv"
        )
        df.to_csv(csv_path, index=False)
        print(f"\nSaved to: {csv_path}")
    else:
        print("No articles found.")
