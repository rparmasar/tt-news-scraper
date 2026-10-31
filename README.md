# Trinidad & Tobago News Scraper

[![PyPI](https://img.shields.io/pypi/v/tt-news-scraper)](https://pypi.org/project/tt-news-scraper/)

A CLI tool for fetching news headlines and metadata from Trinidad Express and Guardian.

## Usage

```bash
# Install (direct PyPI install recommended)
pip install tt-news-scraper

# Default (Express, latest articles)
ttns

# Express with search query
ttns --source express --search-term "politics" --limit 20

# Guardian with search term
ttns --source guardian --search-term "economy" --limit 15

# Custom output file
ttns --output news_headlines.csv

# Fetch full article content (slower, ~3x fetch time per article)
ttns --content --limit 5
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--source {express,guardian}` | Data source to fetch from | express |
| `--limit [N]` | Number of articles/pages to fetch | 10 |
| `--search-term KEYWORD` | Search keyword for Express (q param) or Guardian | None |
| `--output FILE` | Output CSV filename | tt_news_headlines.csv |
| `--content` | Fetch full article content in addition to headlines | False |

## Output

- Console: Formatted table showing index, title, and URL per article
- File: Unified CSV with columns `url`, `title`, `summary`, `author`, `date` (and `content` if flag is specified)
