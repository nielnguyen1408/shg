# -*- coding: utf-8 -*-
"""
Ho Chi Minh City (HCMC) Coverage Report Generator

Usage:
    python hcm_coverage_report.py --input "/path/to/input.xlsx" [--output "/path/to/output.xlsx"] [--ward-map "/path/to/ward_map.csv|xlsx"]

Requirements:
    - Python 3.8+
    - pandas
    - xlsxwriter

What it does:
    - Reads all sheets from the input Excel
    - Heuristically detects address and building-name columns
    - Flags rows in HCMC
    - Extracts district (quan/huyen/tp Thu Duc) using both direct patterns and (optional) ward→district dictionary
    - De-duplicates entries by (building_name,address)
    - Exports an Excel report with Summary, DistrictCoverage (all districts listed, zero-filled), RawHCMC

Notes:
    - You can optionally supply a ward map file via --ward-map (CSV or XLSX) with columns: ward,district.
      If omitted, the script still parses addresses that contain both ward and district. Addresses with only ward
      may remain "Khong ro quan/huyen" unless covered by the small built-in seed mapping.
"""

import argparse
import pandas as pd
import re
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import os

# ----------------------------
# Text normalization helpers
# ----------------------------
def strip_accents(s: Optional[str]) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = unicodedata.normalize('NFC', s)
    return s

def norm_text(s: Optional[str]) -> str:
    s = strip_accents(s).lower()
    s = re.sub(r'[\s,;|/]+', ' ', s).strip()
    return s

# ----------------------------
# Column picking heuristics
# ----------------------------
ADDRESS_CANDIDATES_KW = ['địa', 'dia', 'address', 'addr', 'add', 'địa', 'dia chi', 'dia chi', 'location', 'địa chỉ', 'dia_chi', 'diachi']
NAME_CANDIDATES_KW    = ['tòa', 'toa', 'building', 'ten', 'tên', 'site', 'location name', 'property', 'mall', 'project', 'tower', 'asset', 'name']

def pick_col(cols: List[str], candidates_kw: List[str]) -> Optional[str]:
    scores = {}
    for c in cols:
        c_norm = norm_text(c)
        score = 0
        for kw in candidates_kw:
            if kw in c_norm:
                score += len(kw)
        score -= abs(len(c_norm)-10)*0.01
        scores[c] = score
    best = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if best and best[0][1] > 0:
        return best[0][0]
    return None

# ----------------------------
# HCMC district-level units
# ----------------------------
# City-level unit
HCMC_CITY = "Thành phố Hồ Chí Minh"

# Thu Duc City + urban districts + rural districts
HCMC_UNITS = [
    "Thành phố Thủ Đức",
    "Quận 1","Quận 3","Quận 4","Quận 5","Quận 6","Quận 7","Quận 8","Quận 10","Quận 11","Quận 12",
    "Quận Bình Thạnh","Quận Phú Nhuận","Quận Gò Vấp","Quận Tân Bình","Quận Tân Phú","Quận Bình Tân",
    "Huyện Bình Chánh","Huyện Hóc Môn","Huyện Củ Chi","Huyện Nhà Bè","Huyện Cần Giờ"
]

UNITS_NORM = [norm_text(u) for u in HCMC_UNITS]
UNIT_MAP = dict(zip(UNITS_NORM, HCMC_UNITS))

HCMC_TOKENS = [
    'ho chi minh','thanh pho ho chi minh','tp ho chi minh','tp hcm','tphcm','hcm','sai gon','sai gon',
] + UNITS_NORM

