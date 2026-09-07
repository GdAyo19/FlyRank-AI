# Books to Scrape — Web Scraper

A polite web scraper that collects book metadata from [Books to Scrape](https://books.toscrape.com/), a sandbox site built for scraping practice.

## Target Classification

- **Site**: [books.toscrape.com](https://books.toscrape.com/)
- **Classification**: Sandbox — the site explicitly states "Books to Scrape We love being scraped!" and is designed for this purpose
- **Scope**: First 3 catalogue pages (60 books)
- **Data collected**: Title, price (raw + numeric), rating, availability, description, product URL
- **robots.txt**: Returns 404 — no robots file found

## Quick Start

```bash
git clone https://github.com/GdAyo19/FlyRank-AI.git
cd FlyRank-AI/scraper
pip install -r requirements.txt
python src/main.py
```

Output appears in `output/books.json` and `output/run-report.json`.

## Installation

This project uses **Python 3.10+** with pip (no conda):

```bash
pip install -r requirements.txt
```

Dependencies: `requests`, `beautifulsoup4`, `pydantic`

## Record Schema

Each book record in `output/books.json` follows this shape:

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "It's hard to imagine a world without A Light in the Attic...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-09-07T08:43:51.221889+00:00"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | yes | Book title from the page |
| `product_url` | string (URL) | yes | Canonical URL, used for deduplication |
| `price_text` | string | yes | Raw price as displayed (e.g. "£51.77") |
| `price_gbp` | float | yes | Numeric price extracted from price_text |
| `availability_text` | string | yes | Stock status as displayed |
| `rating_text` | string or null | no | One of: One, Two, Three, Four, Five |
| `description` | string or null | no | Some books have no description — null, never invented |
| `source_page` | string (URL) | yes | Which catalogue page this book appeared on |
| `fetched_at` | string (ISO 8601) | yes | When this record was scraped |

## Politeness Rules

The scraper follows these rules on every request:

| Rule | Implementation |
|------|----------------|
| **User-agent** | `FlyRankInternshipA9/1.0 (+https://github.com/GdAyo19/FlyRank-AI)` |
| **Delay** | 0.5 seconds between non-cached requests |
| **Timeout** | 10 seconds per request |
| **Cache** | HTML files cached to `cache/` — never re-fetch the same page |
| **Retries** | Timeout/5xx get one retry; 404/403 fail immediately |
| **Error handling** | Each page handled separately — one broken page is skipped, good records survive |

## Run Report

A sample `output/run-report.json` from a real run:

```json
{
  "start_time": "2026-09-07T08:43:51.145682+00:00",
  "end_time": "2026-09-07T08:43:52.756472+00:00",
  "duration_seconds": 1.61,
  "pages_fetched": 1,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```

This assignment needed no browser because the data is already in the HTML the server sends — a browser would only add cost.

## Limitations

The scraper only handles the first 3 catalogue pages (60 books). It does not follow links to other sites, handle JavaScript-rendered content, or support login-gated content. The `failed_pages` counter in the run report shows 1 because a deliberate fake URL was injected to prove failure handling works.

## Ethics Note

Only scrape sites that allow it. Use an official API when one exists — it is faster, more reliable, and respects the site's resources. Never bypass logins, paywalls, or blocks. Collect only what you need, identify yourself with a real user-agent, and leave the site as you found it.
