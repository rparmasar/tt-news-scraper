# Trinidad & Tobago News Scraper — Agent Notes

## Architecture

- Single Python package: `src/tt_news_scraper` (requires Python ≥3.12)
- CLI entrypoint: root-level `main.py` exposed as `ttns` command via pyproject.toml
- Two source backends wired through unified wrapper in `dataset_handling/merging_utils.py`:
  - Express: `fetch_express_headlines()` → search page with URL params (`?q=...`)
  - Guardian: `fetch_guardian_headlines()` → list pages + pagination via iterative link-following (BFS-style traversal)
- Output schema (CSV columns): `url`, `title`, `summary`, `author`, `date` — normalized to ISO format dates

## Exact Commands (non-obvious details)

| Task | Command | Notes |
|------|---------|-------|
| Install deps | `uv sync` or `pip install -e .` | uv recommended for faster installs |
| Run CLI default | `ttns --source express --max-pages 10` | Requires at least one non-default arg; shows help if none provided |
| Express with search | `ttns --source express --search-term "politics" --max-pages 20` | Uses `?q=` param on TT Express |
| Guardian with search | `ttns --source guardian --search-term "economy" --max-pages 15` | Constructs URL: `/search-6.14.22d8842fe3/?search_content=...` |
| Output to file | `ttns --output news.csv` | Default is `tt_news_headlines.csv` |
| Fetch full content (slow) | `ttns --content --max-pages 5` | ~3x fetch time per article; merges content via URL join |
| Run tests | `uv run pytest tests/ -v` | Uses `responses` mocks for HTTP; no local HTML fixtures |
| Lint | `uv run ruff check src/ tests/` | Ignores BLE001 (blind except), FA100, UP045 per pyproject.toml |

## Testing & Verification

- Tests in `tests/test_articles.py` and `tests/test_headlines.py`; use `responses` mocks for HTTP.
- No local HTML fixtures; all scraping is mocked via responses library.
- Mock response must implement: `.ok`, `.text`, `.raise_for_status()`, `.encoding="utf-8"`, `.apparent_encoding()`

## Key Quirks & Gotchas

1. **Pagination link detection**: Both Express and Guardian scrapers detect pagination links by text content (e.g., "Next »", "Previous «") in addition to numeric patterns. Uses iterative BFS-style traversal instead of URL construction for dynamic pages.
2. **Express search param**: Uses `&q=` for keyword search on TT Express, plus required `&nsa=eedition`.
3. **Guardian retry-on-fail**: On HTTP errors, waits 2s and retries once before raising; includes 1s sleep between pagination requests.
4. **Date normalization**: Output dates are normalized to ISO format (`%Y-%m-%dT%H:%M:%S`) in `dataset_handling/merging_utils.py` via `pd.to_datetime(...).dt.strftime()`.
5. **Column mapping**: Guardian uses internal names (`headline`, `description`); renamed internally to canonical schema before return. Express includes extra `section_type` column that is dropped during normalization.
6. **Guardian base URL fix**: Root domain `https://www.guardian.co.tt` (not `/news-...`) for proper search result page construction with query params.

## Dependencies

- Runtime: `beautifulsoup4`, `pandas`, `requests`
- Testing: `pytest`, `responses` (mock HTTP for unit tests)
- Dev: `ruff` (linting), `uv` (dependency management)
