"""
Books to Scrape - Scraper
Sandbox site for scraping practice.
"""

import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/GdAyo19/FlyRank-AI)"
TIMEOUT = 10
REQUEST_DELAY = 0.5
MAX_PAGES = 3


def fetch_page(url: str) -> bytes:
    """Fetch a page from the site with a polite user-agent."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.content


def get_cache_path(page_num: int) -> str:
    return os.path.join(CACHE_DIR, f"catalogue-page-{page_num}.html")


def load_or_fetch(page_num: int) -> bytes:
    """Return cached HTML or fetch from site with delay."""
    cache_path = get_cache_path(page_num)

    if os.path.exists(cache_path):
        size = os.path.getsize(cache_path)
        print(f"CACHE HIT — {size:,} bytes from {cache_path}")
        with open(cache_path, "rb") as f:
            return f.read()

    if page_num > 1:
        time.sleep(REQUEST_DELAY)

    url = BASE_URL.format(page_num)
    html = fetch_page(url)
    with open(cache_path, "wb") as f:
        f.write(html)
    print(f"FETCH — {len(html):,} bytes from {url}")
    return html


def extract_book_links(html: bytes, page_url: str) -> list[str]:
    """Extract all book links from a page and convert to absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("article.product_pod h3 a"):
        href = a.get("href")
        if href:
            links.append(urljoin(page_url, href))
    return links


def get_next_page(html: bytes, page_url: str) -> str | None:
    """Find the 'next' button link, or None if last page."""
    soup = BeautifulSoup(html, "html.parser")
    next_btn = soup.select_one("li.next a")
    if next_btn:
        return urljoin(page_url, next_btn.get("href"))
    return None


def main() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)

    all_links: list[str] = []
    current_url = BASE_URL.format(1)

    for page_num in range(1, MAX_PAGES + 1):
        html = load_or_fetch(page_num)
        book_links = extract_book_links(html, current_url)
        all_links.extend(book_links)

        next_url = get_next_page(html, current_url)
        if next_url:
            current_url = next_url
        else:
            break

    unique_links = list(dict.fromkeys(all_links))
    print(f"catalogue_pages={MAX_PAGES} discovered={len(all_links)} unique_urls={len(unique_links)}")


if __name__ == "__main__":
    main()
