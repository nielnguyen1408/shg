import argparse, re, unicodedata, html
import pandas as pd
from pathlib import Path

# ===== CẤU HÌNH =====
WANTED = ["Thiết kế", "Công năng", "Tổng quan"]
IMG_EXT = r"(?:jpg|jpeg|png|webp|gif|bmp|tiff|svg)"

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

# ===== REGEX ẢNH =====
HTML_IMG_REL = re.compile(
    rf"""(?ix)<img[^>]+src\s*=\s*["']?(?P<url>[^"'>]+?\.(?:{IMG_EXT})(?:\?[^\s"'>]*)?)["']?[^>]*>"""
)
MARKDOWN_IMG = re.compile(
    rf"""(?ix)!\[[^\]]*\]\(\s*(<?)(?P<url>[^)\s<>]+?\.(?:{IMG_EXT})(?:\?[^\s)<>]*)?)\s*(?:["'][^"']*["'])?\)"""
)
URL_PATTERN = re.compile(
    rf"""(?ix)(?:(?:https?:)?//|/)[^\s<>"'()]+?\.(?:{IMG_EXT})(?:\?[^\s"'<>)]*)?(?:\#[^\s"'<>)]*)?"""
)

# ===== TIỆN ÍCH =====
VOWELS = "aăâeêioôơuưyAĂÂEÊIOÔƠUƯY"
def strip_accents_lower(s:str)->str:
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
        scored.sort(); return scored[0][1]
    raise SystemExit(f"Không tìm thấy cột tương ứng cho '{wanted_name}'. Các cột hiện có: {cols}")

def html_to_text(s: str) -> str:
    if s is None: return s
    s = html.unescape(str(s))
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(s, "html.parser")
        # bỏ iframe/video nhưng vẫn giữ text xung quanh
        for tag in soup.find_all(["script","style","iframe","video","source"]): tag.decompose()
        for br in soup.find_all("br"): br.replace_with("\n")
        for li in soup.find_all("li"):
            txt = li.get_text(" ", strip=True); li.clear(); li.append(f"- {txt}\n")
        for p in soup.find_all("p"):
            if p.text and not p.text.endswith("\n"): p.append("\n")
        text = soup.get_text(separator=" ", strip=True)
    except Exception:
        text = re.sub(r"(?i)<br\s*/?>", "\n", s)
        text = re.sub(r"(?is)<li[^>]*>(.*?)</li>", lambda m: "- "+re.sub(r"<.*?>"," ",m.group(1))+"\n", text)
        text = re.sub(r"(?is)<p[^>]*>(.*?)</p>", lambda m: re.sub(r"<.*?>"," ",m.group(1))+"\n", text)
        text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"[\u00A0\t]+", " ", text)     # nbsp/tab -> space
    text = re.sub(r"\s*[-–—]\s*", " – ", text)   # dash chuẩn
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()

def fix_numbers_units(s:str)->str:
    # 1.5l / 1 . 5 l -> 1.5L
    s = re.sub(r"(\d)\s*([.,])\s*(\d)", r"\1\2\3", s)
    s = re.sub(r"(\d)(?:\s*[lL])\b", r"\1L", s)  # 5l -> 5L
    # dải số: 4 - 6 -> 4 – 6
    s = re.sub(r"(\d)\s*[-]\s*(\d)", r"\1 – \2", s)
    return s

def fix_intra_word_spaces_once(s:str)->str:
    # join trước phụ âm cuối ng/nh/ch/c/m/n/t/p: "lò ng"->"lòng", "cá ch"->"cách"
    s = re.sub(rf"([A-Za-zÀ-ỹđĐ])\s+(ng|nh|ch|c|m|n|t|p)\b", r"\1\2", s)
    # join nguyên âm bị tách với i/u/y đơn: "lâ u"->"lâu", "ngoà i"->"ngoài"
    s = re.sub(rf"([{VOWELS}])\s+([iuyIUY])\b", r"\1\2", s)
    # join chữ + dấu câu dính sai: "đ&uacute; ng," đã thành "đúng ," -> "đúng,"
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    # gọn khoảng trắng
    s = re.sub(r"[ \t]+", " ", s)
    return s