# ----------------------------
# Optional: built-in small seed of ward→district for some common cases
# (Highly recommended: supply a full mapping via --ward-map to achieve near-0 "Khong ro quan/huyen")
# ----------------------------
SEED_WARD_TO_DISTRICT = {
    # Thu Duc City (city-level)
    'linh trung':'Thành phố Thủ Đức','linh tay':'Thành phố Thủ Đức','hiep binh chanh':'Thành phố Thủ Đức',
    # District 1
    'ben nghe':'Quận 1','ben thanh':'Quận 1','cau ong lanh':'Quận 1','co giang':'Quận 1','da kao':'Quận 1','nguyen thai binh':'Quận 1','pham ngu lao':'Quận 1','tan dinh':'Quận 1',
    # Binh Thanh
    'ward 1 binh thanh':'Quận Bình Thạnh','phuong 1 binh thanh':'Quận Bình Thạnh','phuong 25':'Quận Bình Thạnh','phuong 26':'Quận Bình Thạnh',
    # Phu Nhuan
    'phu nhuận':'Quận Phú Nhuận', 'phu nhuan':'Quận Phú Nhuận',
    # Tan Binh
    'ward 2 tan binh':'Quận Tân Bình','phuong 2 tan binh':'Quận Tân Bình',
    # Go Vap
    'phuong 5 go vap':'Quận Gò Vấp',
}

# ----------------------------
# Detection helpers
# ----------------------------
def detect_hcm(addr: str) -> bool:
    t = norm_text(addr)
    return any(tok in t for tok in HCMC_TOKENS)

def extract_unit_by_keywords(addr: str) -> Optional[str]:
    """
    Detect district/thu duc/huyen by direct keywords and patterns like
    'quan 1', 'q.1', 'district 1', 'tp thu duc', 'thanh pho thu duc', 'huyen binh chanh', 'h. binh chanh'
    """
    t = norm_text(addr)
    # Direct full-name matching
    for u_norm, u_vn in UNIT_MAP.items():
        if re.search(r'\b'+re.escape(u_norm)+r'\b', t):
            return u_vn

    # Abbreviation patterns
    # District number forms
    m = re.search(r'\b(q|quan|d|district)\.?\s*([0-9]{1,2})\b', t)
    if m:
        num = int(m.group(2))
        if 1 <= num <= 12:
            return f"Quận {num}"

    # Thu Duc City
    if re.search(r'\b(thanh pho|tp)\.?\s*(thu duc|thu duc city)\b', t):
        return "Thành phố Thủ Đức"
    if re.search(r'\bthu duc\b', t):
        # careful: 'thu duc' could be ward names, but commonly refers to the city
        return "Thành phố Thủ Đức"

    # Huyen
    m2 = re.search(r'\b(h|huyen)\.?\s*(binh chanh|hoc mon|cu chi|nha be|can gio)\b', t)
    if m2:
        name = m2.group(2)
        mapping = {
            'binh chanh':'Huyện Bình Chánh','hoc mon':'Huyện Hóc Môn','cu chi':'Huyện Củ Chi','nha be':'Huyện Nhà Bè','can gio':'Huyện Cần Giờ'
        }
        return mapping.get(name)

    return None

