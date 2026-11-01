# Trinidad & Tobago News Scraper — Agent Notes

## Architecture

- Single Python package: `src/tt_news_scraper`
- CLI entrypoint: root-level `main.py` (exposed as `ttns` command via pyproject.toml)
- Two source backends wired through unified wrapper in `src/tt_news_scraper/dataset_handling/merging_utils.py`:
  - Express: `fetch_express_headlines()` → TT Express search page with URL params
  - Guardian: `fetch_guardian_headlines()` → list pages + pagination via link-following
- Output schema (CSV columns): `url,title,summary,author,date` — normalized to ISO format dates

## Exact Commands (non-obvious details)

| Task | Command |
|------|---------|
| Install deps | `uv sync` or `pip install -e .` |
| Run CLI default | `ttns` or `python -m tt_news_scraper.main` |
| Express with search | `ttns --source express --search-term "politics" --limit 20` |
| Guardian with search | `ttns --source guardian --search-term "economy" --limit 15` |
| Output to file | `ttns --output news.csv` |
| Fetch full content (slow) | `ttns --content --limit 5` |
| Run tests | `uv run pytest tests/ -v` |
| Lint | `uv run ruff check src/ tests/` |

## Testing & Verification

- Tests in `tests/test_articles.py` and `tests/test_headlines.py`; use `responses` mocks for HTTP.
- No local HTML fixtures; all scraping is mocked via responses library.

## Key Quirks & Gotchas

1. **Guardian pagination**: Uses iterative link-following (BFS) instead of URL construction to handle dynamic pagination; respects `max_pages` limit (~20 articles/page).
2. **Express search param**: Uses `&q=` for keyword search on TT Express, plus required `&nsa=eedition`.
3. **Guardian retry-on-fail**: On HTTP errors, waits 2s and retries once before raising; includes 1s sleep between pagination requests.
4. **Date normalization**: Output dates are normalized to ISO format (`%Y-%m-%dT%H:%M:%S`) in `merging_utils.py`.
5. **Column mapping**: Guardian uses internal names (`headline`, `description`); renamed internally to canonical schema before return.
6. **Express columns**: Includes extra `section_type` column that is dropped during normalization; no equivalent on Guardian side.

## Dependencies

- Python ≥3.12
- Runtime: `beautifulsoup4`, `pandas`, `requests`
- Testing: `pytest`, `responses` (mock HTTP for unit tests)
