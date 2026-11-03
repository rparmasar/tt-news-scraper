# Pagination Navigation Guide

This document details how the scraper handles pagination for both Trinidad Express and Guardian sources.

## Overview

Both scrapers use **iterative link-following** instead of URL construction to handle dynamic pagination structures correctly. This approach:

- Follows actual `<a>` tags in the HTML rather than guessing URL patterns
- Handles edge cases like disabled links, icon-only navigation, and mixed content
- Uses BFS-style traversal with a queue to process pages sequentially
- Respects `max_pages` limit across all fetched pages (including base URL)

---

## Trinidad Express Pagination

### Structure

Express uses a Bootstrap-styled pagination container:

```html
<div class="pagination-container text-center">
    <ul class="pagination pagination-lg">
        <li class="prev disabled">
            <a rel="nofollow">
                <svg class="tnt-svg tnt-chevron-left" aria-hidden="true">...</svg>&nbsp;
            </a>
        </li>
        <li class="count"><a>1 of 1106</a></li>
        <li class="next">
            <a href="/search/?l=25&amp;q=crime&amp;o=25" rel="nofollow">
                &nbsp;<svg class="tnt-svg tnt-chevron-right">...</svg>
            </a>
        </li>
    </ul>
</div>
```

### Detection Logic

The scraper identifies pagination links using **three criteria**:

1. **Text-based keywords** (case-insensitive):
   - `"next"`, `"prev"`, `"previous"` in link text
   
2. **Numeric patterns**:
   - Link text starts with a digit and has length > 2 (e.g., "2", "10 of 50")

3. **Icon/SVG detection** (for Font Awesome or custom icons):
   - Checks descendant elements for classes containing `"fas"` or `"tnt-chevron"`
   - Detects `<svg>` elements inside the anchor tag
   - Handles both text+icon and icon-only links

### URL Normalization

Express uses a `l=` parameter to control items per page. The scraper normalizes this:

- **Default**: Forces `l=100` on all pagination URLs
- **Benefit**: Reduces number of pages needed (e.g., 1106 articles → ~12 pages instead of 45)
- **Implementation**: In `normalize_express_pagination_url()`:
  ```python
  if "l" in params:
      params["l"] = ["100"]
  else:
      params["l"] = ["100"]
  ```

### Example Flow

```
Base URL: https://trinidadexpress.com/?q=crime&l=10
  ↓ (fetch page 1)
Extracts link: /search/?o=25&q=crime
  ↓ (normalize with l=100)
Page 2: https://trinidadexpress.com/?o=25&q=crime&l=100
  ↓ (extract next link)
Page 3: https://trinidadexpress.com/?o=50&q=crime&l=100
  ... continues until max_pages reached or no more links found
```

---

## Guardian Pagination

### Structure

Guardian uses a simpler navigation structure with text-based links:

```html
<div class="ag_page_navigation">
    <a href="?o=25" rel="nofollow">&laquo; Previous</a>
    <span class="current">1</span>
    <a href="?o=50" rel="nofollow">2</a>
    ...
    <a href="?o=75" rel="nofollow">Next &raquo;</a>
</div>
```

### Detection Logic

Guardian pagination is detected by:

1. **Class-based selection**: Finds elements with class containing `"ag_page_navigation"`
2. **Text content matching**: Links contain "Previous", "Next", or numeric page indicators
3. **Link validation**: Only follows links that have valid `href` attributes

### Retry Behavior

Guardian scraping includes built-in resilience:

- On HTTP error (4xx/5xx): Waits 2 seconds, retries once before failing
- Between pagination requests: Sleeps 1 second to avoid rate limiting
- This is handled in the Guardian-specific fetching logic

---

## Common Patterns & Edge Cases Handled

### Disabled Links
```html
<li class="prev disabled">
    <a rel="nofollow">&laquo;</a>
</li>
```
The scraper skips links with `disabled` class or `rel="nofollow"` that don't point to new content.

### Icon-Only Navigation
```html
<a href="?o=25"><svg class="fas fa-chevron-right">...</svg></a>
```
Detected via SVG element presence and Font Awesome class patterns.

### Mixed Content
Pages may contain:
- Article cards (primary target)
- Pagination nav (followed for next page)
- Ads, modals, or other noise (ignored via CSS selectors)

### URL Parameter Variations
Both sources use different parameter names:
- Express: `l=` (items per page), `o=` (offset)
- Guardian: `o=` (offset only)

The scraper extracts these dynamically from the HTML rather than hardcoding patterns.

---

## Performance Notes

- **Express**: With `l=100`, ~12 pages for 1,200 articles vs ~45 with default `l=10`
- **Guardian**: No normalization needed; follows actual links from page HTML
- Both use iterative queue-based traversal to avoid recursion limits and handle broken links gracefully
