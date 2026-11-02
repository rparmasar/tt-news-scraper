"""Shared configuration and constants for the news scraper."""

# Canonical column schema for unified output across all sources
CANONICAL_COLUMNS = ["title", "url", "author", "date", "summary"]

# Base URLs for each source
BASE_URLS = {
    "express": "https://trinidadexpress.com/search/?t=article&sd=desc",
    "guardian": "https://www.guardian.co.tt/news-6.12.0.4f1749cb44",
}

# Base domain for URL normalization
BASE_DOMAINS = {
    "express": "https://trinidadexpress.com",
    "guardian": "https://www.guardian.co.tt",
}

HEADLINE_REQUEST_TIMEOUT = 15
ARTICLE_REQUEST_TIMEOUT = 45
