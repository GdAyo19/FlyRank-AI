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
from pydantic import BaseModel, Field, HttpUrl, ValidationError

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/GdAyo19/FlyRank-AI)"
TIMEOUT = 10
REQUEST_DELAY = 0.5
MAX_PAGES = 3
MAX_RETRIES = 1


class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float = Field(ge=0)
    availability_text: str
    rating_text: str | None = None
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str


def fetch_page(url: str) -> bytes:
    """Fetch a page with polite user-agent. Retries on timeout/5xx, not on 404/403."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1 + MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            if response.status_code >= 500 and attempt < MAX_RETRIES:
                print(f"  RETRY — {response.status_code} from {url}, waiting 2s")
                time.sleep(2)
                continue
            response.raise_for_status()
            return response.content
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                print(f"  RETRY — timeout from {url}, waiting 2s")
                time.sleep(2)
                continue
            raise
    raise RuntimeError(f"Failed to fetch {url} after {1 + MAX_RETRIES} attempts")


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


def normalize_price(price_text: str) -> float:
    """Extract numeric value from price string like '£51.77'."""
    match = re.search(r"[\d.]+", price_text)
    if not match:
        raise ValueError(f"Cannot parse price: {price_text!r}")
    return float(match.group())


def extract_book_detail(html: bytes, product_url: str, source_page: str) -> dict:
    """Parse a single book detail page and return a raw record."""
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.select_one("div.product_main h1")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Price — first price inside the product area
    price_tag = soup.select_one("div.product_main p.price_color")
    price_text = price_tag.get_text(strip=True) if price_tag else None
    price_gbp = normalize_price(price_text) if price_text else None

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
        "price_gbp": price_gbp,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    start_time = datetime.now(timezone.utc)
    stats = {
        "start_time": start_time.isoformat(),
        "pages_fetched": 0,
        "cache_hits": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "failed_pages": 0,
    }

    # Stage 5 — collect book links from catalogue pages
    all_links: list[str] = []
    for page_num in range(1, MAX_PAGES + 1):
        page_url = BASE_URL.format(page_num)
        cache_path = get_cache_path(page_num)
        if os.path.exists(cache_path):
            stats["cache_hits"] += 1
        else:
            stats["pages_fetched"] += 1
        try:
            html = load_or_fetch(page_num)
            book_links = extract_book_links(html, page_url)
            all_links.extend(book_links)
        except Exception as e:
            stats["failed_pages"] += 1
            print(f"  FAILED — catalogue page {page_num}: {e}")
            continue

    unique_links = list(dict.fromkeys(all_links))
    # Inject one fake URL to prove failure handling works
    unique_links.append("https://books.toscrape.com/catalogue/fake-book-9999/index.html")
    print(f"catalogue_pages={MAX_PAGES} discovered={len(all_links)} unique_urls={len(unique_links)}")

    # Stage 5 — fetch and parse every detail page, survive failures
    raw_records: list[dict] = []
    source_page = BASE_URL.format(1)
    for idx, url in enumerate(unique_links, 1):
        cache_path = get_detail_cache_path(url)
        if os.path.exists(cache_path):
            stats["cache_hits"] += 1
        else:
            stats["pages_fetched"] += 1
        try:
            detail_html = load_or_fetch_detail(url)
            record = extract_book_detail(detail_html, url, source_page)
            raw_records.append(record)
        except Exception as e:
            stats["failed_pages"] += 1
            print(f"  FAILED — {url}: {e}")
            continue
        if idx % 10 == 0:
            print(f"  … parsed {idx}/{len(unique_links)} detail pages")

    # Stage 4 — deduplicate, validate, write output
    seen_urls: set[str] = set()
    books: list[dict] = []
    errors: list[dict] = []

    for record in raw_records:
        url = record["product_url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)

        try:
            validated = BookRecord(**record)
            books.append(validated.model_dump(mode="json"))
            stats["valid_records"] += 1
        except ValidationError as e:
            errors.append({"record": record, "error": e.errors()})
            stats["invalid_records"] += 1

    # Write output files (idempotent — overwrite on each run)
    books_path = os.path.join(OUTPUT_DIR, "books.json")
    with open(books_path, "w") as f:
        json.dump(books, f, indent=2)

    errors_path = os.path.join(OUTPUT_DIR, "errors.json")
    with open(errors_path, "w") as f:
        json.dump(errors, f, indent=2)

    # Stage 5 — write run report
    end_time = datetime.now(timezone.utc)
    duration_seconds = (end_time - start_time).total_seconds()
    run_report = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": round(duration_seconds, 2),
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": stats["valid_records"],
        "invalid_records": stats["invalid_records"],
        "failed_pages": stats["failed_pages"],
    }
    report_path = os.path.join(OUTPUT_DIR, "run-report.json")
    with open(report_path, "w") as f:
        json.dump(run_report, f, indent=2)

    print(f"\nCHECKPOINT — one complete raw record:")
    print(json.dumps(books[0], indent=2))
    print(f"\nbooks={len(books)} errors={len(errors)} failed_pages={stats['failed_pages']}")
    print(f"Output: {books_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
