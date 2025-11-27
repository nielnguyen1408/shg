#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vn_clean_and_split4.py

Bước 1:
- Sửa lỗi tiếng Việt bên trong HTML (giữ cấu trúc <h1..h6>, <p>, <br>, <ul><li>..., <img>...)

Bước 2:
- Xuất 4 file:
  1) *_clean.xlsx               : bản đã chỉnh sửa (giữ nguyên cột, chỉ sửa text trong HTML)
  2) *_tongquan_chunks.xlsx     : chỉ cột "Tổng quan", tách thành nhiều phần theo ảnh
  3) *_thietke_chunks.xlsx      : chỉ cột "Thiết kế", tách theo ảnh
  4) *_congnang_chunks.xlsx     : chỉ cột "Công năng", tách theo ảnh

Yêu cầu: Python 3.9+ ; pip install pandas openpyxl beautifulsoup4
"""

import argparse, re, unicodedata, html, sys
from pathlib import Path
from typing import List, Dict, Optional, Iterable
import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag, Comment, CData

# ================= CẤU HÌNH =================
TARGET_COLS = ["Tổng quan", "Thiết kế", "Công năng"]
HEADING_TAGS = {"h1","h2","h3","h4","h5","h6"}

# Cột SKU đoán tự động (nếu có)
SKU_CANDIDATES = [
    "Mã hàng (SKU)", "Mã hàng", "SKU", "Mã sản phẩm", "Mã SP",
    "Product code", "Product Code", "Code", "Mã"
]
PARENT_SKU_CANDIDATES = [
    "Thuộc mã hàng nào (điền SKU sản phẩm chính, dành cho trường hợp sản phẩm này là một biến thể của sản phẩm chính. Nếu đây là sản phẩm chính thì bỏ trống ô này)",
    "Thuộc mã hàng nào", "Parent SKU", "SKU cha", "Thuộc SKU", "Mã sản phẩm chính"
]

COMMON_FIXES = {
    r"\bthiet ke\b": "thiết kế",
    r"\bcong nang\b": "công năng",
    r"\btong quan\b": "tổng quan",
    r"\bkieu dang\b": "kiểu dáng",
    r"\bkich thuoc\b": "kích thước",
    r"\bbao hanh\b": "bảo hành",
    r"\bdung tich\b": "dung tích",
    r"\bcong suat\b": "công suất",
    r"\binox\b": "inox",
    r"\bnoi com\b": "nồi cơm",
}

# ================= TIỆN ÍCH =================
def is_nonempty(x) -> bool:
    return x is not None and not (isinstance(x, float) and pd.isna(x)) and str(x).strip() != ""

def strip_accents_lower(s: str) -> str:
    if s is None: return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = unicodedata.normalize("NFC", s).lower().strip()
    return re.sub(r"\s+", " ", s)

def best_match_column(df: pd.DataFrame, wanted_name: str) -> Optional[str]:
    # match chính xác
    if wanted_name in df.columns:
        return wanted_name
    # match bỏ dấu + lower
    wn = strip_accents_lower(wanted_name)
    norm_cols = {c: strip_accents_lower(c) for c in df.columns}
    for c, cn in norm_cols.items():
        if cn == wn: return c
    # heuristic: chứa các từ
    wtokens = wn.split()
    scored = [(abs(len(cn)-len(wn)), c) for c, cn in norm_cols.items() if all(t in cn for t in wtokens)]
    if scored:
        scored.sort()
        return scored[0][1]
    return None

def find_any_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns: return name
    # gần đúng
    for name in candidates:
        c = best_match_column(df, name)
        if c: return c
    # heuristic
    for c in df.columns:
        lc = strip_accents_lower(c)
        if "sku" in lc: return c
    return None

# -------- Sửa tiếng Việt trong text node, giữ HTML --------
def fix_numbers_units(s: str) -> str:
    s = re.sub(r"(\d)\s*([.,])\s*(\d)", r"\1\2\3", s)  # 1 , 5 -> 1,5
    s = re.sub(r"(\d)(?:\s*[lL])\b", r"\1L", s)       # 2 l -> 2L
    s = re.sub(r"(\d)\s*[-]\s*(\d)", r"\1 – \2", s)   # 1 - 2 -> 1 – 2
    return s

def fix_intra_word_spaces_once(s: str) -> str:
    s = re.sub(rf"([A-Za-zÀ-ỹđĐ])\s+(ng|nh|ch|c|m|n|t|p)\b", r"\1\2", s)
    s = re.sub(rf"([aăâeêioôơuưyAĂÂEÊIOÔƠUƯY])\s+([iuyIUY])\b", r"\1\2", s)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s

def clean_text_keep_html_textnode(text: str) -> str:
    if text is None: return text
    s = unicodedata.normalize("NFC", text)
    s = fix_numbers_units(s)
    for _ in range(2):
        for pattern, repl in COMMON_FIXES.items():
            s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    for _ in range(4):
        new_s = fix_intra_word_spaces_once(s)
        if new_s == s: break
        s = new_s
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"([,.;:!?])(?!\s|$)", r"\1 ", s)
    return s

def normalize_html_preserve_structure(raw_html: str) -> str:
    """Sửa lỗi TV trong text nodes, giữ nguyên thẻ HTML."""
    if raw_html is None or (isinstance(raw_html, float) and pd.isna(raw_html)): return raw_html
    try:
        soup = BeautifulSoup(str(raw_html), "html.parser")
        skip_tags = {"script", "style", "iframe", "video", "audio", "source"}
        for el in soup.descendants:
            if isinstance(el, (Comment, CData)):  # bỏ qua
                continue
            if isinstance(el, NavigableString):
                parent = el.parent.name if el.parent else ""
                if parent in skip_tags:
                    continue
                # nếu text giống URL trong <a>, tránh chỉnh
                if parent == "a" and re.search(r"https?://", str(el)):
                    continue
                cleaned = clean_text_keep_html_textnode(str(el))
                if cleaned != str(el):
                    el.replace_with(cleaned)
        return str(soup)
    except Exception:
        # Fallback: vẫn chỉnh nhẹ text mà không strip thẻ
        return clean_text_keep_html_textnode(str(raw_html))

# -------- Chia chunk theo ảnh (ảnh thuộc chunk trước nó), heading bắt đầu phần mới nếu đang có nội dung --------
def html_chunks_by_image_and_heading(raw_html: str) -> List[str]:
    if not is_nonempty(raw_html):
        return []
    soup = BeautifulSoup(str(raw_html), "html.parser")
    body_nodes: List = list(soup.contents)
    if len(body_nodes)==1 and isinstance(body_nodes[0], Tag) and body_nodes[0].name in ("html","body"):
        body_nodes = list(body_nodes[0].contents)

    chunks: List[str] = []
    buf: List[str] = []

    def flush():
        if buf:
            chunks.append("".join(buf).strip())
            buf.clear()

    def serialize(node) -> str:
        return str(node)

    def walk(nodes: Iterable):
        for node in nodes:
            if isinstance(node, (Comment, CData)):  # bỏ
                continue
            if isinstance(node, NavigableString):
                txt = str(node)
                if txt:
                    buf.append(txt)
                continue
            if isinstance(node, Tag):
                # Heading: nếu đã có nội dung trong buf thì kết thúc phần trước rồi thêm heading
                if node.name in HEADING_TAGS and any(f.strip() for f in buf):
                    flush()
                    buf.append(serialize(node))
                    continue
                if node.name == "img":
                    buf.append(serialize(node))
                    flush()
                    continue
                # Block khác: mở tag, duyệt con, đóng tag (giữ nguyên thuộc tính)
                if node.contents:
                    open_tag = f"<{node.name}"
                    for k, v in node.attrs.items():
                        if v is True:
                            open_tag += f' {k}'
                        else:
                            open_tag += f' {k}="{html.escape(str(v), quote=True)}"'
                    open_tag += ">"
                    buf.append(open_tag)
                    walk(node.contents)
                    buf.append(f"</{node.name}>")
                else:
                    buf.append(serialize(node))

    walk(body_nodes)
    flush()

    # loại phần rỗng
    return [c for c in chunks if c and c.strip("<> \n\t\r")]

def extract_img_urls(html_chunk: str) -> List[str]:
    if not html_chunk: return []
    IMG_SRC = re.compile(r"""<img[^>]+src\s*=\s*["']?([^"'>\s]+)""", re.IGNORECASE)
    urls, seen = [], set()
    for m in IMG_SRC.finditer(html_chunk):
        u = m.group(1).strip()
        if u.startswith("//"): u = "https:" + u
        if u not in seen:
            seen.add(u); urls.append(u)
    return urls

# ================= MAIN FLOW =================
def process(input_path: Path, sheet_kw: Optional[str|int]):
    # Đọc sheet
    if sheet_kw is None:
        df = pd.read_excel(input_path, sheet_name=0, engine="openpyxl", dtype=str)
    else:
        try:
            idx = int(sheet_kw)
            df = pd.read_excel(input_path, sheet_name=idx, engine="openpyxl", dtype=str)
        except ValueError:
            df = pd.read_excel(input_path, sheet_name=sheet_kw, engine="openpyxl", dtype=str)

    # Map 3 cột đích
    col_map: Dict[str, str] = {}
    for name in TARGET_COLS:
        c = best_match_column(df, name)
        if c: col_map[name] = c
    if not col_map:
        sys.exit(f"Không tìm thấy các cột mục tiêu {TARGET_COLS}. Hãy kiểm tra tên cột.")

    # Tìm SKU / Parent SKU nếu có
    sku_col = find_any_column(df, SKU_CANDIDATES)
    parent_sku_col = find_any_column(df, PARENT_SKU_CANDIDATES)

    # ---- Bước 1: Clean giữ HTML ----
    df_clean = df.copy()
    for logical, real_col in col_map.items():
        df_clean[real_col] = df_clean[real_col].apply(normalize_html_preserve_structure)

    # Lưu file clean
    out_clean = input_path.with_name(input_path.stem + "_clean.xlsx")
    df_clean.to_excel(out_clean, index=False, engine="openpyxl")

    # ---- Bước 2: Xuất 3 file chunk theo cột ----
    def make_chunk_df(target_logical_name: str) -> pd.DataFrame:
        real_col = col_map.get(target_logical_name)
        if not real_col:
            # Nếu không có cột này trong file, trả DataFrame rỗng với schema chuẩn
            return pd.DataFrame(columns=[
                "source_row_excel","SKU","column_name","part_index","chunk_html","chunk_text","first_image_url","all_image_urls"
            ])

        rows = []
        for ridx, row in df_clean.iterrows():
            raw_html = row.get(real_col)
            chunks = html_chunks_by_image_and_heading(raw_html)
            # SKU: ưu tiên Parent
            sku_val = ""
            if parent_sku_col and is_nonempty(row.get(parent_sku_col)):
                sku_val = str(row.get(parent_sku_col)).strip()
            elif sku_col and is_nonempty(row.get(sku_col)):
                sku_val = str(row.get(sku_col)).strip()

            if not chunks:
                rows.append({
                    "source_row_excel": int(ridx)+2,
                    "SKU": sku_val,
                    "column_name": target_logical_name,
                    "part_index": 1,
                    "chunk_html": "" if raw_html is None else str(raw_html),
                    "chunk_text": "",
                    "first_image_url": "",
                    "all_image_urls": "",
                })
                continue

            for i, ch in enumerate(chunks, start=1):
                txt = BeautifulSoup(ch, "html.parser").get_text(separator=" ", strip=True)
                imgs = extract_img_urls(ch)
                rows.append({
                    "source_row_excel": int(ridx)+2,
                    "SKU": sku_val,
                    "column_name": target_logical_name,
                    "part_index": i,
                    "chunk_html": ch,
                    "chunk_text": txt,
                    "first_image_url": imgs[0] if imgs else "",
                    "all_image_urls": ";".join(imgs),
                })
        return pd.DataFrame(rows, columns=[
            "source_row_excel","SKU","column_name","part_index","chunk_html","chunk_text","first_image_url","all_image_urls"
        ])

    df_tongquan = make_chunk_df("Tổng quan")
    df_thietke  = make_chunk_df("Thiết kế")
    df_congnang = make_chunk_df("Công năng")

    out_tq = input_path.with_name(input_path.stem + "_tongquan_chunks.xlsx")
    out_tk = input_path.with_name(input_path.stem + "_thietke_chunks.xlsx")
    out_cn = input_path.with_name(input_path.stem + "_congnang_chunks.xlsx")

    df_tongquan.to_excel(out_tq, index=False, engine="openpyxl")
    df_thietke.to_excel(out_tk, index=False, engine="openpyxl")
    df_congnang.to_excel(out_cn, index=False, engine="openpyxl")

    print("✔ Hoàn tất:")
    print(f"  1) Clean  : {out_clean}")
    print(f"  2) Tổng quan chunks : {out_tq}")
    print(f"  3) Thiết kế  chunks : {out_tk}")
    print(f"  4) Công năng chunks : {out_cn}")

def main():
    ap = argparse.ArgumentParser(
        description="Chỉnh TV giữ HTML + tách theo ảnh 3 cột (Tổng quan/Thiết kế/Công năng) thành 4 file."
    )
    ap.add_argument("input", help="File Excel đầu vào (.xlsx)")
    ap.add_argument("--sheet", default=None, help="Tên hoặc index sheet (mặc định: sheet đầu)")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"Không tìm thấy file: {in_path}")

    process(in_path, args.sheet)

if __name__ == "__main__":
    main()