def normalize_vietnamese(text: str) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)): return text
    s = html_to_text(str(text))
    s = unicodedata.normalize("NFC", s)
    s = fix_numbers_units(s)

    # Thay thế phổ biến (nhiều vòng)
    for _ in range(2):
        for pattern, repl in COMMON_FIXES.items():
            s = re.sub(pattern, repl, s, flags=re.IGNORECASE)

    # Vá khoảng trắng trong từ (lặp cho đến khi ổn định hoặc tối đa 6 vòng)
    for _ in range(6):
        new_s = fix_intra_word_spaces_once(s)
        if new_s == s: break
        s = new_s

    # Chuẩn dấu câu và viết hoa đầu câu (giữ newline)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"([,.;:!?])(?!\s|$)", r"\1 ", s)
    parts = re.split(r"([.?!]\s+|\n+)", s)
    out = []
    for i, seg in enumerate(parts):
        if i % 2 == 0:
            seg = seg.strip()
            if seg:
                seg = seg[0].upper() + seg[1:] if len(seg) > 1 else seg.upper()
            out.append(seg)
        else:
            out.append(seg)
    s = "".join(out)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def extract_image_urls(raw: str) -> list[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)): return []
    s = str(raw)
    urls = []
    urls += [m.group("url") for m in MARKDOWN_IMG.finditer(s)]
    urls += [m.group("url") for m in HTML_IMG_REL.finditer(s)]
    urls += URL_PATTERN.findall(s)
    cleaned = []
    for u in urls:
        u = html.unescape(u).replace(" ", "")
        if u.startswith("//"): u = "https:" + u
        cleaned.append(u)
    # dedup
    seen, out = set(), []
    for u in cleaned:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

# ===== MAIN =====
def main():
    ap = argparse.ArgumentParser(description="Làm sạch TV + gỡ HTML + vá khoảng trắng + trích ảnh (Thiết kế/Công năng/Tổng quan).")
    ap.add_argument("input", help="Đường dẫn file Excel đầu vào (.xlsx)")
    ap.add_argument("--out-clean", default=None, help="File Excel sạch (mặc định: *_clean.xlsx)")
    ap.add_argument("--out-images", default=None, help="CSV ảnh (mặc định: *_images.csv)")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists(): raise SystemExit(f"Không tìm thấy file: {in_path}")

    print("ℹ Đang đọc sheet đầu tiên …")
    df = pd.read_excel(in_path, sheet_name=0, engine="openpyxl", dtype=str)

    # Tự dò cột mục tiêu (có thể thiếu 1-2 cột, sẽ bỏ qua)
    col_map = {}
    for w in WANTED:
        try:
            col_map[w] = best_match_column(df, w)
        except SystemExit as e:
            print(f"⚠ {e}. Bỏ qua '{w}'.")
    if not col_map: raise SystemExit("Không dò được cột mục tiêu nào.")

    print(f"✔ Khớp cột: {col_map}")

    # Làm sạch cột
    df_clean = df.copy()
    for w, col in col_map.items():
        df_clean[col] = df_clean[col].apply(normalize_vietnamese)

    # Trích ảnh từ dữ liệu gốc (trước khi strip HTML) để không mất URL
    rows = []
    for idx, row in df.iterrows():
        for w, col in col_map.items():
            urls = extract_image_urls(row.get(col))
            if urls:
                rows.append({
                    "row_index_excel": int(idx) + 2,  # +2 vì header = dòng 1
                    "column": col,
                    "count": len(urls),
                    "first_image": urls[0],
                    "image_urls": " | ".join(urls),
                })
    images_df = pd.DataFrame(rows, columns=["row_index_excel","column","count","first_image","image_urls"])

    out_clean = args.out_clean or in_path.with_name(in_path.stem + "_clean.xlsx")
    out_images = args.out_images or in_path.with_name(in_path.stem + "_images.csv")
    df_clean.to_excel(out_clean, index=False, engine="openpyxl")
    images_df.to_csv(out_images, index=False, encoding="utf-8-sig")

    print(f"✔ Đã lưu file sạch: {out_clean}")
    print(f"✔ Đã lưu danh sách ảnh: {out_images}")

if __name__ == "__main__":
    main()
