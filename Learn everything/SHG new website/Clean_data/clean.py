#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_preserve_html.py
- Sửa lỗi TV bên trong HTML (giữ nguyên thẻ h1–h6, p, br, ul/li, a, img…)
- Không strip HTML; chỉ chỉnh nội dung text node.
- Xuất danh sách ảnh (mỗi URL 1 dòng), kèm SKU/Parent SKU và vị trí.
"""

import argparse, re, unicodedata, html, sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pandas as pd

# ========= CẤU HÌNH =========
DEFAULT_WANTED = ["Thiết kế", "Công năng", "Tổng quan"]
IMG_EXT = r"(?:jpg|jpeg|png|webp|gif|bmp|tiff|svg)"

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

# ========= REGEX ẢNH =========
HTML_IMG_REL = re.compile(
    rf"""(?ix)<img[^>]+src\s*=\s*["']?(?P<url>[^"'>]+?\.(?:{IMG_EXT})(?:\?[^\s"'>]*)?)["']?[^>]*>"""
)
MARKDOWN_IMG = re.compile(
    rf"""(?ix)!\[[^\]]*\]\(\s*(<?)(?P<url>[^)\s<>]+?\.(?:{IMG_EXT})(?:\?[^\s)<>]*)?)\s*(?:["'][^"']*["'])?\)"""
)
URL_PATTERN = re.compile(
    rf"""(?ix)(?:(?:https?:)?//|/)[^\s<>"'()]+?\.(?:{IMG_EXT})(?:\?[^\s"'<>)]*)?(?:\#[^\s"'<>)]*)?"""
)

# ========= TIỆN ÍCH =========
def strip_accents_lower(s: str) -> str:
    if s is None: return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = unicodedata.normalize("NFC", s).lower().strip()
    return re.sub(r"\s+", " ", s)

def best_match_column(df: pd.DataFrame, wanted_name: str) -> str:
    cols = list(df.columns)
    norm_cols = {c: strip_accents_lower(c) for c in cols}
    wn = strip_accents_lower(wanted_name)
    if wanted_name in cols: return wanted_name
    for c, cn in norm_cols.items():
        if cn == wn: return c
    wtokens = wn.split()
    scored = [(abs(len(cn)-len(wn)), c) for c, cn in norm_cols.items() if all(t in cn for t in wtokens)]
    if scored:
        scored.sort()
        return scored[0][1]
    raise SystemExit(f"Không thấy cột '{wanted_name}'. Các cột: {cols}")

def find_any_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns: return name
    for name in candidates:
        try:
            return best_match_column(df, name)
        except SystemExit:
            continue
    # fallback heuristic
    norm_cols = {c: strip_accents_lower(c) for c in df.columns}
    scored: List[Tuple[int, str]] = []
    for c, cn in norm_cols.items():
        score = 0
        if "sku" in cn: score += 3
        if "ma" in cn: score += 1
        if any(x in cn for x in ["hang", "san pham", "sp"]): score += 1
        if score >= 3: scored.append((-score, c))
    if scored:
        scored.sort()
        return scored[0][1]
    return None

def fix_numbers_units(s: str) -> str:
    # Chỉ sửa trong text node; không đụng tới HTML
    s = re.sub(r"(\d)\s*([.,])\s*(\d)", r"\1\2\3", s)  # 1 , 5 -> 1,5
    s = re.sub(r"(\d)(?:\s*[lL])\b", r"\1L", s)       # 2 l -> 2L
    s = re.sub(r"(\d)\s*[-]\s*(\d)", r"\1 – \2", s)   # 1 - 2 -> 1 – 2
    return s

def fix_intra_word_spaces_once(s: str) -> str:
    # Thu gọn lỗi tách âm trong tiếng Việt, tránh phá layout.
    s = re.sub(rf"([A-Za-zÀ-ỹđĐ])\s+(ng|nh|ch|c|m|n|t|p)\b", r"\1\2", s)
    s = re.sub(rf"([aăâeêioôơuưyAĂÂEÊIOÔƠUƯY])\s+([iuyIUY])\b", r"\1\2", s)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    # Không convert \n vì \n trong HTML thường không quyết định xuống dòng; br/p sẽ giữ layout
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
    # khoảng trắng trước dấu câu + 1 space sau dấu câu (nếu không có thẻ)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"([,.;:!?])(?!\s|$)", r"\1 ", s)
    return s

def normalize_html_preserve_structure(raw_html: str) -> str:
    """Sửa lỗi TV trong text nodes, giữ nguyên thẻ HTML."""
    if raw_html is None or (isinstance(raw_html, float) and pd.isna(raw_html)): return raw_html
    from bs4 import BeautifulSoup, NavigableString, Comment, CData
    try:
        soup = BeautifulSoup(str(raw_html), "html.parser")

        skip_tags = {"script", "style", "iframe", "video", "audio", "source"}
        for el in soup.descendants:
            # Chỉ xử lý text nodes
            if isinstance(el, NavigableString) and not isinstance(el, (Comment, CData)):
                parent = el.parent.name if el.parent else ""
                if parent in skip_tags:
                    continue
                # Bỏ qua text nằm bên trong <a> nếu là URL (tránh bể link hiển thị)
                if parent == "a" and re.search(r"https?://", str(el)):
                    continue
                cleaned = clean_text_keep_html_textnode(str(el))
                if cleaned != str(el):
                    el.replace_with(cleaned)
        # Không tự thêm newline hay wrap — để nguyên cấu trúc
        return str(soup)
    except Exception:
        # Fallback: nếu HTML lỗi, vẫn sửa text “nhẹ” bằng regex nhưng không strip thẻ
        return clean_text_keep_html_textnode(str(raw_html))

