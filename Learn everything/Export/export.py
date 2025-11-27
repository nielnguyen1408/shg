#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export "Thông số kỹ thuật" từ trang sản phẩm Sunhouse.
- Hỗ trợ 1 URL hoặc nhiều URL (qua --infile).
- Xuất JSON + CSV.
Yêu cầu: pip install requests beautifulsoup4 lxml pandas
"""

import re
import os
import csv
import json
import argparse
import pathlib
from typing import Dict, List, Tuple, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd


# ============= Utils =============

def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def slugify(s: str, fallback: str = "product") -> str:
    s = normalize_space(s)
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or fallback

def fetch_html(url: str, timeout: int = 30) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


# ============= Core parsers =============

def find_specs_root(soup: BeautifulSoup):
    """
    Tìm phần tử gốc chứa 'Thông số kỹ thuật'.
    Ưu tiên: heading có text khớp -> phần tử danh sách/bảng ngay sau.
    Fallback: quét table/ul/ol/div có dấu hiệu là block thông số.
    """
    heading = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3", "h4", "strong", "p", "span"]
        and tag.get_text(strip=True)
        and re.search(r"thông\s*số\s*kỹ\s*thuật", tag.get_text(strip=True), re.I)
    )

    if heading:
        # phần tử (ul/ol/table/div/section) gần nhất sau heading
        nxt = heading.find_next(lambda t: t.name in ["ul", "ol", "table", "div", "section"])
        if nxt:
            return nxt

    # Fallback 1: tìm table có nhiều nhãn đặc trưng
    for tb in soup.find_all("table"):
        ttext = normalize_space(tb.get_text(" ", strip=True)).lower()
        if any(k in ttext for k in [
            "kích thước", "chất liệu", "xuất xứ", "bảo hành", "đường kính",
            "công suất", "trọng lượng", "dung tích", "mã sản phẩm"
        ]):
            return tb

    # Fallback 2: tìm khối div có cụm từ khóa
    for d in soup.find_all(["div", "section"]):
        t = normalize_space(d.get_text(" ", strip=True)).lower()
        if ("thông số" in t and "kỹ thuật" in t) or \
           sum(1 for kw in ["kích thước", "chất liệu", "xuất xứ", "bảo hành", "mã sản phẩm"] if kw in t) >= 2:
            return d

    return None

def extract_kv_from_table(table) -> List[Tuple[str, str]]:
    data = []
    rows = table.find_all("tr")
    for tr in rows:
        cells = tr.find_all(["th", "td"])
        if len(cells) >= 2:
            key = normalize_space(cells[0].get_text(" ", strip=True))
            val = normalize_space(" ".join(c.get_text(" ", strip=True) for c in cells[1:]))
            if key and val:
                data.append((key, val))
    return data

def extract_kv_from_list(list_tag) -> List[Tuple[str, str]]:
    """
    Nhiều trang Sunhouse để mỗi <li> có 2 dòng: [Nhãn] + [Giá trị],
    hoặc nhãn và nhiều mẩu con bên dưới. Lấy phần đầu làm key, phần còn lại nối làm value.
    """
    out = []
    for li in list_tag.find_all("li"):
        parts = [p.strip() for p in li.stripped_strings if p and p.strip()]
        if not parts:
            continue
        key = parts[0]
        val = " ".join(parts[1:]).strip()
        # Bỏ qua mục không có giá trị hoặc mục tiêu đề tràn dài
        if not val or len(key) > 200:
            continue
        out.append((normalize_space(key), normalize_space(val)))
    return out

def extract_kv_from_block(block) -> List[Tuple[str, str]]:
    """
    Nếu chỉ có 1 div/section với nhiều dòng 'label: value' bên trong.
    """
    text = block.get_text("\n", strip=True)
    lines = [normalize_space(x) for x in text.split("\n") if normalize_space(x)]
    data = []
    for line in lines:
        if re.search(r"thông\s*số\s*kỹ\s*thuật", line, re.I):
            continue
        parts = re.split(r"\s*[:：]\s*", line, maxsplit=1)
        if len(parts) == 2:
            key, val = parts
            if key and val:
                data.append((key, val))
    return data

def parse_specs(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    specs_root = find_specs_root(soup)
    if not specs_root:
        return {}

    if specs_root.name == "table":
        kv_pairs = extract_kv_from_table(specs_root)
    elif specs_root.name in ["ul", "ol"]:
        kv_pairs = extract_kv_from_list(specs_root)
    else:
        # thử ưu tiên table/list con
        table = specs_root.find("table")
        if table:
            kv_pairs = extract_kv_from_table(table)
        else:
            lst = specs_root.find(["ul", "ol"])
            if lst:
                kv_pairs = extract_kv_from_list(lst)
            else:
                kv_pairs = extract_kv_from_block(specs_root)

    # Lọc trùng key, giữ lần đầu
    specs = {}
    for k, v in kv_pairs:
        if k not in specs:
            specs[k] = v
    return specs

def parse_title_and_code(html: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Lấy tên sản phẩm (title/h1) và mã sản phẩm (nếu có trong specs/HTML).
    """
    soup = BeautifulSoup(html, "lxml")

    # Title/H1
    title = None
    h1 = soup.find("h1")
    if h1 and normalize_space(h1.get_text()):
        title = normalize_space(h1.get_text())
    if not title and soup.title and normalize_space(soup.title.get_text()):
        title = normalize_space(soup.title.get_text())
        # cắt hậu tố site nếu có
        title = re.sub(r"\s*\|\s*.*$", "", title).strip()

    # SKU/mã sản phẩm khả dĩ trong trang
    # 1) thử meta/schema/keywords phổ biến
    sku = None
    # 2) nếu không có, sẽ lấy từ specs sau
    return title, sku


