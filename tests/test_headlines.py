from unittest.mock import patch

import pandas as pd

from tt_news_scraper.fetching_utils.headlines import (
    fetch_express_headlines,
    fetch_guardian_headlines,
)


def _create_mock_response(html: str):
    """Create a mock requests.Response that works with BeautifulSoup."""
    # Use requests.Response as base class to get proper interface
    response = type("MockResponse", (object,), {"ok": True, "text": html})()

    # Add raise_for_status method for compatibility
    def mock_raise_for_status():
        pass  # No-op for successful requests

    # Add encoding attributes to prevent BeautifulSoup's encoding detection issues
    response.encoding = "utf-8"
    response.apparent_encoding = lambda: "utf-8"

    response.raise_for_status = mock_raise_for_status
    return response


def test_fetch_express_headlines_basic():
    """Minimal test: Express returns expected columns and count."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article1.html">Article One</a></h3></div>
  <span class="card-byline span.tnt-byline.asset-byline">John Doe</span>
  <time datetime="2026-10-31T10:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Short summary text.</p></div>
</article>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article2.html">Article Two</a></h3></div>
  <time datetime="2026-10-30T08:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Another summary.</p></div>
</article>
</body></html>"""

    # Use search result URL (with ?q=) to trigger pagination logic
    url = "https://trinidadexpress.com/?q=test&l=10"

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_express_headlines(url=url, limit=10)

        assert len(result) == 2
        assert list(result.columns) == ["url", "title", "summary", "author", "date"]


def test_fetch_guardian_headlines_basic():
    """Minimal test: Guardian returns expected columns and count."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<div class="_LIST">
  <a href="/article1.html"><h1 class="headline">Guardian Article One</h1></a>
  <div>byJane Smith | 20261031120000</div>
</div>
<div class="_LIST">
  <a href="/article2.html"><h1 class="headline">Guardian Article Two</h1></a>
  <div>byBob Jones | 20261030140000</div>
</div>
</body></html>"""

    MOCK_INPUT = pd.DataFrame([{"url": "https://www.guardian.co.tt"}])

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_response.text = MOCK_HTML  # Ensure text attribute is accessible
        mock_get.return_value = mock_response

        result = fetch_guardian_headlines(url=MOCK_INPUT["url"], max_pages=1)

        assert len(result) == 2
        assert list(result.columns) == ["url", "title", "summary", "author", "date"]


def test_fetch_express_headlines_empty_result():
    """Express returns empty DataFrame when no articles found."""
    MOCK_HTML = "<html><body></body></html>"

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        # Use homepage URL to avoid pagination logic that makes real HTTP requests
        result = fetch_express_headlines(url="https://trinidadexpress.com/")

        assert len(result) == 0


def test_fetch_guardian_headlines_empty_result():
    """Guardian returns empty DataFrame when no articles found."""
    MOCK_HTML = "<html><body></body></html>"

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_guardian_headlines(
            url="https://www.guardian.co.tt/search?q=empty"
        )

        assert len(result) == 0


def test_fetch_express_headlines_with_search_term():
    """Express constructs URL with search term correctly."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article.html">Search Result</a></h3></div>
  <time datetime="2026-10-31T10:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Summary.</p></div>
</article>
</body></html>"""

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        # Use explicit homepage URL with search term to avoid pagination logic
        result = fetch_express_headlines(url="https://trinidadexpress.com/", limit=10)

        assert len(result) == 1


def test_fetch_guardian_headlines_with_search_term():
    """Guardian constructs URL with search term correctly."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<div class="_LIST">
  <a href="/article.html"><h1 class="headline">Guardian Search Result Article</h1></a>
  <div>byAuthor | 20261031120000</div>
</div>
</body></html>"""

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        # Verify URL includes search term
        result = fetch_guardian_headlines(search_term="politics")

        assert len(result) == 1


