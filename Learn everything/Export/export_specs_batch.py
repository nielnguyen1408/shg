#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch export "Thông số kỹ thuật" từ nhiều URL Sunhouse.
- Đọc được urls.txt (mỗi dòng 1 URL) hoặc urls.md (trích URL trong Markdown).
- Đa luồng (thread pool), retry nhẹ, timeout.
- Xuất:
  - exports/<slug>.json và exports/<slug>.csv cho từng sản phẩm
  - all_specs_long.csv (dạng dài: url, title, thuoc_tinh, gia_tri)
  - all_specs.jsonl (mỗi dòng 1 sản phẩm: {"url","title","specs":{...}})
Yêu cầu: pip install requests beautifulsoup4 lxml pandas
"""

import re
import os
import json
import time
import argparse
import concurrent.futures as cf
from typing import Dict, List, Tuple, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd

# ================= Utils =================

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def slugify(s: str, fallback: str = "product") -> str:
    s = normalize_space(s).lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or fallback

def fetch_html(url: str, timeout: int = 30, max_retries: int = 2, delay: float = 1.0) -> str:
    headers = {"User-Agent": UA}
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(delay)
    raise last_err

# ================= Parsers =================

def find_specs_root(soup: BeautifulSoup):
    """Tìm khối 'Thông số kỹ thuật' (ưu tiên heading -> block ngay sau)."""
    heading = soup.find(
        lambda tag: tag.name in ["h1","h2","h3","h4","strong","p","span"]
        and tag.get_text(strip=True)
        and re.search(r"thông\s*số\s*kỹ\s*thuật", tag.get_text(strip=True), re.I)
    )
    if heading:
        nxt = heading.find_next(lambda t: t.name in ["ul","ol","table","div","section"])
        if nxt:
            return nxt

    # Fallback: table có từ khóa
    for tb in soup.find_all("table"):
        ttext = normalize_space(tb.get_text(" ", strip=True)).lower()
        if any(k in ttext for k in [
            "kích thước","chất liệu","xuất xứ","bảo hành","đường kính",
            "công suất","trọng lượng","dung tích","mã sản phẩm"
        ]):
            return tb

    # Fallback: div/section giàu từ khóa
    for d in soup.find_all(["div","section"]):
        t = normalize_space(d.get_text(" ", strip=True)).lower()
        if ("thông số" in t and "kỹ thuật" in t) or \
           sum(1 for kw in ["kích thước","chất liệu","xuất xứ","bảo hành","mã sản phẩm"] if kw in t) >= 2:
            return d
    return None

def extract_kv_from_table(table) -> List[Tuple[str, str]]:
    out = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th","td"])
        if len(cells) >= 2:
            key = normalize_space(cells[0].get_text(" ", strip=True))
            val = normalize_space(" ".join(c.get_text(" ", strip=True) for c in cells[1:]))
            if key and val:
                out.append((key, val))
    return out

def extract_kv_from_list(list_tag) -> List[Tuple[str, str]]:
    """
    Nhiều trang dùng <li> với nhãn dòng 1 + giá trị ở các dòng sau.
    Lấy phần đầu làm key, phần còn lại nối lại làm value.
    """
    out = []
    for li in list_tag.find_all("li"):
        parts = [p.strip() for p in li.stripped_strings if p and p.strip()]
        if not parts:
            continue
        key = parts[0]
        val = " ".join(parts[1:]).strip()
        if not val or len(key) > 200:
            continue
        out.append((normalize_space(key), normalize_space(val)))
    return out

def extract_kv_from_block(block) -> List[Tuple[str, str]]:
    """Nếu chỉ có khối văn bản: tách theo 'label: value'."""
    text = block.get_text("\n", strip=True)
    lines = [normalize_space(x) for x in text.split("\n") if normalize_space(x)]
    out = []
    for line in lines:
        if re.search(r"thông\s*số\s*kỹ\s*thuật", line, re.I):
            continue
        parts = re.split(r"\s*[:：]\s*", line, maxsplit=1)
        if len(parts) == 2:
            key, val = parts
            if key and val:
                out.append((key, val))
    return out

def parse_specs(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    specs_root = find_specs_root(soup)
    if not specs_root:
        return {}
    if specs_root.name == "table":
        kv = extract_kv_from_table(specs_root)
    elif specs_root.name in ["ul","ol"]:
        kv = extract_kv_from_list(specs_root)
    else:
        table = specs_root.find("table")
        if table:
            kv = extract_kv_from_table(table)
        else:
            lst = specs_root.find(["ul","ol"])
            if lst:
                kv = extract_kv_from_list(lst)
            else:
                kv = extract_kv_from_block(specs_root)
    specs = {}
    for k, v in kv:
        if k not in specs:
            specs[k] = v
    return specs

def parse_title(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    if soup.find("h1") and normalize_space(soup.find("h1").get_text()):
        return normalize_space(soup.find("h1").get_text())
    if soup.title and normalize_space(soup.title.get_text()):
        title = normalize_space(soup.title.get_text())
        return re.sub(r"\s*\|\s*.*$", "", title).strip()
    return None

# ================= I/O helpers =================

URL_RE = re.compile(r"""(?ix)
    \bhttps?://[^\s)<>"']+