# ============= Exporters =============

def write_outputs(base_name: str, outdir: str, url: str, title: Optional[str],
                  specs: Dict[str, str]):
    os.makedirs(outdir, exist_ok=True)

    # Nếu specs có "Mã sản phẩm" thì bổ sung vào file name
    code = None
    for k in specs.keys():
        if re.search(r"mã\s*sản\s*phẩm", k, re.I):
            code = specs[k]
            break

    # Base file name
    parts_for_name = [p for p in [code, title] if p]
    fname_base = slugify(" ".join(parts_for_name)) if parts_for_name else base_name

    # JSON
    json_path = os.path.join(outdir, f"{fname_base}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "url": url,
            "title": title,
            "specs": specs
        }, f, ensure_ascii=False, indent=2)

    # CSV (hai cột: thuoc_tinh, gia_tri)
    csv_path = os.path.join(outdir, f"{fname_base}.csv")
    rows = [{"thuoc_tinh": k, "gia_tri": v} for k, v in specs.items()]
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"✔ Đã lưu: {json_path}")
    print(f"✔ Đã lưu: {csv_path}")

def process_url(url: str, outdir: str):
    print(f"\n>>> Đang xử lý: {url}")
    html = fetch_html(url)
    title, _ = parse_title_and_code(html)
    specs = parse_specs(html)

    if not specs:
        print("⚠ Không tìm thấy mục 'Thông số kỹ thuật'. Có thể nội dung render bằng JavaScript hoặc cấu trúc HTML khác.")
    else:
        # Hợp nhất thêm SKU từ specs vào tiêu đề file nếu có
        write_outputs(base_name=slugify(url.split("/")[-1] or "product"),
                      outdir=outdir, url=url, title=title, specs=specs)

# ============= CLI =============

def read_urls_from_file(path: str) -> List[str]:
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if u and not u.startswith("#"):
                urls.append(u)
    return urls

def main():
    parser = argparse.ArgumentParser(description="Export 'Thông số kỹ thuật' từ trang sản phẩm Sunhouse.")
    parser.add_argument("--url", help="URL trang sản phẩm (1 trang).")
    parser.add_argument("--infile", help="Đường dẫn file chứa danh sách URL (mỗi dòng 1 URL).")
    parser.add_argument("--outdir", default="exports", help="Thư mục xuất file (mặc định: exports).")
    args = parser.parse_args()

    if not args.url and not args.infile:
        parser.error("Cung cấp --url hoặc --infile.")

    urls = []
    if args.url:
        urls.append(args.url)
    if args.infile:
        urls.extend(read_urls_from_file(args.infile))

    # Loại trùng
    urls = list(dict.fromkeys(urls))

    print(f"Tổng URL: {len(urls)} | Output dir: {args.outdir}")
    for u in urls:
        try:
            process_url(u, args.outdir)
        except Exception as e:
            print(f"✖ Lỗi với URL: {u}\n  -> {e}")

if __name__ == "__main__":
    main()