def extract_image_urls(raw: str) -> List[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)): return []
    s = str(raw)
    urls: List[str] = []
    urls += [m.group("url") for m in MARKDOWN_IMG.finditer(s)]
    urls += [m.group("url") for m in HTML_IMG_REL.finditer(s)]
    urls += URL_PATTERN.findall(s)
    # chuẩn hóa & dedup
    seen, out = set(), []
    for u in urls:
        u = html.unescape(u).replace(" ", "")
        if u.startswith("//"): u = "https:" + u
        if u not in seen:
            seen.add(u); out.append(u)
    return out

def is_nonempty(x) -> bool:
    return x is not None and not (isinstance(x, float) and pd.isna(x)) and str(x).strip() != ""

# ========= MAIN =========
def main():
    ap = argparse.ArgumentParser(
        description="Sửa lỗi tiếng Việt bên trong HTML (giữ nguyên thẻ) + trích URL ảnh."
    )
    ap.add_argument("input", help="File Excel đầu vào (.xlsx)")
    ap.add_argument("--sheet", default=None, help="Tên hoặc index sheet (mặc định: sheet đầu)")
    ap.add_argument("--cols", nargs="*", default=None,
                    help="Danh sách cột HTML cần xử lý. Mặc định: 'Thiết kế' 'Công năng' 'Tổng quan'")
    ap.add_argument("--out-clean", default=None, help="File Excel output (mặc định: *_clean.xlsx)")
    ap.add_argument("--out-images", default=None, help="CSV ảnh (mặc định: *_images.csv)")
    ap.add_argument("--unique-per-sku", action="store_true",
                    help="Chống trùng ảnh theo SKU (1 URL/ SKU).")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"Không tìm thấy file: {in_path}")

    # Đọc sheet
    sheet_kw = args.sheet
    if sheet_kw is None:
        df = pd.read_excel(in_path, sheet_name=0, engine="openpyxl", dtype=str)
    else:
        try:
            sheet_arg = int(sheet_kw)
            df = pd.read_excel(in_path, sheet_name=sheet_arg, engine="openpyxl", dtype=str)
        except ValueError:
            df = pd.read_excel(in_path, sheet_name=sheet_kw, engine="openpyxl", dtype=str)

    # Cột đích
    wanted = args.cols if args.cols else DEFAULT_WANTED
    col_map: Dict[str, str] = {}
    for w in wanted:
        try:
            col_map[w] = best_match_column(df, w)
        except SystemExit as e:
            print(f"⚠ {e}. Bỏ qua '{w}'.")

    if not col_map:
        sys.exit("Không dò được cột cần xử lý. Dùng --cols để chỉ định chính xác.")

    # SKU & Parent SKU
    sku_col = find_any_column(df, SKU_CANDIDATES)
    parent_sku_col = find_any_column(df, PARENT_SKU_CANDIDATES)
    print(f"✔ Cột HTML: {col_map}")
    print(f"✔ SKU: {sku_col} | Parent SKU: {parent_sku_col}")

    # Xử lý — GIỮ NGUYÊN HTML, chỉ sửa text nodes
    df_clean = df.copy()
    for _, col in col_map.items():
        df_clean[col] = df_clean[col].apply(normalize_html_preserve_structure)

    # Trích ảnh
    rows = []
    seen_by_sku = set()  # (sku, url)
    for idx, row in df.iterrows():
        # SKU ưu tiên Parent
        sku_val = ""
        if parent_sku_col and is_nonempty(row.get(parent_sku_col)):
            sku_val = str(row.get(parent_sku_col)).strip()
        elif sku_col and is_nonempty(row.get(sku_col)):
            sku_val = str(row.get(sku_col)).strip()

        for _, col in col_map.items():
            urls = extract_image_urls(row.get(col))
            for k, u in enumerate(urls, start=1):
                if args.unique_per_sku and sku_val:
                    key = (sku_val, u)
                    if key in seen_by_sku:
                        continue
                    seen_by_sku.add(key)
                rows.append({
                    "row_index_excel": int(idx) + 2,  # header dòng 1
                    "SKU": sku_val,
                    "column": col,
                    "image_index": k,
                    "image_url": u,
                })

    images_df = pd.DataFrame(rows, columns=["row_index_excel", "SKU", "column", "image_index", "image_url"])

    out_clean = args.out_clean or in_path.with_name(in_path.stem + "_clean.xlsx")
    out_images = args.out_images or in_path.with_name(in_path.stem + "_images.csv")
    df_clean.to_excel(out_clean, index=False, engine="openpyxl")
    images_df.to_csv(out_images, index=False, encoding="utf-8-sig")

    print(f"✔ Đã lưu: {out_clean}")
    print(f"✔ Đã lưu: {out_images}")
    if args.unique_per_sku:
        print("ℹ Đã bật chống trùng ảnh theo SKU.")

if __name__ == "__main__":
    main()
