# Trinidad & Tobago News Scraper — Agent Notes

## Architecture

- Single Python package: `src/tt_news_scraper` (entrypoint: `main.py`)
- Two source backends wired through a unified wrapper in `merging_utils.py`:
  - Express: `fetch_express_headlines()` → TT Express search page with URL params
  - Guardian: `fetch_guardian_headlines()` → list pages + pagination via link-following
- Output schema is canonical across both sources: `["title", "url", "author", "date", "summary"]`

## Exact Commands (non-obvious details)

| Task | Command |
|------|---------|
| Install deps | `uv sync` or `pip install -e .` |
| Run Express default | `python -m tt_news_scraper --source express --limit 10` |
| Run Guardian with search | `python -m tt_news_scraper --source guardian --search-term "politics" --limit 20` |
| Output to file | `python -m tt_news_scraper --output news.csv` |

## Testing & Verification

- No test suite present; verification is manual via CSV output.
- Example HTMLs in `example_htmls/` for local parsing tests:
  - `single_express_article.html`, `single_guardian_article.html`
  - `guardian_default_search_page.html`, `guardian_example.html`

## Key Quirks & Gotchas

1. **Guardian pagination**: Uses iterative link-following (BFS) instead of URL construction to handle dynamic pagination; respects `max_pages` limit (~20 articles/page).
2. **Express search param**: Uses `&q=` for keyword search on TT Express.
3. **Polite delays**: Guardian scraping includes 1s sleep between requests and retry logic on HTTP errors.
4. **Date normalization**: Output dates are normalized to ISO format (`%Y-%m-%dT%H:%M:%S`) in `merging_utils.py`.
5. **Column mapping**: Guardian uses internal names (`headline`, `description`); renamed internally to canonical schema before return.

## Dependencies

- Python ≥3.12
- `beautifulsoup4`, `pandas`, `requests` (defined in `pyproject.toml`)
