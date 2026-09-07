"""Basic tests for the books scraper output."""
import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
BOOKS_FILE = os.path.join(OUTPUT_DIR, "books.json")


def test_books_file_exists():
    assert os.path.exists(BOOKS_FILE), f"{BOOKS_FILE} not found"


def test_books_count():
    with open(BOOKS_FILE) as f:
        books = json.load(f)
    assert len(books) == 60, f"Expected 60 books, got {len(books)}"


def test_all_prices_are_numbers():
    with open(BOOKS_FILE) as f:
        books = json.load(f)
    for book in books:
        assert isinstance(book["price_gbp"], float), f"price_gbp not a float: {book['price_gbp']}"


def test_all_urls_are_https():
    with open(BOOKS_FILE) as f:
        books = json.load(f)
    for book in books:
        assert book["product_url"].startswith("https://"), f"URL not HTTPS: {book['product_url']}"
