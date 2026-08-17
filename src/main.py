import os
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = "cache"
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/fahd-ashraf-farouk/week5_flyrank)"
}

def fetch_page(url: str, cache_filename: str) -> str:
    """
    تحميل الصفحة أو قراءتها من الـ Cache إذا كانت محفوظة.
    تطبيق delay فقط إذا تم إرسال طلب حقيقي للشبكة.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        print(f"CACHE HIT | {cache_filename}")
        return html_content

    # أدب السكرايبر: انتظار نصف ثانية قبل أي طلب حقيقي 
    time.sleep(0.5)

    print(f"FETCH | URL: {url}")
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url}, status: {response.status_code}")

    html_content = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_content

def discover_books(max_pages: int = 3):
    """
    المرور على صفحات الكتالوج وتجميع روابط الـ 60 كتاب
    """
    current_url = BASE_URL
    book_urls = []
    pages_crawled = 0

    while current_url and pages_crawled < max_pages:
        pages_crawled += 1
        cache_file = f"catalogue-page-{pages_crawled}.html"
        
        # 1. جلب محتوى الصفحة
        html = fetch_page(current_url, cache_file)
        soup = BeautifulSoup(html, "html.parser")

        # 2. استخراج روابط الكتب داخل الصفحة
        articles = soup.find_all("article", class_="product_pod")
        for article in articles:
            rel_link = article.h3.a["href"]
            # تحويل الرابط النسبي إلى مطلق باستخدام urljoin [cite: 85]
            abs_link = urljoin(current_url, rel_link)
            book_urls.append(abs_link)

        # 3. العثور على رابط الصفحة التالية (Next link) 
        next_button = soup.find("li", class_="next")
        if next_button and next_button.a:
            next_rel_link = next_button.a["href"]
            current_url = urljoin(current_url, next_rel_link)
        else:
            current_url = None

    # إزالة التكرار
    unique_book_urls = list(dict.fromkeys(book_urls))

    # طباعة نتائج الـ Checkpoint الرسمية 
    print("\n--- STAGE 2 CHECKPOINT ---")
    print(f"catalogue_pages = {pages_crawled}")
    print(f"discovered = {len(book_urls)}")
    print(f"unique_urls = {len(unique_book_urls)}")

    return unique_book_urls

if __name__ == "__main__":
    discover_books(max_pages=3)