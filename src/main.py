import os
import re
import json
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
from typing import Optional
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, Field

# ---------------------------------------------------------
# 1. Configuration & Constants
# ---------------------------------------------------------
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = "cache"
OUTPUT_DIR = "output"
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/fahd-ashraf-farouk/week5_flyrank)"
}

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5
}

# ---------------------------------------------------------
# 2. Pydantic Schema
# ---------------------------------------------------------
class BookSchema(BaseModel):
    title: str
    product_url: HttpUrl
    price_gbp: float = Field(ge=0.0)
    in_stock: bool
    stock_count: int = Field(ge=0)
    rating_stars: int = Field(ge=1, le=5)
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str

# ---------------------------------------------------------
# 3. Helper & Extraction Functions
# ---------------------------------------------------------
def fetch_page(url: str, cache_filename: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    time.sleep(0.5)

    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url}, status code: {response.status_code}")

    html_content = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_content

def discover_books(max_pages: int = 3) -> list:
    current_url = BASE_URL
    discovered_items = []
    pages_crawled = 0

    while current_url and pages_crawled < max_pages:
        pages_crawled += 1
        cache_file = f"catalogue-page-{pages_crawled}.html"
        
        html = fetch_page(current_url, cache_file)
        soup = BeautifulSoup(html, "html.parser")

        articles = soup.find_all("article", class_="product_pod")
        for article in articles:
            rel_link = article.h3.a["href"]
            abs_link = urljoin(current_url, rel_link)
            discovered_items.append({
                "product_url": abs_link,
                "source_page": current_url
            })

        next_button = soup.find("li", class_="next")
        if next_button and next_button.a:
            next_rel_link = next_button.a["href"]
            current_url = urljoin(current_url, next_rel_link)
        else:
            current_url = None

    return discovered_items

def normalize_and_validate(raw_data: dict) -> BookSchema:
    # 1. Price Normalization (£51.77 -> 51.77)
    price_match = re.search(r"[\d.]+", raw_data["price_text"])
    price_gbp = float(price_match.group()) if price_match else 0.0

    # 2. Availability Normalization
    in_stock = "In stock" in raw_data["availability_text"]
    stock_match = re.search(r"\d+", raw_data["availability_text"])
    stock_count = int(stock_match.group()) if stock_match else 0

    # 3. Rating Normalization ("Three" -> 3)
    rating_stars = RATING_MAP.get(raw_data["rating_text"], 0)

    # 4. Description Cleaning
    desc = raw_data["description"].strip() if raw_data["description"] else None

    # Construct and validate using Pydantic
    validated_book = BookSchema(
        title=raw_data["title"],
        product_url=raw_data["product_url"],
        price_gbp=price_gbp,
        in_stock=in_stock,
        stock_count=stock_count,
        rating_stars=rating_stars,
        description=desc,
        source_page=raw_data["source_page"],
        fetched_at=raw_data["fetched_at"]
    )

    return validated_book

def process_all_books(items: list) -> list:
    validated_books = []

    for index, item in enumerate(items, start=1):
        product_url = item["product_url"]
        source_page = item["source_page"]
        
        slug = product_url.split("/")[-2]
        cache_file = f"book-{index}-{slug}.html"

        html = fetch_page(product_url, cache_file)
        soup = BeautifulSoup(html, "html.parser")

        product_main = soup.find("div", class_="product_main")
        
        title = product_main.h1.text.strip() if product_main and product_main.h1 else ""
        price_text = product_main.find("p", class_="price_color").text.strip() if product_main.find("p", class_="price_color") else ""
        availability_text = product_main.find("p", class_="instock availability").text.strip() if product_main.find("p", class_="instock availability") else ""
        
        rating_p = product_main.find("p", class_="star-rating")
        rating_text = ""
        if rating_p:
            classes = rating_p.get("class", [])
            rating_text = [c for c in classes if c != "star-rating"][0] if len(classes) > 1 else ""

        description = None
        product_desc_div = soup.find("div", id="product_description")
        if product_desc_div:
            desc_p = product_desc_div.find_next_sibling("p")
            if desc_p:
                description = desc_p.text.strip()

        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        raw_data = {
            "title": title,
            "product_url": product_url,
            "price_text": price_text,
            "availability_text": availability_text,
            "rating_text": rating_text,
            "description": description,
            "source_page": source_page,
            "fetched_at": fetched_at
        }

        # Validate with Pydantic
        validated_book = normalize_and_validate(raw_data)
        validated_books.append(validated_book.model_dump(mode="json"))

    return validated_books

def save_output(data: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "books.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} books to {output_path}")

# ---------------------------------------------------------
# 4. Main Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    print("Discovering books...")
    items = discover_books(max_pages=3)
    
    print(f"Processing and validating {len(items)} books...")
    books_data = process_all_books(items)

    save_output(books_data)

    print("\n--- STAGE 4 CHECKPOINT ---")
    print(f"records_saved = {len(books_data)}")
    print("Sample Clean Record:")
    print(json.dumps(books_data[0], indent=2))