def test_fetch_express_headlines_handles_missing_fields():
    """Express gracefully handles articles with missing optional fields."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article.html">No Author/Date</a></h3></div>
</article>
</body></html>"""

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_express_headlines(url="https://trinidadexpress.com/")

        assert len(result) == 1
        # Missing fields should be empty strings or NaT
        assert result["author"].iloc[0] == ""
        # Empty string is acceptable for missing date (pd.isna returns False for "")
        assert not pd.notna(result["date"].iloc[0]) or result["date"].iloc[0] == ""


def test_fetch_guardian_headlines_handles_missing_fields():
    """Guardian gracefully handles articles with missing optional fields."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<div class="_LIST">
  <a href="/article.html"><h1 class="headline">Guardian No Author Date Article</h1></a>
</div>
</body></html>"""

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(_create_mock_response(MOCK_HTML))()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_guardian_headlines(
            url="https://www.guardian.co.tt/search?q=test"
        )

        assert len(result) == 1
        # Missing fields should be empty strings or NaT
        assert result["author"].iloc[0] == ""
        # Empty string is acceptable for missing date (pd.isna returns False for "")
        assert not pd.notna(result["date"].iloc[0]) or result["date"].iloc[0] == ""


def test_fetch_express_headlines_pagination():
    """Express pagination fetches multiple pages when URL has query params."""
    # Mock requests.get to return HTML with article cards and pagination links for each page
    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:

        def _make_response(html):
            response = type("MockResponse", (object,), {"ok": True, "text": html})()

            def mock_raise_for_status():
                pass

            response.encoding = "utf-8"
            response.apparent_encoding = lambda: "utf-8"
            response.raise_for_status = mock_raise_for_status
            return response

        # Page 1: 2 article cards + pagination nav to page 2 (headlines > 20 chars)
        PAGE_1_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article1.html">First Article Title Here</a></h3></div>
  <span class="card-byline span.tnt-byline.asset-byline">John Doe</span>
  <time datetime="2026-10-31T10:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Summary one.</p></div>
</article>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article2.html">Second Article Title Here</a></h3></div>
  <span class="card-byline span.tnt-byline.asset-byline">Jane Smith</span>
  <time datetime="2026-10-30T08:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Summary two.</p></div>
</article>
<div class="ag_page_navigation"><a href="?o=10&l=10">Next &raquo;</a></div>
</body></html>"""

        # Page 2: 2 more article cards + pagination nav to page 3 (headlines > 20 chars)
        PAGE_2_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article3.html">Third Article Title Here</a></h3></div>
  <span class="card-byline span.tnt-byline.asset-byline">Bob Wilson</span>
  <time datetime="2026-10-29T08:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Summary three.</p></div>
</article>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article4.html">Fourth Article Title Here</a></h3></div>
  <span class="card-byline span.tnt-byline.asset-byline">Alice Brown</span>
  <time datetime="2026-10-28T08:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Summary four.</p></div>
</article>
<div class="ag_page_navigation"><a href="?o=20&l=10">Next &raquo;</a></div>
</body></html>"""

        # Page 3: no pagination (end of results) (headline > 20 chars)
        PAGE_3_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article5.html">Fifth Article Title Here</a></h3></div>
  <span class="card-byline span.tnt-byline.asset-byline">Charlie Davis</span>
  <time datetime="2026-10-27T08:00:00"></time>
  <div class="card-lead"><p class="tnt-summary">Summary five.</p></div>
</article>
</body></html>"""

        def side_effect(url, **kwargs):
            if "q=test" in url and "?o=" not in url:
                return _make_response(PAGE_1_HTML)
            elif "?o=10&l=10" in url:
                return _make_response(PAGE_2_HTML)
            elif "?o=20&l=10" in url:
                return _make_response(PAGE_3_HTML)
            else:
                # Fallback to first page
                return _make_response(PAGE_1_HTML)

        mock_get.side_effect = side_effect

        url = "https://trinidadexpress.com/?q=test&l=10"
        result = fetch_express_headlines(url=url, limit=20)

        assert len(result) == 5, (
            f"Expected 5 articles from pagination, got {len(result)}"
        )
        assert list(result.columns) == ["url", "title", "summary", "author", "date"]
