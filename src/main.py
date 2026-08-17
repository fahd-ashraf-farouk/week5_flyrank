import os
import requests

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
        print(f"CACHE HIT | File: {cache_filename} | Size: {len(html_content)} bytes")
        return html_content

    print(f"FETCH | URL: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch page. Status code: {response.status_code}")

        html_content = response.text
        
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"FETCH | File saved: {cache_filename} | Size: {len(html_content)} bytes")
        return html_content

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        raise e

if __name__ == "__main__":
    fetch_page(BASE_URL, "catalogue-page-1.html")