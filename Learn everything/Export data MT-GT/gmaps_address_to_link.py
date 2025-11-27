#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gmaps_address_to_link.py

Mục tiêu:
- Từ địa chỉ -> tìm ra link Google Maps
- Nếu không có chính xác thì thêm một cột "gan_dung"
- Từ link lấy ra tọa độ (khi có thể)

Yêu cầu:
- Python 3.9+
- Thư viện: requests, pandas, python-slugify (tùy chọn)
- Biến môi trường: GOOGLE_MAPS_API_KEY (khuyến nghị) hoặc truyền --api-key

Sử dụng:
1) Geocode danh sách địa chỉ từ CSV:
   python gmaps_address_to_link.py geocode --in input.csv --out output.csv --api-key YOUR_KEY
   (CSV input cần cột: address)

2) Geocode một địa chỉ đơn lẻ:
   python gmaps_address_to_link.py geocode --address "120B tổ 3 Đa Sỹ Kiến Hưng, Hà Đông, Hà Nội" --out output.csv --api-key YOUR_KEY

3) Parse một link Google Maps để lấy toạ độ (nếu có trong URL):
   python gmaps_address_to_link.py parse-url --url "https://www.google.com/maps/place/...@21.0278,105.8342,17z/"

Ghi chú:
- Để đánh dấu "gần đúng", script dùng trường "partial_match" từ Google Geocoding API.
- Nếu chỉ có place_id mà không có lat/lng trong URL, cần thêm 1 gọi Place Details hoặc Geocoding để lấy lat/lng.
"""

import os
import re
import sys
import time
import json
import argparse
from typing import Dict, Any, Optional, Tuple, List

import requests
import pandas as pd

GEOCODE_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

def get_api_key(passed_key: Optional[str] = None) -> str:
    key = passed_key or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise RuntimeError("Thiếu API key. Truyền --api-key hoặc đặt biến môi trường GOOGLE_MAPS_API_KEY.")
    return key

def normalize_address_for_compare(s: str) -> str:
    # So sánh tương đối: hạ chữ, bỏ khoảng kép.
    return re.sub(r"\s+", " ", s or "").strip().lower()

def build_gmaps_link_from_latlng(lat: float, lng: float) -> str:
    # Link chuẩn theo tài liệu: https://www.google.com/maps/search/?api=1&query=lat,lng
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

def build_gmaps_link_from_place_id(place_id: str, label: Optional[str] = None) -> str:
    # Có thể dùng query_place_id để force tới đúng place; query có thể là label hiển thị.
    if not label:
        label = "Location"
    from urllib.parse import quote
    return f"https://www.google.com/maps/search/?api=1&query={quote(label)}&query_place_id={quote(place_id)}"

def geocode_address(address: str, api_key: str, sleep_secs: float = 0.0) -> Dict[str, Any]:
    """Gọi Geocoding API. Trả về dict gồm:
        {
            'input_address': ...,
            'formatted_address': ...,
            'lat': ...,
            'lng': ...,
            'place_id': ...,
            'types': [...],
            'partial_match': True/False,
            'google_maps_url': ...,
            'gan_dung': True/False,
            'raw': {...}  # toàn bộ JSON để debug
        }
    """
    params = {
        "address": address,
        "key": api_key,
        "language": "vi"  # ưu tiên kết quả tiếng Việt
    }
    resp = requests.get(GEOCODE_ENDPOINT, params=params, timeout=20)
    data = resp.json()
    status = data.get("status")
    results = data.get("results", [])

    result: Dict[str, Any] = {
        "input_address": address,
        "formatted_address": None,
        "lat": None,
        "lng": None,
        "place_id": None,
        "types": None,
        "partial_match": None,
        "google_maps_url": None,
        "gan_dung": None,
        "raw": data
    }

    if status != "OK" or not results:
        result["gan_dung"] = True  # không có kết quả rõ ràng => coi như gần đúng
        return result

    first = results[0]
    geometry = first.get("geometry", {})
    location = geometry.get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")

    formatted = first.get("formatted_address")
    place_id = first.get("place_id")
    types = first.get("types", [])
    partial_match = first.get("partial_match", False)

    # Xác định near/exact: dựa trên partial_match (Google cung cấp)
    gan_dung = bool(partial_match)

    # Tạo link ưu tiên theo place_id (ổn định) + kèm lat/lng link để linh hoạt
    url = build_gmaps_link_from_place_id(place_id, label=formatted) if place_id else None
    if not url and lat is not None and lng is not None:
        url = build_gmaps_link_from_latlng(lat, lng)

    result.update({
        "formatted_address": formatted,
        "lat": lat,
        "lng": lng,
        "place_id": place_id,
        "types": ",".join(types) if types else None,
        "partial_match": partial_match,
        "google_maps_url": url,
        "gan_dung": gan_dung
    })

    # Tùy chọn: nghỉ giữa các request để tránh quota
    if sleep_secs > 0:
        time.sleep(sleep_secs)

    return result

# -------- Parse Google Maps URL -> lat/lng nếu có ----------

_AT_PATTERN = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)(?:,|\b)")
_Q_PATTERN = re.compile(r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)\b")
_QUERY_PATTERN = re.compile(r"[?&]query=(-?\d+\.\d+),(-?\d+\.\d+)\b")
_CENTER_PATTERN = re.compile(r"[?&]center=(-?\d+\.\d+),(-?\d+\.\d+)\b")

def parse_gmaps_url(url: str) -> Tuple[Optional[float], Optional[float], Dict[str, Any]]:
    """
    Cố gắng trích lat/lng từ một URL Google Maps.
    Hỗ trợ các dạng phổ biến:
      - .../@lat,lng,17z/...
      - ...?q=lat,lng
      - ...?query=lat,lng
      - ...?center=lat,lng
    Trả về: (lat, lng, meta_dict)
    meta_dict có thể chứa query_place_id nếu phát hiện (không tự resolve được lat/lng nếu chỉ có place_id).
    """
    meta = {}

    # Thử với @lat,lng
    m = _AT_PATTERN.search(url)
    if m:
        return float(m.group(1)), float(m.group(2)), meta

    # Thử q=lat,lng
    m = _Q_PATTERN.search(url)
    if m:
        return float(m.group(1)), float(m.group(2)), meta

    # Thử query=lat,lng
    m = _QUERY_PATTERN.search(url)
    if m:
        return float(m.group(1)), float(m.group(2)), meta

    # Thử center=lat,lng
    m = _CENTER_PATTERN.search(url)
    if m:
        return float(m.group(1)), float(m.group(2)), meta

    # Nếu có place_id trong URL, lưu lại meta (cần API call khác để resolve)
    # Ví dụ: ...search/?api=1&query=...&query_place_id=ChIJ...
    pid = None
    try:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(url).query)
        qpid = qs.get("query_place_id", [None])[0]
        if qpid:
            meta["query_place_id"] = qpid
    except Exception:
        pass

    return None, None, meta

# -------------------- CLI --------------------

def cmd_geocode(args: argparse.Namespace) -> None:
    api_key = get_api_key(args.api_key)

    # Chuẩn bị dữ liệu địa chỉ đầu vào
    addresses: List[str] = []
    if args.address:
        addresses = [args.address]
    elif args.in_csv:
        df_in = pd.read_csv(args.in_csv)
        if "address" not in df_in.columns:
            raise RuntimeError("CSV đầu vào phải có cột 'address'")
        addresses = df_in["address"].astype(str).fillna("").tolist()
    else:
        raise RuntimeError("Cần --address HOẶC --in input.csv")

    out_rows = []
    for i, addr in enumerate(addresses, start=1):
        addr = addr.strip()
        if not addr:
            out_rows.append({
                "input_address": "",
                "formatted_address": None,
                "lat": None,
                "lng": None,
                "place_id": None,
                "types": None,
                "partial_match": None,
                "google_maps_url": None,
                "gan_dung": True,
                "error": "Địa chỉ rỗng"
            })
            continue

        try:
            res = geocode_address(addr, api_key, sleep_secs=args.sleep)
            row = {
                "input_address": res.get("input_address"),
                "formatted_address": res.get("formatted_address"),
                "lat": res.get("lat"),
                "lng": res.get("lng"),
                "place_id": res.get("place_id"),
                "types": res.get("types"),
                "partial_match": res.get("partial_match"),
                "google_maps_url": res.get("google_maps_url"),
                "gan_dung": res.get("gan_dung"),
            }
        except Exception as e:
            row = {
                "input_address": addr,
                "formatted_address": None,
                "lat": None,
                "lng": None,
                "place_id": None,
                "types": None,
                "partial_match": None,
                "google_maps_url": None,
                "gan_dung": True,
                "error": str(e),
            }
        out_rows.append(row)

        if args.verbose:
            print(f"[{i}/{len(addresses)}] {addr} -> {row.get('google_maps_url')} | gan_dung={row.get('gan_dung')}")

    df_out = pd.DataFrame(out_rows)
    if args.out_csv:
        df_out.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
        print(f"Đã ghi kết quả vào: {args.out_csv}")
    else:
        # In ra màn hình
        print(df_out.to_csv(index=False, encoding="utf-8-sig"))

def cmd_parse_url(args: argparse.Namespace) -> None:
    lat, lng, meta = parse_gmaps_url(args.url)
    out = {
        "url": args.url,
        "lat": lat,
        "lng": lng,
        "query_place_id": meta.get("query_place_id"),
        "note": "Nếu chỉ có place_id, cần gọi Geocoding/Place Details API để lấy lat/lng."
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Từ địa chỉ -> link Google Maps -> đánh dấu gần đúng -> lấy tọa độ.")
    sub = parser.add_subparsers(dest="cmd")

    p1 = sub.add_parser("geocode", help="Geocode địa chỉ (CSV hoặc đơn lẻ).")
    p1.add_argument("--in", dest="in_csv", help="Đường dẫn CSV đầu vào (cột: address).")
    p1.add_argument("--address", help="Geocode 1 địa chỉ đơn lẻ.")
    p1.add_argument("--out", dest="out_csv", help="Đường dẫn CSV đầu ra.")
    p1.add_argument("--api-key", dest="api_key", help="API key (nếu không dùng biến môi trường).")
    p1.add_argument("--sleep", type=float, default=0.0, help="Nghỉ giữa các request (giây).")
    p1.add_argument("--verbose", action="store_true", help="In log trong khi chạy.")
    p1.set_defaults(func=cmd_geocode)

    p2 = sub.add_parser("parse-url", help="Parse link Google Maps để trích toạ độ (nếu có trong URL).")
    p2.add_argument("--url", required=True, help="URL Google Maps.")
    p2.set_defaults(func=cmd_parse_url)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    args.func(args)

if __name__ == "__main__":
    main()
