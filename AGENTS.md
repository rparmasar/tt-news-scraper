# Trinidad & Tobago News Scraper — Agent Notes

## Architecture

- Single Python package: `src/tt_news_scraper`
- Real CLI entrypoint: root-level `main.py`, not inside src/
- Two source backends wired through unified wrapper in `dataset_handling/merging_utils.py`:
  - Express: `fetch_express_headlines()` → TT Express search page with URL params
  - Guardian: `fetch_guardian_headlines()` → list pages + pagination via link-following
- Output schema (CSV columns): `url,title,summary,author,date` — normalized to ISO format dates

## Exact Commands (non-obvious details)

| Task | Command |
|------|---------|
| Install deps | `uv sync` or `pip install -e .` |
| Run Express default | `python main.py --source express --limit 10` |
| Run Guardian with search | `python main.py --source guardian --search-term "politics" --limit 20` |
| Output to file | `python main.py --output news.csv` |
| Test with local HTML (Express) | `python main.py --source express --url file://example_htmls/single_express_article.html` |
| Test with local HTML (Guardian) | `python main.py --source guardian --url file://example_htmls/guardian_example.html` |

## Testing & Verification

- Stub tests exist in `tests/test_articles.py` but don't exercise real scraping; use manual CSV verification.
- Example HTMLs in `example_htmls/` for local parsing tests:
  - `single_express_article.html`, `single_guardian_article.html`
  - `guardian_default_search_page.html`, `guardian_example.html`

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
