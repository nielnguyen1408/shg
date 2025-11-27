import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import requests
import sys
from pathlib import Path

# Paths
INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "urls.txt"
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else "results.csv"

# Message snippet to detect "no results" page (case-insensitive, relaxed match)
# Updated per request: look for the exact phrase "Tìm thấy 0 kết quả"
NOT_FOUND_SNIPPET = ("tìm thấy 0 kết quả")

# Heuristic patterns to detect Sunhouse product URLs and canonical links
PRODUCT_HREF_PATTERN = re.compile(
    r'href=["\'](?P<href>(?:https?://[^"\']+)?/(?:san-pham|product|products)/[^"\']+)["\']',
    flags=re.IGNORECASE,
)

CANONICAL_PATTERN = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\'](?P<href>[^"\']+)["\']',
    flags=re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LinkChecker/1.0; +https://example.invalid)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi,vi-VN;q=0.9,en;q=0.8",
    "Connection": "close",
}

TIMEOUT = 20
MAX_WORKERS = 20
RETRIES = 2
BACKOFF = 1.5

def fetch(url: str):
    last_exc = None
    for attempt in range(RETRIES + 1):
        try:
            return requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        except Exception as e:
            last_exc = e
            if attempt < RETRIES:
                time.sleep((BACKOFF ** attempt))
    raise last_exc

def detect_status_and_product(resp: requests.Response):
    status_code = getattr(resp, "status_code", None)
    final_url = getattr(resp, "url", "")

    if status_code is None:
        return "http_error", "", "No status code"

    if status_code >= 400:
        return "http_error", "", f"HTTP {status_code}"

    text_lower = resp.text.lower()

    if NOT_FOUND_SNIPPET in text_lower:
        return "not_found", "", "search page says no results"

    if "/search/" not in final_url:
        return "product", final_url, "redirected or landed on non-search page"

    m = CANONICAL_PATTERN.search(resp.text)
    if m:
        href = m.group("href")
        if href and "/search/" not in href:
            return "product", href, "canonical suggests product"

    m2 = PRODUCT_HREF_PATTERN.search(resp.text)
    if m2:
        href = m2.group("href")
        if href.startswith("/"):
            parsed = urlparse(final_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        return "product", href, "found product link in page"

    return "unknown", "", "no not-found text, no product link detected"

def process_url(url: str):
    url = url.strip()
    if not url:
        return {
            "input_url": url,
            "http_status": "",
            "final_url": "",
            "status": "skip",
            "product_url": "",
            "notes": "empty line",
        }

    try:
        resp = fetch(url)
        status, product_url, notes = detect_status_and_product(resp)
        return {
            "input_url": url,
            "http_status": resp.status_code,
            "final_url": resp.url,
            "status": status,
            "product_url": product_url,
            "notes": notes,
        }
    except Exception as e:
        return {
            "input_url": url,
            "http_status": "",
            "final_url": "",
            "status": "http_error",
            "product_url": "",
            "notes": str(e),
        }

def main():
    in_path = Path(INPUT_FILE)
    if not in_path.exists():
        print(f"Input file not found: {in_path}")
        sys.exit(2)

    with in_path.open("r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_url, u): u for u in urls}
        done_count = 0
        total = len(futures)
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            done_count += 1
            if done_count % 50 == 0 or done_count == total:
                print(f"Processed {done_count}/{total}")

    fieldnames = ["input_url", "http_status", "final_url", "status", "product_url", "notes"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as fo:
        writer = csv.DictWriter(fo, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    sum_not_found = sum(1 for r in results if r["status"] == "not_found")
    sum_product = sum(1 for r in results if r["status"] == "product")
    sum_unknown = sum(1 for r in results if r["status"] == "unknown")
    sum_error = sum(1 for r in results if r["status"] == "http_error")
    print("Done.")
    print(f"product: {sum_product} | not_found: {sum_not_found} | unknown: {sum_unknown} | http_error: {sum_error}")
    print(f"Saved -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()