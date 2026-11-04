# guardian scraping requirements

NOTE: the scope here is ONLY for the `fetch_guardian_headlines()` function because `fetch_express_headlines()` uses a completely different page structure.

## context

the `fetch_guardian_headlines()` function takes in arguments for `url`, `search_term` and `max_pages` and will use these to fetch the headlines for various articles matching `search_term`.

if no search term is provided, it will fetch the content from the homepage defined by `https://www.guardian.co.tt/news-6.12.0.4f1749cb44`

HOWEVER, if a `search_term` is provided (this is the more common usecase) it should use a url like `f"https://www.guardian.co.tt/search-6.14.22d8842fe3/{search_content=search_term}"`

ultimately, we want to extract the `url`, `headline`, `author` and `date` for a given article.

## procedure to fetch articles (with search term)

1. fetch the HTML content from `f"https://www.guardian.co.tt/search-6.14.22d8842fe3/{search_content=search_term}"`

2. select our main container to process which is a div with `class=" BT_SQLSTATEMENTS_978_LIST aghor agwrp agjcfe agaifs search-list"` (exactly!)

3. for each `a` tag within our main container (from `2.`)
      1. the `url` is given by the `href` attribute of the `a` tag
      2. the `author` is given by the inner text from a `span` with `class="text-editor string"` (this is nested within the `a` tag)
      3. the `date` is given by the inner text from a `span` with `class="textelement-publishing date"` (also nested within the `a` tag)
      4. extract each of these

4. after processing all the `a` tags from 3., extract the `href` attribute from the `a` tag where the inner text is EXACTLY `"›"`

5. use the url from the `href` extracted from 4. to navigate to the next page.

6. repeat steps 1-5 for the new page until the number of pages processed is equal to `max_pages`.