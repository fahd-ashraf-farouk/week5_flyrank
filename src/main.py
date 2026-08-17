import os
import re
import json
import time
import random
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

MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0

# ---------------------------------------------------------
# 2. Run Report Tracker
# ---------------------------------------------------------
class RunReport:
    def __init__(self):
        self.start_time = time.time()
        self.pages_discovered = 0
        self.pages_scraped = 0
        self.pages_cached = 0
        self.pages_network = 0
        self.pages_failed = 0
        self.records_extracted = 0
        self.records_saved = 0

    def to_dict(self) -> dict:
        duration = round(time.time() - self.start_time, 2)
        status = "SUCCESS" if self.pages_failed == 0 else "PARTIAL_SUCCESS"
        if self.records_saved == 0:
            status = "FAILED"

        return {
            "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": duration,
            "pages_discovered": self.pages_discovered,
            "pages_scraped": self.pages_scraped,
            "pages_cached": self.pages_cached,
            "pages_network": self.pages_network,
            "pages_failed": self.pages_failed,
            "records_extracted": self.records_extracted,
            "records_saved": self.records_saved,
            "status": status
        }

    def save(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        report_path = os.path.join(OUTPUT_DIR, "run-report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Report saved to {report_path}")

# ---------------------------------------------------------
# 3. Pydantic Schema
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
# 4. Fetch Function with Tracking
# ---------------------------------------------------------
def fetch_page_with_retry(url: str, cache_filename: str, report: RunReport) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    # Cache Hit
    if os.path.exists(cache_path):
        report.pages_cached += 1
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    # Network Fetch
    report.pages_network += 1
    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        time.sleep(0.5)

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)

            if response.status_code == 200:
                html_content = response.text
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                return html_content

            if response.status_code in [404, 410]:
                raise Exception(f"Permanent HTTP error {response.status_code} for {url}")

            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                sleep_time = float(retry_after)
            else:
                jitter = random.uniform(0.1, 0.5)
                sleep_time = (INITIAL_BACKOFF * (2 ** (attempt - 1))) + jitter

            time.sleep(sleep_time)

        except (requests.exceptions.RequestException, Exception) as e:
            if "Permanent HTTP error" in str(e) or attempt == MAX_RETRIES:
                report.pages_failed += 1
                raise e
            
            jitter = random.uniform(0.1, 0.5)
            sleep_time = (INITIAL_BACKOFF * (2 ** (attempt - 1))) + jitter
            time.sleep(sleep_time)

    report.pages_failed += 1
    raise Exception(f"Failed to fetch {url} after {MAX_RETRIES} attempts.")

# ---------------------------------------------------------
# 5. Pipeline Stages
# ---------------------------------------------------------
def discover_books(report: RunReport, max_pages: int = 3) -> list:
    current_url = BASE_URL
    discovered_items = []
    pages_crawled = 0

    while current_url and pages_crawled < max_pages:
        pages_crawled += 1
        cache_file = f"catalogue-page-{pages_crawled}.html"
        
        try:
            html = fetch_page_with_retry(current_url, cache_file, report)
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
        except Exception as e:
            print(f"[ERROR] Failed discovering catalogue page {current_url}: {e}")
            break

    report.pages_discovered = len(discovered_items)
    return discovered_items

def normalize_and_validate(raw_data: dict) -> BookSchema:
    price_match = re.search(r"[\d.]+", raw_data["price_text"])
    price_gbp = float(price_match.group()) if price_match else 0.0

    in_stock = "In stock" in raw_data["availability_text"]
    stock_match = re.search(r"\d+", raw_data["availability_text"])
    stock_count = int(stock_match.group()) if stock_match else 0

    rating_stars = RATING_MAP.get(raw_data["rating_text"], 0)
    desc = raw_data["description"].strip() if raw_data["description"] else None

    return BookSchema(
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

def process_all_books(items: list, report: RunReport) -> list:
    validated_books = []

    for index, item in enumerate(items, start=1):
        product_url = item["product_url"]
        source_page = item["source_page"]
        slug = product_url.split("/")[-2]
        cache_file = f"book-{index}-{slug}.html"

        try:
            html = fetch_page_with_retry(product_url, cache_file, report)
            report.pages_scraped += 1

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

            report.records_extracted += 1

            validated_book = normalize_and_validate(raw_data)
            validated_books.append(validated_book.model_dump(mode="json"))
            report.records_saved += 1

        except Exception as e:
            print(f"[SKIP] Error processing book at {product_url}: {e}")

    return validated_books

def save_output(data: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "books.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------
# 6. Main Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    report = RunReport()

    print("Running scraper pipeline...")
    items = discover_books(report, max_pages=3)
    books_data = process_all_books(items, report)

    save_output(books_data)
    report.save()

    # Stage 6 Checkpoint Output
    print("\n--- STAGE 6 CHECKPOINT ---")
    print(json.dumps(report.to_dict(), indent=2))