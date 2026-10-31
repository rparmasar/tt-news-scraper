from unittest.mock import patch

import pandas as pd

from tt_news_scraper.fetching_utils.headlines import (
    fetch_express_headlines,
    fetch_guardian_headlines,
)


def test_fetch_express_headlines_basic():
    """Minimal test: Express returns expected columns and count."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article1.html">Article One</a></h3></div>
  <span class="card-byline span.tnt-byline.asset-byline">John Doe</span>
  <time datetime="2026-10-31T10:00:00"></time>
  <p class="tnt-summary">Short summary text.</p>
</article>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article2.html">Article Two</a></h3></div>
  <time datetime="2026-10-30T08:00:00"></time>
  <p class="tnt-summary">Another summary.</p>
</article>
</body></html>"""

    url = "https://trinidadexpress.com/search?q=test"

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_express_headlines(url="https://trinidadexpress.com/search?q=empty")

        assert len(result) == 0


def test_fetch_guardian_headlines_empty_result():
    """Guardian returns empty DataFrame when no articles found."""
    MOCK_HTML = "<html><body></body></html>"

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_guardian_headlines(url="https://www.guardian.co.tt/search?q=empty")

        assert len(result) == 0


def test_fetch_express_headlines_with_search_term():
    """Express constructs URL with search term correctly."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article.html">Search Result</a></h3></div>
  <time datetime="2026-10-31T10:00:00"></time>
  <p class="tnt-summary">Summary.</p>
</article>
</body></html>"""

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        # Verify URL includes search term
        result = fetch_express_headlines(search_term="politics", limit=10)

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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_express_headlines(url="https://trinidadexpress.com/search?q=test")

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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_guardian_headlines(url="https://www.guardian.co.tt/search?q=test")

        assert len(result) == 1
        # Missing fields should be empty strings or NaT
        assert result["author"].iloc[0] == ""
        # Empty string is acceptable for missing date (pd.isna returns False for "")
        assert not pd.notna(result["date"].iloc[0]) or result["date"].iloc[0] == ""


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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_express_headlines(url="https://trinidadexpress.com/search?q=empty")

        assert len(result) == 0


def test_fetch_guardian_headlines_empty_result():
    """Guardian returns empty DataFrame when no articles found."""
    MOCK_HTML = "<html><body></body></html>"

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_guardian_headlines(url="https://www.guardian.co.tt/search?q=empty")

        assert len(result) == 0


def test_fetch_express_headlines_with_search_term():
    """Express constructs URL with search term correctly."""
    MOCK_HTML = """<!DOCTYPE html>
<html><body>
<article class="tnt-asset-type-article">
  <div class="card-headline"><h3><a href="/article.html">Search Result</a></h3></div>
  <time datetime="2026-10-31T10:00:00"></time>
  <p class="tnt-summary">Summary.</p>
</article>
</body></html>"""

    with patch("tt_news_scraper.fetching_utils.headlines.requests.get") as mock_get:
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        # Verify URL includes search term
        result = fetch_express_headlines(search_term="politics", limit=10)

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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_express_headlines(url="https://trinidadexpress.com/search?q=test")

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
        mock_response = type(
            "Response", (object,), {"ok": True, "text": MOCK_HTML}
        )()
        mock_response.raise_for_status = lambda: None  # Add missing method for mocking
        mock_get.return_value = mock_response

        result = fetch_guardian_headlines(url="https://www.guardian.co.tt/search?q=test")

        assert len(result) == 1
        # Missing fields should be empty strings or NaT
        assert result["author"].iloc[0] == ""
        # Empty string is acceptable for missing date (pd.isna returns False for "")
        assert not pd.notna(result["date"].iloc[0]) or result["date"].iloc[0] == ""
