# Books to Scrape - The Polite Scraper (FlyRank Internship W5-A9)

A polite, robust, and idempotent web scraper built in Python to extract and normalize book data from the Books to Scrape practice sandbox.

---

## Target Classification
* Target Site: Books to Scrape (https://books.toscrape.com/)
* Purpose: Sandbox built specifically for scraping practice.
* Scope: First 3 catalogue pages (~60 books).
* Data Collected: Book title, product URL, price (GBP), availability status, stock count, rating stars, description, source page, and fetch timestamp.
* Robots.txt Status: No robots file found (robots.txt returned 404).
* Ethics Agreement: Scraping is explicitly allowed on this practice site. I will not reuse this code on another site without checking its rules and terms first.

---

## Tech Stack & Requirements
* Language: Python 3.10+
* Libraries:
  * requests: For HTTP communication with custom User-Agent, timeouts, and error handling.
  * beautifulsoup4: For HTML parsing and extraction.
  * pydantic: For data schema validation and type coercion.

---

## How to Run (Quickstart under 5 Minutes)

### 1. Clone the repository
```bash
git clone [https://github.com/fahd-ashraf-farouk/week5_flyrank.git](https://github.com/fahd-ashraf-farouk/week5_flyrank.git)
cd week5_flyrank