def load_ward_map(path: str) -> Dict[str, str]:
    """
    Load ward→district mapping from CSV or XLSX with columns 'ward' and 'district'.
    Returns a dict {normalized_ward: district_label}
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.csv', '.txt']:
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    # Basic sanitization
    cols = {norm_text(c): c for c in df.columns}
    ward_col = cols.get('ward') or cols.get('phuong') or list(df.columns)[0]
    dist_col = cols.get('district') or cols.get('quan') or cols.get('quan/huyen') or list(df.columns)[1]

    mapping = {}
    for _, row in df.iterrows():
        w = norm_text(row[ward_col])
        d = str(row[dist_col]).strip()
        if w:
            mapping[w] = d
    return mapping

def extract_unit_with_wards(addr: str, ward_map: Dict[str, str]) -> Optional[str]:
    """
    Try to get unit via keyword, then via ward_map (when only ward appears).
    Also parse explicit 'phường ... , quận ...' pattern.
    """
    t = norm_text(addr)

    # 1) If both ward and district are in text, prefer district by keywords
    d0 = extract_unit_by_keywords(addr)
    if d0:
        return d0

    # 2) Explicit pattern "phường/xã ... , quận/huyện ..."
    m_exp = re.search(r'\b(p|phuong|xa|thi tran|tt)\.?\s+[a-z0-9\s\-\/]+?,\s*(q|quan|d|district|h|huyen|tp)\.?\s*([a-z0-9\s]+)\b', t)
    if m_exp:
        # Try to resolve the 3rd group into a unit
        tail = m_exp.group(3).strip()
        # Try numeric district
        mnum = re.search(r'\b([0-9]{1,2})\b', tail)
        if mnum:
            n = int(mnum.group(1))
            if 1 <= n <= 12:
                return f"Quận {n}"
        # Try name match against UNIT_MAP
        for u_norm, u_vn in UNIT_MAP.items():
            if re.search(r'\b'+re.escape(u_norm)+r'\b', tail):
                return u_vn

    # 3) Ward-only mapping (when only ward name appears)
    # Look for token after 'phuong/p.'
    m = re.search(r'\b(p|phuong)\.?\s+([a-z0-9\s\-\/]+)\b', t)
    candidates = []
    if m:
        candidates.append(m.group(2).strip())

    # Direct membership in ward_map keys
    for w_key, dist in ward_map.items():
        if re.search(r'\b'+re.escape(w_key)+r'\b', t):
            return dist

    # Fuzzy match from candidates
    for cand in candidates:
        best = None
        best_score = 0
        for w_key, dist in ward_map.items():
            toks = set(w_key.split())
            score = sum(1 for tok in toks if tok in cand.split())
            if score > best_score:
                best_score = score
                best = dist
        if best and best_score>0:
            return best

    # 4) Seed fallback
    for w_key, dist in SEED_WARD_TO_DISTRICT.items():
        if re.search(r'\b'+re.escape(w_key)+r'\b', t):
            return dist

    return None

# ----------------------------
# Main processing
# ----------------------------
def load_all_sheets(input_path: str) -> pd.DataFrame:
    xls = pd.ExcelFile(input_path)
    frames = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        df2 = df.copy()
        df2['__sheet__'] = sheet_name

        addr_col = pick_col(df2.columns, ADDRESS_CANDIDATES_KW)
        name_col = pick_col(df2.columns, NAME_CANDIDATES_KW)

        if addr_col is None:
            for c in df2.columns:
                sample = ' '.join(map(str, df2[c].head(20).tolist()))
                sm = norm_text(sample)
                if any(tok in sm for tok in ['ho chi minh','hcm','sai gon','quan','huyen','tp','phuong','duong','pho']):
                    addr_col = c
                    break

        df2['__address_col__'] = addr_col or ""
        df2['__name_col__']    = name_col or ""
        df2['__address__']     = df2[addr_col].astype(str) if addr_col in df2.columns else ""
        df2['__name__']        = df2[name_col].astype(str) if name_col in df2.columns else ""
        frames.append(df2)

    if not frames:
        raise RuntimeError("Khong doc duoc du lieu tu file Excel.")
    return pd.concat(frames, ignore_index=True)

def pick_identifier(row: pd.Series) -> str:
    if isinstance(row['__name__'], str) and row['__name__'].strip():
        return row['__name__'].strip()
    for col in row.index:
        if col in ['__address__','__sheet__','__address_col__','__name_col__','__is_hcm__','__unit__']:
            continue
        v = row[col]
        if isinstance(v, str) and v.strip():
            s = norm_text(v)
            if not any(k in s for k in ['duong','pho','phuong','xa','quan','huyen','ho chi minh','hcm','viet nam','vn']):
                return v
    return row['__address__']

def compute_report(df: pd.DataFrame, ward_map: Dict[str, str]) -> dict:
    df = df.copy()
    df['__is_hcm__'] = df['__address__'].apply(detect_hcm)
    df['__unit__'] = df.apply(lambda r: extract_unit_with_wards(r['__address__'], ward_map) if r['__is_hcm__'] else None, axis=1)
    df['__building_id__'] = df.apply(pick_identifier, axis=1)

    hcm_df = df[df['__is_hcm__']].copy()
    hcm_df['__dedup_key__'] = hcm_df['__building_id__'].astype(str).str.strip().str.lower() + '|' + hcm_df['__address__'].astype(str).str.strip().str.lower()
    hcm_df = hcm_df.drop_duplicates(subset='__dedup_key__')

    # Raw counts including unknowns (None)
    counts_raw = hcm_df['__unit__'].value_counts(dropna=False)

    # Build full DistrictCoverage table with zeros for missing
    full_index = list(HCMC_UNITS)
    unknown_label = 'Khong ro quan/huyen'
    if pd.isna(counts_raw.index).any() or (None in counts_raw.index if hasattr(counts_raw.index, '__contains__') else False):
        full_index = full_index + [unknown_label]

    # Map counts to dict with normalized unknown
    raw_map = {}
    for k, v in counts_raw.items():
        label = k if pd.notna(k) else unknown_label
        raw_map[label] = int(v)

    district_counts = pd.DataFrame({
        'District': full_index,
        'Buildings': [raw_map.get(d, 0) for d in full_index]
    })

    num_units_covered = sum(1 for d in HCMC_UNITS if raw_map.get(d, 0) > 0)
    total_units = len(HCMC_UNITS)
    coverage_pct = round((num_units_covered / total_units * 100) if total_units else 0.0, 2)

    num_unknown = raw_map.get(unknown_label, 0)
    summary_df = pd.DataFrame([
        ['Tong so dong trong file', len(df)],
        ['So dia diem thuoc HCM (sau khi loai trung)', len(hcm_df)],
        ['So don vi cap quan/huyen/co tp co hien dien', num_units_covered],
        ['Tong so don vi cap quan/huyen/co tp cua HCM', total_units],
        ['Do phu theo don vi hanh chinh (%)', coverage_pct],
        ['So toa "Khong ro quan/huyen"', int(num_unknown)],
    ], columns=['Chi tieu','Gia tri'])

    # Export-ready RawHCMC with header "Quan/Phuong" (header only; values are district-level unit names)
    export_df = hcm_df[['__sheet__','__name__','__address__','__unit__']].rename(columns={
        '__sheet__':'Sheet',
        '__name__':'Ten Toa nha (heuristic)',
        '__address__':'Dia chi',
        '__unit__':'Quan/Phuong'
    }).copy()
    export_df['Quan/Phuong'] = export_df['Quan/Phuong'].fillna(unknown_label)

    return {
        'summary': summary_df,
        'district_counts': district_counts,
        'raw_hcm': export_df
    }

def save_report(tables: dict, output_path: str) -> str:
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        tables['summary'].to_excel(writer, sheet_name='Summary', index=False)
        tables['district_counts'].to_excel(writer, sheet_name='DistrictCoverage', index=False)
        tables['raw_hcm'].to_excel(writer, sheet_name='RawHCMC', index=False)
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Generate HCMC coverage report from LED building Excel.")
    parser.add_argument('--input', required=True, help='Path to input Excel file')
    parser.add_argument('--output', required=False, help='Path to output Excel report (.xlsx). If omitted, auto-named in same folder.')
    parser.add_argument('--ward-map', required=False, help='Optional CSV/XLSX mapping file with columns ward,district')
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = re.sub(r'\.xlsx?$', '', input_path, flags=re.IGNORECASE)
        output_path = f"{base}_HCM_Coverage_{ts}.xlsx"

    # Load data
    df = load_all_sheets(input_path)

    # Optional ward map
    ward_map = {}
    if args.ward_map:
        try:
            ward_map = load_ward_map(args.ward_map)
        except Exception as e:
            print("Warning: Khong the tai ward-map. Tiep tuc voi mapping mac dinh. Error =", e)

    tables = compute_report(df, ward_map)
    save_report(tables, output_path)

    print("Report generated:", output_path)

if __name__ == '__main__':
    main()
