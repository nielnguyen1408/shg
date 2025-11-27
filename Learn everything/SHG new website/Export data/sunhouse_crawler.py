#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sunhouse crawler -> Excel (col1 images; drop data:image; blacklist; optional JS rendering)
- Ảnh: CHỈ lấy trong <div class="col1">; loại tuyệt đối data:image/...; áp dụng blacklist.
- Specs: CHỈ lấy từ <div class="thongSoKyThuatSanPham1" id="menuView4"> (.text/.val)
- Output: 1 Excel (sheet 'products'): url | slug | status | image_links(JSON) | specs_json(JSON) | note
- Input: product.md (mỗi dòng 1 URL hoặc dạng [text](url))
- Optional: --js để render JS bằng Playwright (lấy đầy đủ ảnh slider)
"""

import argparse
import json
import os
import re
import time
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, urljoin, urlunparse
from urllib import robotparser

import requests
import pandas as pd
from bs4 import BeautifulSoup
from bs4.element import Tag

# ---- Optional: Playwright (only if --js is used) ----
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# ---------- Config ----------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SHG-CodeSmith/1.0; +https://example.com/bot-info)",
    "Accept-Language": "vi,vi-VN;q=0.9,en;q=0.8",
}
URL_REGEX = re.compile(r"https?://[^\s)>\]]+", re.I)
HREF_IMG = re.compile(r"\.(?:jpe?g|png|webp|gif|avif)(?:[?#].*)?$", re.I)
DATA_URI_RE = re.compile(r"^\s*data:", re.I)  # loại tuyệt đối data:
BG_URL_RE = re.compile(r"url\((?:['\"]?)(.*?)(?:['\"]?)\)", re.I)

# ---------- Blacklist ----------
# Có thể thêm trực tiếp vào đây, hoặc nạp từ file --blacklist
BLACKLIST_URLS: Set[str] = {
    "*thumb/small/",  # bỏ thumb small đi.
}

def _strip_qf(u: str) -> str:
    try:
        p = urlparse(u); p = p._replace(query="", fragment=""); return urlunparse(p)
    except Exception:
        return u

def _norm(s: str) -> str:
    return (s or "").strip().strip('"').strip("'")

def is_blacklisted(u: str) -> bool:
    if not u:
        return False
    u0 = _norm(u)
    u_noq = _strip_qf(u0).lower()
    for pat in BLACKLIST_URLS:
        pat0 = _norm(pat)
        if not pat0:
            continue
        if pat0.startswith("*"):
            if pat0[1:].lower() in u_noq:
                return True
            continue
        if re.match(r"^https?://", pat0, re.I):
            if _strip_qf(pat0).lower() == u_noq:
                return True
            continue
        if u_noq.endswith(pat0.lower()):
            return True
    return False

def load_blacklist_file(path: Optional[str]) -> None:
    if not path:
        return
    if not os.path.isfile(path):
        print(f"[WARN] Không tìm thấy file blacklist: {path}")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = _norm(line)
                if not s or s.startswith("#") or s.startswith("//"):
                    continue
                BLACKLIST_URLS.add(s)
        print(f"[OK] Nạp {len(BLACKLIST_URLS)} mẫu blacklist (kể cả mặc định).")
    except Exception as e:
        print(f"[WARN] Lỗi đọc blacklist '{path}': {e}")

# ---------- Helpers ----------
def sanitize_slug(url: str) -> str:
    slug = urlparse(url).path.rstrip("/").split("/")[-1] or "output"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug).strip("-")
    return slug or "output"

def allowed_by_robots(url: str) -> bool:
    p = urlparse(url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True  # thận trọng

def fetch(url: str) -> requests.Response:
    return requests.get(url, headers=HEADERS, timeout=20)

def is_http_image(u: str) -> bool:
    if not u:
        return False
    s = u.strip().lower()
    if s.startswith(("data:", "javascript:", "about:")):
        return False
    return s.startswith("http://") or s.startswith("https://") or s.startswith("//")

def pick_best_img_src(img: Tag, base: str) -> Optional[str]:
    """Ưu tiên src -> data-src/data-original/data-lazy/data-image -> srcset; loại data:/blacklist."""
    src = (img.get("src") or "").strip()

    for k in ("data-src", "data-original", "data-lazy", "data-image"):
        if (not src) and img.get(k):
            cand = (img.get(k) or "").strip()
            if cand and not DATA_URI_RE.match(cand):
                src = cand

    if not src:
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
            for cand in reversed(parts):
                if cand and not DATA_URI_RE.match(cand):
                    src = cand
                    break

    if (not src) or DATA_URI_RE.match(src):
        return None

    full = urljoin(base, src)
    if not is_http_image(full) or is_blacklisted(full):
        return None
    return full

# ---- IMAGE: chỉ trong div.col1 (requests + BS4) ----
def collect_images_col1_static(soup: BeautifulSoup, base_url: str) -> List[str]:
    imgs, seen = [], set()

    for col in soup.select("div.col1"):
        # <img>
        for img in col.select("img"):
            u = pick_best_img_src(img, base_url)
            if u and is_http_image(u) and (not is_blacklisted(u)) and u not in seen:
                seen.add(u); imgs.append(u)

        # Link zoom ảnh
        for a in col.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            if HREF_IMG.search(href):
                u = urljoin(base_url, href)
                if is_http_image(u) and (not is_blacklisted(u)) and u not in seen:
                    seen.add(u); imgs.append(u)

        # background-image trong style (slider CSS)
        for el in col.select("[style]"):
            st = el.get("style") or ""
            for m in BG_URL_RE.finditer(st):
                u = urljoin(base_url, (m.group(1) or "").strip())
                if HREF_IMG.search(u) and is_http_image(u) and (not is_blacklisted(u)) and u not in seen:
                    seen.add(u); imgs.append(u)

    # Lọc lần chót
    imgs = [u for u in imgs if not DATA_URI_RE.match(u) and not is_blacklisted(u)]
    return imgs

# ---- IMAGE: Playwright (JS render) ----
def collect_images_col1_js(url: str) -> List[str]:
    """Dùng Playwright load trang, chờ render, quét ảnh trong div.col1 (img/a[img]/background-image)."""
    if not PLAYWRIGHT_AVAILABLE:
        print("[WARN] Playwright chưa cài. Bỏ qua --js.")
        return []
    results, seen = [], set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="vi-VN", user_agent=HEADERS["User-Agent"])
        page = context.new_page()
        page.set_default_timeout(15000)
        page.goto(url, wait_until="domcontentloaded")
        try:
            # chờ khu vực col1 xuất hiện (tối đa 10s), sau đó thêm chờ network idle nhẹ
            page.wait_for_selector("div.col1", timeout=10000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
        except Exception:
            pass

        # Scroll nhẹ để lazy-load
        try:
            page.evaluate("window.scrollBy(0, 400)")
            time.sleep(0.4)
        except Exception:
            pass

        # Lấy tất cả nodes trong col1
        nodes = page.query_selector_all("div.col1")
        for blk in nodes:
            # IMG
            for img in blk.query_selector_all("img"):
                cand = None
                try:
                    src = (img.get_attribute("src") or "").strip()
                    ds  = (img.get_attribute("data-src") or img.get_attribute("data-original") or
                           img.get_attribute("data-lazy") or img.get_attribute("data-image") or "")
                    ds = ds.strip()
                    srcset = (img.get_attribute("srcset") or img.get_attribute("data-srcset") or "").strip()
                    if src and not DATA_URI_RE.match(src):
                        cand = src
                    elif ds and not DATA_URI_RE.match(ds):
                        cand = ds
                    elif srcset:
                        parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
                        for c in reversed(parts):
                            if c and not DATA_URI_RE.match(c):
                                cand = c; break
                except Exception:
                    cand = None
                if cand and is_http_image(cand) and (not is_blacklisted(cand)) and cand not in seen:
                    seen.add(cand); results.append(cand)

            # <a href="*.jpg"> (zoom)
            for a in blk.query_selector_all("a[href]"):
                href = (a.get_attribute("href") or "").strip()
                if href and HREF_IMG.search(href) and is_http_image(href) and (not is_blacklisted(href)) and href not in seen:
                    seen.add(href); results.append(href)

            # background-image
            for el in blk.query_selector_all("[style]"):
                st = (el.get_attribute("style") or "").strip()
                for m in BG_URL_RE.finditer(st):
                    u = (m.group(1) or "").strip()
                    if u and HREF_IMG.search(u) and is_http_image(u) and (not is_blacklisted(u)) and u not in seen:
                        seen.add(u); results.append(u)

        context.close()
        browser.close()

    # Lọc lần cuối (phòng hờ)
    results = [u for u in results if not DATA_URI_RE.match(u) and not is_blacklisted(u)]
    return results

# ---- SPECS (#menuView4) ----
def html_to_text_preserve_br(node: Tag) -> str:
    return node.get_text("\n", strip=True)

def collect_specs_menuView4(soup: BeautifulSoup) -> List[Dict[str, str]]:
    container = soup.select_one("div.thongSoKyThuatSanPham1#menuView4")
    if not container:
        return []
    data: List[Dict[str, str]] = []
    for li in container.select("ul > li"):
        k = li.select_one(".text")
        v = li.select_one(".val")
        if not k or not v:
            continue
        key = k.get_text(" ", strip=True)
        val = html_to_text_preserve_br(v)
        if key and val:
            data.append({"key": key, "value": val})
    return data

# ---- INPUT ----
def parse_urls_from_markdown(md_path: str) -> List[str]:
    if not os.path.isfile(md_path):
        raise FileNotFoundError(f"Không tìm thấy file: {md_path}")
    urls: List[str] = []
    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("<!--"):
                continue
            m = re.search(r"\]\((https?://[^\s)]+)\)", s)
            if m:
                urls.append(m.group(1)); continue
            for m in URL_REGEX.finditer(s):
                urls.append(m.group(0))
    out, seen = [], set()
    for u in urls:
        if "sunhouse.com.vn" in urlparse(u).netloc and u not in seen:
            seen.add(u); out.append(u)
    return out

# ---- PROCESS ----
def process_url(url: str, use_js: bool) -> Dict[str, str]:
    rec = {"url": url, "slug": sanitize_slug(url), "status": "OK",
           "image_links": "[]", "specs_json": "[]", "note": ""}

    if not allowed_by_robots(url):
        rec["status"] = "SKIP_ROBOTS"; rec["note"] = "robots.txt không cho phép"; return rec

    try:
        resp = fetch(url)
    except Exception as e:
        rec["status"] = "ERROR"; rec["note"] = f"Lỗi kết nối: {e}"; return rec

    if resp.status_code >= 400:
        rec["status"] = f"HTTP_{resp.status_code}"; rec["note"] = "Trang lỗi/không tồn tại"; return rec

    soup = BeautifulSoup(resp.text, "lxml")

    # Ảnh trong col1
    if use_js:
        imgs = collect_images_col1_js(resp.url)
        if not imgs:
            # fallback tĩnh nếu JS không gom được
            imgs = collect_images_col1_static(soup, resp.url)
    else:
        imgs = collect_images_col1_static(soup, resp.url)
    rec["image_links"] = json.dumps(imgs, ensure_ascii=False)

    # Specs: #menuView4
    specs = collect_specs_menuView4(soup)
    if specs:
        rec["specs_json"] = json.dumps(specs, ensure_ascii=False)
    else:
        rec["status"] = "NO_SPECS_MENUVIEW4"
        rec["note"] = "Không thấy div.thongSoKyThuatSanPham1#menuView4 hoặc không có <li> hợp lệ"

    return rec

def main():
    ap = argparse.ArgumentParser(description="Sunhouse -> Excel (col1 images; blacklist; optional JS; specs #menuView4)")
    ap.add_argument("-i", "--input", default="product.md", help="Đường dẫn file product.md")
    ap.add_argument("-o", "--out", default="sunhouse_products.xlsx", help="File Excel output")
    ap.add_argument("-b", "--blacklist", default=None, help="File blacklist (mỗi dòng 1 mẫu)")
    ap.add_argument("--js", action="store_true", help="Bật renderer JS (Playwright) để lấy ảnh slider đầy đủ")
    args = ap.parse_args()

    load_blacklist_file(args.blacklist)

    if args.js and not PLAYWRIGHT_AVAILABLE:
        print("[WARN] Bạn bật --js nhưng chưa cài playwright. Cài bằng:")
        print("  pip install playwright && playwright install chromium")
        print("Tiếp tục chạy ở chế độ tĩnh...")

    try:
        urls = parse_urls_from_markdown(args.input)
    except Exception as e:
        print(f"[ERR] Đọc file input: {e}")
        return
    if not urls:
        print("[WARN] Không có URL hợp lệ trong input.")
        return

    rows = []
    for u in urls:
        rec = process_url(u, use_js=args.js and PLAYWRIGHT_AVAILABLE)
        rows.append(rec)
        try:
            n_img = len(json.loads(rec["image_links"]))
            n_specs = len(json.loads(rec["specs_json"]))
        except Exception:
            n_img = n_specs = 0
        print(f"[{rec['status']}] {rec['slug']} | imgs:{n_img} | specs:{n_specs} | note:{rec['note']}")
        time.sleep(0.4)

    df = pd.DataFrame(rows, columns=["url", "slug", "status", "image_links", "specs_json", "note"])
    with pd.ExcelWriter(args.out, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="products", index=False)
    print(f"[OK] Xuất Excel -> {args.out}")

if __name__ == "__main__":
    main()
