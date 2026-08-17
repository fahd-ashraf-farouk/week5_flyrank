import os
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = "cache"
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/fahd-ashraf-farouk/week5_flyrank)"
}

def fetch_page(url: str, cache_filename: str) -> str:

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return html_content

    time.sleep(0.5)

    response = requests.get(url, headers=HEADERS, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url}, status code: {response.status_code}")

    html_content = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_content

def discover_books(max_pages: int = 3):
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

def extract_book_details(items: list) -> list:
    raw_records = []

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

        raw_record = {
            "title": title,
            "product_url": product_url,
            "price_text": price_text,
            "availability_text": availability_text,
            "rating_text": rating_text,
            "description": description,
            "source_page": source_page,
            "fetched_at": fetched_at
        }
        
        raw_records.append(raw_record)

    return raw_records

if __name__ == "__main__":
    print("Discovering book links...")
    items = discover_books(max_pages=3)
    
    print(f"Extracting details for {len(items)} books...")
    raw_records = extract_book_details(items)

    print("\n--- STAGE 3 CHECKPOINT ---")
    print(f"detail_pages = {len(raw_records)}")
    print("\nSample Raw Record:")
    import json
    print(json.dumps(raw_records[0], indent=2))