""")

def read_urls_from_file(path: str) -> List[str]:
    """
    - .txt: mỗi dòng 1 URL (bỏ dòng trống, # comment)
    - .md : trích tất cả URL (pattern http/https) trong file Markdown
    """
    urls: List[str] = []
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if ext == ".md":
        urls = URL_RE.findall(content)
    else:
        # coi như .txt
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = URL_RE.search(line)
            if m:
                urls.append(m.group(0))

    # loại trùng, giữ thứ tự
    seen = set()
    uniq = []
    for u in urls:
        if u not in seen:
            uniq.append(u)
            seen.add(u)
    return uniq

def ensure_outdir(outdir: str):
    os.makedirs(outdir, exist_ok=True)

def save_per_product(outdir: str, url: str, title: Optional[str], specs: Dict[str, str]):
    # Dùng mã sản phẩm nếu có để đặt tên
    code = None
    for k in specs:
        if re.search(r"mã\s*sản\s*phẩm", k, re.I):
            code = specs[k]
            break
    base = " ".join([p for p in [code, title] if p]) or url.split("/")[-1] or "product"
    fname = slugify(base)

    # JSON
    with open(os.path.join(outdir, f"{fname}.json"), "w", encoding="utf-8") as f:
        json.dump({"url": url, "title": title, "specs": specs}, f, ensure_ascii=False, indent=2)

    # CSV (2 cột)
    rows = [{"thuoc_tinh": k, "gia_tri": v} for k, v in specs.items()]
    pd.DataFrame(rows).to_csv(os.path.join(outdir, f"{fname}.csv"), index=False, encoding="utf-8-sig")

# ================= Worker =================

def process_one(url: str, timeout: int) -> Dict:
    try:
        html = fetch_html(url, timeout=timeout)
        title = parse_title(html)
        specs = parse_specs(html)
        ok = bool(specs)
        return {"url": url, "title": title, "specs": specs, "ok": ok, "error": None}
    except Exception as e:
        return {"url": url, "title": None, "specs": {}, "ok": False, "error": str(e)}

# ================= Main =================

def main():
    parser = argparse.ArgumentParser(description="Batch export 'Thông số kỹ thuật' Sunhouse từ nhiều URL.")
    parser.add_argument("--infile", required=True, help="Đường dẫn urls.txt hoặc urls.md")
    parser.add_argument("--outdir", default="exports", help="Thư mục xuất file (mặc định: exports/)")
    parser.add_argument("--workers", type=int, default=6, help="Số luồng tải song song (mặc định: 6)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout mỗi request (giây), mặc định 30")
    args = parser.parse_args()

    urls = read_urls_from_file(args.infile)
    if not urls:
        print("❗Không tìm thấy URL trong file input.")
        return

    print(f"Tổng URL: {len(urls)}  |  Workers: {args.workers}  |  Outdir: {args.outdir}")
    ensure_outdir(args.outdir)

    results: List[Dict] = []
    # Đa luồng tải & parse
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(process_one, u, args.timeout) for u in urls]
        for i, fut in enumerate(cf.as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            status = "OK" if res["ok"] else f"ERR ({res['error']})"
            print(f"[{i}/{len(urls)}] {status} - {res['url']}")

    # Lưu per-product + tổng hợp
    all_rows = []
    with open("all_specs.jsonl", "w", encoding="utf-8") as jlf:
        for r in results:
            if r["ok"]:
                save_per_product(args.outdir, r["url"], r["title"], r["specs"])
                # ghi jsonl
                jlf.write(json.dumps({"url": r["url"], "title": r["title"], "specs": r["specs"]},
                                     ensure_ascii=False) + "\n")
                # rows cho CSV dài
                for k, v in r["specs"].items():
                    all_rows.append({
                        "url": r["url"],
                        "title": r["title"],
                        "thuoc_tinh": k,
                        "gia_tri": v
                    })
            else:
                # vẫn ghi dòng lỗi vào jsonl cho dễ debug
                jlf.write(json.dumps({"url": r["url"], "title": None, "error": r["error"], "specs": {}},
                                     ensure_ascii=False) + "\n")

    if all_rows:
        pd.DataFrame(all_rows).to_csv("all_specs_long.csv", index=False, encoding="utf-8-sig")
        print("✔ Đã lưu tổng hợp: all_specs_long.csv, all_specs.jsonl")
    else:
        print("⚠ Không có bản ghi nào trích xuất thành công (kiểm tra all_specs.jsonl để biết lỗi).")

if __name__ == "__main__":
    main()


#Cách sử dụng: cmd cd vào folder chứa file, sau đó dùng command này nếu dùng urls.md
#python export_specs_batch.py --infile urls.md --workers 8

#Nếu dùng file urls.txt
#python export_specs_batch.py --infile urls.txt