"""
Books to Scrape - Scraper
Sandbox site for scraping practice.
"""

import os
import requests

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "catalogue-page-1.html")
URL = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/GdAyo19/FlyRank-AI)"
TIMEOUT = 10


def fetch_page(url: str) -> bytes:
    """Fetch a page from the site with a polite user-agent."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.content


def main() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)

    if os.path.exists(CACHE_FILE):
        size = os.path.getsize(CACHE_FILE)
        print(f"CACHE HIT — {size:,} bytes from {CACHE_FILE}")
    else:
        html = fetch_page(URL)
        with open(CACHE_FILE, "wb") as f:
            f.write(html)
        print(f"FETCH — {len(html):,} bytes from {URL}")


if __name__ == "__main__":
    main()
