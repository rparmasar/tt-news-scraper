# Trinidad & Tobago News Scraper

A simple web scraper for fetching news headlines and descriptions from Trinidad Express.

## Usage

```bash
# Install dependencies
uv sync  # or: pip install -e .

# Scrape latest articles (default)
python -m tt_news_scraper

# Custom URL
python -m tt_news_scraper "https://trinidadexpress.com/search/?t=article&sd=desc&l=20&nsa=eedition"
```

## Output

Displays a formatted console table with:
- Article title (left-aligned)
- Description/snippet (right side)

Skipped/malformed entries are logged to stderr.
