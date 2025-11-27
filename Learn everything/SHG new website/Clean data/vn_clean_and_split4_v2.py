#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vn_clean_and_split4_v3.py

Bước 1:
- Sửa lỗi TV trong text node (giữ cấu trúc HTML), gộp ""..."" -> "..."
- XÓA toàn bộ inline style="" trong mọi thẻ
- Không sửa nội dung thuộc tính (src/href/...), chỉ sửa text node
- Cho phép sửa text fallback bên trong <iframe> (nếu có)

Bước 2:
- Xuất 4 file:
  1) *_clean.xlsx                : bản đã chỉnh sửa (giữ nguyên cột; bỏ style; fix nháy trong text)
  2) *_tongquan_chunks.xlsx      : chỉ cột "Tổng quan", tách theo ảnh
  3) *_thietke_chunks.xlsx       : chỉ cột "Thiết kế", tách theo ảnh
  4) *_congnang_chunks.xlsx      : chỉ cột "Công năng", tách theo ảnh

Доп:
- Khi tách, ảnh <img> có src tương đối sẽ được absolutize với --base-url (mặc định https://sunhouse.com.vn)
- Khi tách, <iframe> được bỏ khỏi HTML chunk; link YouTube được đưa vào cột youtube_links
"""

import argparse, re, unicodedata, html, sys
from pathlib import Path
from typing import List, Dict, Optional, Iterable
from urllib.parse import urlparse, parse_qs, urljoin
import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag, Comment, CData

# ================= CẤU HÌNH =================
TARGET_COLS = ["Tổng quan", "Thiết kế", "Công năng"]
HEADING_TAGS = {"h1","h2","h3","h4","h5","h6"}
VOID_TAGS = {"img","br","hr","input","source","meta","link","area","col","embed","param","track","wbr"}

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
    if wanted_name in df.columns:
        return wanted_name
    wn = strip_accents_lower(wanted_name)
    norm_cols = {c: strip_accents_lower(c) for c in df.columns}
    for c, cn in norm_cols.items():
        if cn == wn: return c
    wtokens = wn.split()
    scored = [(abs(len(cn)-len(wn)), c) for c, cn in norm_cols.items() if all(t in cn for t in wtokens)]
    if scored:
        scored.sort()
        return scored[0][1]
    return None

def find_any_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns: return name
    for name in candidates:
        c = best_match_column(df, name)
        if c: return c
    for c in df.columns:
        if "sku" in strip_accents_lower(c): return c
    return None

# --------- TEXT CLEANING (chỉ text node) ---------
def fix_numbers_units(s: str) -> str:
    s = re.sub(r"(\d)\s*([.,])\s*(\d)", r"\1\2\3", s)  # 1 , 5 -> 1,5
    s = re.sub(r"(\d)(?:\s*[lL])\b", r"\1L", s)       # 2 l -> 2L
    s = re.sub(r"(\d)\s*[-]\s*(\d)", r"\1 – \2", s)   # 1 - 2 -> 1 – 2
    return s

# Gộp ""..."" -> "..."
_DBLQUOTE_PAIR = re.compile(r'""\s*([^"]*?)\s*""')

def collapse_double_quotes(s: str) -> str:
    for _ in range(3):
        ns = _DBLQUOTE_PAIR.sub(r'"\1"', s)
        if ns == s: break
        s = ns
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
    s = collapse_double_quotes(s)
    for _ in range(2):
        for pattern, repl in COMMON_FIXES.items():
            s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    for _ in range(4):
        ns = fix_intra_word_spaces_once(s)
        if ns == s: break
        s = ns
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"([,.;:!?])(?!\s|$)", r"\1 ", s)
    return s

def remove_styles_in_subtree(soup_or_tag: Tag):
    for t in (soup_or_tag.find_all(True) if hasattr(soup_or_tag, "find_all") else []):
        if "style" in t.attrs:
            del t.attrs["style"]
    return soup_or_tag

def normalize_html_preserve_structure(raw_html: str) -> str:
    """Sửa text node + gộp ""..."" -> "..." và loại bỏ toàn bộ style="" trong HTML."""
    if raw_html is None or (isinstance(raw_html, float) and pd.isna(raw_html)): return raw_html
    try:
        soup = BeautifulSoup(str(raw_html), "html.parser")
        # 1) Bỏ inline style
        remove_styles_in_subtree(soup)
        # 2) Sửa các text node (kể cả fallback text trong <iframe>)
        skip_tags = {"script", "style", "video", "audio", "source"}  # không skip iframe để xử lý text fallback
        for el in soup.descendants:
            if isinstance(el, (Comment, CData)):
                continue
            if isinstance(el, NavigableString):
                parent = el.parent.name if el.parent else ""
                if parent in skip_tags:
                    continue
                if parent == "a" and re.search(r"https?://", str(el)):
                    continue
                cleaned = clean_text_keep_html_textnode(str(el))
                if cleaned != str(el):
                    el.replace_with(cleaned)
        return str(soup)
    except Exception:
        return collapse_double_quotes(clean_text_keep_html_textnode(str(raw_html)))

# --------- URL UTILS ---------
def absolutize(u: str, base_url: str) -> str:
    if not u: return u
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if re.match(r"^(?:https?|data|mailto|tel|javascript):", u, flags=re.I):
        return u
    # còn lại: tương đối => join vào base
    try:
        return urljoin(base_url.rstrip("/") + "/", u)
    except Exception:
        return u

def youtube_watch_url(src: str) -> Optional[str]:
    if not src: return None
    try:
        p = urlparse(src)
        host = (p.netloc or "").lower()
        path = (p.path or "")
        if "youtube.com" in host or "youtube-nocookie.com" in host:
            if path.startswith("/embed/"):
                vid = path.split("/embed/")[1].split("/")[0]
                if vid: return f"https://www.youtube.com/watch?v={vid}"
            if path == "/watch":
                v = parse_qs(p.query).get("v", [None])[0]
                if v: return f"https://www.youtube.com/watch?v={v}"
        if host.endswith("youtu.be"):
            vid = path.strip("/").split("/")[0]
            if vid: return f"https://www.youtube.com/watch?v={vid}"
    except Exception:
        pass
    return None

# --------- CHUNKING ---------
def strip_styles_html_fragment(fragment: str) -> str:
    s = BeautifulSoup(fragment, "html.parser")
    remove_styles_in_subtree(s)
    return str(s)

def html_chunks_by_image_and_heading(raw_html: str, base_url: str) -> List[Dict]:
    """
    Trả về list các dict:
      { "html": chunk_html, "youtube_links": [..] }
    - Ảnh (<img>) nằm trong chunk và khi gặp <img> thì KẾT THÚC chunk
    - Heading (h1..h6) bắt đầu chunk mới nếu buf đã có nội dung
    - <iframe>: không render vào chunk_html; trích youtube link vào youtube_links
    - Mọi thẻ render KHÔNG có style=""; ảnh sẽ được absolutize src theo base_url
    """
    if not is_nonempty(raw_html):
        return []

    soup = BeautifulSoup(str(raw_html), "html.parser")
    remove_styles_in_subtree(soup)

    body_nodes: List = list(soup.contents)
    if len(body_nodes)==1 and isinstance(body_nodes[0], Tag) and body_nodes[0].name in ("html","body"):
        body_nodes = list(body_nodes[0].contents)

    chunks: List[Dict] = []
    buf: List[str] = []
    cur_yt: List[str] = []

    def flush():
        nonlocal buf, cur_yt
        if buf or cur_yt:
            chunks.append({"html": "".join(buf).strip(), "youtube_links": list(cur_yt)})
            buf, cur_yt = [], []

    def render_open_no_style(tag: Tag, base: str) -> str:
        attrs = []
        for k, v in tag.attrs.items():
            if k.lower() == "style":
                continue
            if v is True:
                attrs.append(f"{k}")
            else:
                vv = v
                # chỉnh src/href tương đối -> tuyệt đối
                if tag.name in {"img","source"} and k.lower() == "src":
                    vv = absolutize(str(v), base)
                elif tag.name == "a" and k.lower() == "href":
                    vv = absolutize(str(v), base)
                attrs.append(f'{k}="{html.escape(str(vv), quote=True)}"')
        return f"<{tag.name}{(' ' + ' '.join(attrs)) if attrs else ''}>"

    def render_self_no_style(tag: Tag, base: str) -> str:
        return render_open_no_style(tag, base)  # giữ dạng <img ...>

    def walk(nodes: Iterable):
        nonlocal cur_yt
        for node in nodes:
            if isinstance(node, (Comment, CData)):
                continue

            if isinstance(node, NavigableString):
                txt = clean_text_keep_html_textnode(str(node))
                if txt:
                    buf.append(txt)
                continue

            if isinstance(node, Tag):
                # iframes -> lấy link youtube, KHÔNG render
                if node.name == "iframe":
                    yt = youtube_watch_url(node.get("src", ""))
                    if yt:
                        cur_yt.append(yt)
                    # không render iframe vào HTML chunk
                    continue

                # Heading: nếu đã có nội dung -> ngắt trước
                if node.name in HEADING_TAGS and any(f.strip() for f in buf):
                    flush()
                    buf.append(strip_styles_html_fragment(str(node)))
                    continue

                # thẻ tự đóng
                if node.name in VOID_TAGS:
                    buf.append(render_self_no_style(node, base_url))
                    if node.name == "img":
                        flush()
                    continue

                # thẻ thường
                buf.append(render_open_no_style(node, base_url))
                if node.contents:
                    walk(node.contents)
                buf.append(f"</{node.name}>")

    walk(body_nodes)
    flush()

    # loại phần hoàn toàn rỗng
    return [c for c in chunks if (c["html"] and c["html"].strip("<> \n\t\r")) or c["youtube_links"]]

def extract_img_urls(html_chunk: str, base_url: str) -> List[str]:
    if not html_chunk: return []
    IMG_SRC = re.compile(r"""<img[^>]+src\s*=\s*["']?([^"'>\s]+)""", re.IGNORECASE)
    urls, seen = [], set()
    for m in IMG_SRC.finditer(html_chunk):
        u = m.group(1).strip()
        u = absolutize(u, base_url)
        if u not in seen:
            seen.add(u); urls.append(u)
    return urls

# ================= MAIN FLOW =================
def process(input_path: Path, sheet_kw: Optional[str|int], base_url: str):
    # đọc sheet
    if sheet_kw is None:
        df = pd.read_excel(input_path, sheet_name=0, engine="openpyxl", dtype=str)
    else:
        try:
            idx = int(sheet_kw)
            df = pd.read_excel(input_path, sheet_name=idx, engine="openpyxl", dtype=str)
        except ValueError:
            df = pd.read_excel(input_path, sheet_name=sheet_kw, engine="openpyxl", dtype=str)

    # map cột
    col_map: Dict[str, str] = {}
    for name in TARGET_COLS:
        c = best_match_column(df, name)
        if c: col_map[name] = c
    if not col_map:
        sys.exit(f"Không tìm thấy các cột mục tiêu {TARGET_COLS}. Kiểm tra tên cột.")

    # SKU/Parent SKU nếu có
    sku_col = find_any_column(df, SKU_CANDIDATES)
    parent_sku_col = find_any_column(df, PARENT_SKU_CANDIDATES)

    # ---- B1: Clean giữ HTML + bỏ style + gộp ""..."" ----
    df_clean = df.copy()
    for logical, real_col in col_map.items():
        df_clean[real_col] = df_clean[real_col].apply(normalize_html_preserve_structure)

    out_clean = input_path.with_name(input_path.stem + "_clean.xlsx")
    df_clean.to_excel(out_clean, index=False, engine="openpyxl")

    # ---- B2: Chia 3 file chunk theo ảnh, bỏ iframe, trích YouTube + absolutize ảnh ----
    def make_chunk_df(target_logical_name: str) -> pd.DataFrame:
        real_col = col_map.get(target_logical_name)
        if not real_col:
            return pd.DataFrame(columns=[
                "source_row_excel","SKU","column_name","part_index",
                "chunk_html","chunk_text","first_image_url","all_image_urls","youtube_links"
            ])

        rows = []
        for ridx, row in df_clean.iterrows():
            raw_html = row.get(real_col)
            parts = html_chunks_by_image_and_heading(raw_html, base_url)

            # SKU ưu tiên Parent
            sku_val = ""
            if parent_sku_col and is_nonempty(row.get(parent_sku_col)):
                sku_val = str(row.get(parent_sku_col)).strip()
            elif sku_col and is_nonempty(row.get(sku_col)):
                sku_val = str(row.get(sku_col)).strip()

            if not parts:
                rows.append({
                    "source_row_excel": int(ridx)+2,
                    "SKU": sku_val,
                    "column_name": target_logical_name,
                    "part_index": 1,
                    "chunk_html": "" if raw_html is None else strip_styles_html_fragment(str(raw_html)),
                    "chunk_text": "",
                    "first_image_url": "",
                    "all_image_urls": "",
                    "youtube_links": ""
                })
                continue

            for i, part in enumerate(parts, start=1):
                ch = part["html"]
                yts = part.get("youtube_links", [])
                txt = BeautifulSoup(ch, "html.parser").get_text(separator=" ", strip=True)
                imgs = extract_img_urls(ch, base_url)
                rows.append({
                    "source_row_excel": int(ridx)+2,
                    "SKU": sku_val,
                    "column_name": target_logical_name,
                    "part_index": i,
                    "chunk_html": ch,  # không style, ảnh đã absolutize
                    "chunk_text": txt,
                    "first_image_url": imgs[0] if imgs else "",
                    "all_image_urls": ";".join(imgs),
                    "youtube_links": ";".join(yts)
                })
        return pd.DataFrame(rows, columns=[
            "source_row_excel","SKU","column_name","part_index",
            "chunk_html","chunk_text","first_image_url","all_image_urls","youtube_links"
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
        description="Chỉnh TV giữ HTML + gộp \"\"...\"\" + bỏ style + tách theo ảnh 3 cột; bóc iframe -> link YouTube; absolutize ảnh."
    )
    ap.add_argument("input", help="File Excel đầu vào (.xlsx)")
    ap.add_argument("--sheet", default=None, help="Tên hoặc index sheet (mặc định: sheet đầu)")
    ap.add_argument("--base-url", default="https://sunhouse.com.vn", help="Base URL để cộng vào các đường dẫn ảnh tương đối")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"Không tìm thấy file: {in_path}")

    process(in_path, args.sheet, args.base_url)

#if __name__ == "__main__":
#    main()



# vn_clean_and_split4_v2.py - thêm phần gọi hàm
# --- thay thế phần process_files hiện tại ---
from pathlib import Path

def process_files(paths, sheet=None, base_url="https://sunhouse.com.vn"):
    for p in paths:
        process(Path(p), sheet, base_url)   # <--- GỌI xử lý thật

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="+", help="1 hoặc nhiều file .xlsx")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--base-url", default="https://sunhouse.com.vn")
    a = ap.parse_args()
    process_files(a.input, a.sheet, a.base_url)
