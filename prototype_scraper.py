import sys

from src.tt_news_scraper.data_fetching_utils import scrape_guardian_news


if __name__ == "__main__":
    if len(sys.argv) > 1:
        search_term = " ".join(sys.argv[1:])
        url = f"https://www.guardian.co.tt/search-6.14.0.3.40.dd56412694?search_content={search_term}"
    else:
        # Default to homepage list page for demo
        url = None

    print(f"Scraping from: {url or 'Homepage'}")
    df = scrape_guardian_news(url, max_pages=10)

    if len(df) > 0:
        print(f"\n✓ Scraped {len(df)} articles\n")
        print("First 5 rows:")
        for i, row in df.head(5).iterrows():
            print(f"{i + 1}. {row['headline']}")
            print(f"   URL: {row['url'][:70]}...")
            print(f"   Desc: {row['description'][:80]}...\n")

        # Show sample from later pages if available
        if len(df) > 15:
            print("-" * 60)
            print("Sample from page 3:")
            for i in range(15, min(20, len(df))):
                row = df.iloc[i]
                print(f"{i + 1}. {row['headline']}")

        # Save to CSV (optional)
        csv_path = (
            "tt_guardian_articles.csv" if url else "tt_guardian_homepage_articles.csv"
        )
        df.to_csv(csv_path, index=False)
        print(f"\nSaved to: {csv_path}")
    else:
        print("No articles found.")
