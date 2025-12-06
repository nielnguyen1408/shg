"""
Prefix relative image paths in a JSON file with a chosen base URL.

Defaults target the feature file `new_website_tinhnang_noimage.json` so you
can quickly normalize its images.

Usage examples:
  python input_image_v1.py
  python input_image_v1.py --input clean_info_noimage.json --output clean_info_noimage.json --base-url https://sunhouse.com.vn/
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urljoin

IMG_ATTR_RE = re.compile(
    r'(<img[^>]*?(?:src|data-src)\s*=\s*)(["\'])([^"\'>]*)(\2)',
    re.IGNORECASE,
)
IMG_TAG_RE = re.compile(r"<img\b([^>]*?)(/?)>", re.IGNORECASE)
STYLE_RE = re.compile(r'style\s*=\s*("([^"]*)"|\'([^\']*)\')', re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Them base URL vao duong dan anh trong file JSON."
    )
    parser.add_argument(
        "--input",
        default="new_website_tinhnang_noimage.json",
        help="Duong dan file JSON can xu ly.",
    )
    parser.add_argument(
        "--output",
        default="new_website_tinhnang_noimage.json",
        help="Noi ghi file JSON sau khi cap nhat duong dan anh.",
    )
    parser.add_argument(
        "--base-url",
        default="https://preview6305.canhcam.com.vn/",
        help="Domain hoac thu muc goc de ghep vao duong dan anh.",
    )
    parser.add_argument(
        "--image-keys",
        default="Image,AttributeImageFile",
        help="Danh sach key duoc xem la truong anh (phan cach bang dau phay).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=450,
        help="Width (px) gan vao the <img> de tranh vo khung.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=450,
        help="Height (px) gan vao the <img> de tranh vo khung.",
    )
    return parser.parse_args()


def is_absolute_url(url: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url)) or url.startswith("//")


def normalize_base(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def prefix_url(path: str, base_url: str) -> str:
    trimmed = path.strip()
    if not trimmed or is_absolute_url(trimmed):
        return path
    return urljoin(base_url, trimmed.lstrip("/"))


def replace_img_sources(
    text: str, base_url: str, stats: Dict[str, int], width: int, height: int
) -> str:
    def repl(match: re.Match) -> str:
        prefix, quote, src, _closing = match.groups()
        new_src = prefix_url(src, base_url)
        if new_src != src:
            stats["html_img"] += 1
        return f"{prefix}{quote}{new_src}{quote}"

    updated = IMG_ATTR_RE.sub(repl, text)
    return ensure_img_dimensions(updated, width, height, stats)


def ensure_img_dimensions(
    text: str, width: int, height: int, stats: Dict[str, int]
) -> str:
    def repl(match: re.Match) -> str:
        attrs, closing = match.groups()
        attrs_body = attrs.rstrip().rstrip("/").rstrip()

        style_val = ""
        style_match = STYLE_RE.search(attrs_body)
        if style_match:
            style_val = style_match.group(2) or style_match.group(3) or ""
            start, end = style_match.span()
            attrs_body = attrs_body[:start] + attrs_body[end:]

        attrs_body = re.sub(
            r'\s+\bwidth\s*=\s*(".*?"|\'.*?\'|[^\s>]+)', "", attrs_body, flags=re.IGNORECASE
        )
        attrs_body = re.sub(
            r'\s+\bheight\s*=\s*(".*?"|\'.*?\'|[^\s>]+)', "", attrs_body, flags=re.IGNORECASE
        )

        extra = f"max-width:{width}px;max-height:{height}px;object-fit:contain;"
        new_style_val = (style_val.rstrip(";") + ";" + extra).lstrip(";")

        attrs_body = attrs_body.rstrip()
        if attrs_body:
            attrs_body += " "
        attrs_body += f'style="{new_style_val}" width="{width}" height="{height}"'

        stats["sized_img"] += 1
        closing_char = "/>" if closing else ">"
        return f"<img {attrs_body}{closing_char}"

    return IMG_TAG_RE.sub(repl, text)


def transform_value(
    value: Any,
    base_url: str,
    image_keys: set[str],
    stats: Dict[str, int],
    width: int,
    height: int,
    current_key: str | None = None,
) -> Any:
    if isinstance(value, dict):
        return {
            key: transform_value(val, base_url, image_keys, stats, width, height, key)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [
            transform_value(item, base_url, image_keys, stats, width, height, current_key)
            for item in value
        ]
    if isinstance(value, str):
        updated = value
        if current_key and current_key.lower() in image_keys:
            new_url = prefix_url(updated, base_url)
            if new_url != updated:
                stats["image_field"] += 1
            updated = new_url
        updated = replace_img_sources(updated, base_url, stats, width, height)
        return updated
    return value


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    base_url = normalize_base(args.base_url.strip())
    image_keys = {key.strip().lower() for key in args.image_keys.split(",") if key.strip()}

    src = Path(args.input)
    dst = Path(args.output)

    data = load_json(src)
    stats: Dict[str, int] = {"image_field": 0, "html_img": 0, "sized_img": 0}
    updated = transform_value(
        data, base_url, image_keys, stats, width=args.width, height=args.height
    )
    save_json(dst, updated)

    print(
        f"Da ghi {dst} voi base {base_url} "
        f"(truong anh: {stats['image_field']}, img trong HTML: {stats['html_img']}, img them size: {stats['sized_img']})."
    )


if __name__ == "__main__":
    main()
