"""
Books to Scrape - Scraper
Sandbox site for scraping practice.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
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


def get_detail_cache_path(url: str) -> str:
    """Derive a cache filename from the book's product URL."""
    slug = url.split("/catalogue/")[-1].replace("/", "_")
    return os.path.join(CACHE_DIR, f"detail_{slug}")


def load_or_fetch_detail(url: str) -> bytes:
    """Return cached detail HTML or fetch from site with delay."""
    cache_path = get_detail_cache_path(url)

    if os.path.exists(cache_path):
        size = os.path.getsize(cache_path)
        print(f"CACHE HIT — {size:,} bytes from {cache_path}")
        with open(cache_path, "rb") as f:
            return f.read()

    time.sleep(REQUEST_DELAY)

    html = fetch_page(url)
    with open(cache_path, "wb") as f:
        f.write(html)
    print(f"FETCH — {len(html):,} bytes from {url}")
    return html


def extract_book_detail(html: bytes, product_url: str, source_page: str) -> dict:
    """Parse a single book detail page and return a raw record."""
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.select_one("div.product_main h1")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Price — first price inside the product area
    price_tag = soup.select_one("div.product_main p.price_color")
    price_text = price_tag.get_text(strip=True) if price_tag else None

    # Availability
    avail_tag = soup.select_one("div.product_main p.instock.availability")
    availability_text = avail_tag.get_text(strip=True) if avail_tag else None

    # Rating
    rating_tag = soup.select_one("div.product_main p.star-rating")
    rating_text = None
    if rating_tag:
        classes = rating_tag.get("class", [])
        for cls in classes:
            if cls != "star-rating":
                rating_text = cls.capitalize()
                break

    # Description
    desc_tag = soup.select_one("#product_description ~ p")
    description = desc_tag.get_text(strip=True) if desc_tag else None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)

    all_links: list[str] = []
    current_url = BASE_URL.format(1)

    for page_num in range(1, MAX_PAGES + 1):
        html = load_or_fetch(page_num)
        page_url = BASE_URL.format(page_num)
        book_links = extract_book_links(html, page_url)
        all_links.extend(book_links)

        next_url = get_next_page(html, page_url)
        if next_url:
            current_url = next_url
        else:
            break

    unique_links = list(dict.fromkeys(all_links))
    print(f"catalogue_pages={MAX_PAGES} discovered={len(all_links)} unique_urls={len(unique_links)}")

    # Stage 3 — fetch and parse every detail page
    detail_pages: list[dict] = []
    source_page = BASE_URL.format(1)
    for idx, url in enumerate(unique_links, 1):
        detail_html = load_or_fetch_detail(url)
        record = extract_book_detail(detail_html, url, source_page)
        detail_pages.append(record)
        if idx % 10 == 0:
            print(f"  … parsed {idx}/{len(unique_links)} detail pages")

    # Checkpoint — print one complete raw record
    print("\nCHECKPOINT — one complete raw record:")
    print(json.dumps(detail_pages[0], indent=2))
    print(f"\ndetail_pages={len(detail_pages)}")


if __name__ == "__main__":
    main()
