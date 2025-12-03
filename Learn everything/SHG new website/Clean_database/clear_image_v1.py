"""
Utility script to remove embedded <img> tags from the rich-text fields
inside clean_info.json and new_website_tinhnang.json.

Running this script produces *_noimage.json versions that keep all of the
original structure but strip problematic image tags from the HTML snippets.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, List, Tuple

import argparse

BASE_DIR = Path(__file__).resolve().parent
TARGET_FILES = [
    ("clean_info.json", "clean_info_noimage.json"),
    ("new_website_tinhnang.json", "new_website_tinhnang_noimage.json"),
]

IMG_TAG_RE = re.compile(r"<img\b[^>]*?>", re.IGNORECASE | re.DOTALL)
ATTR_RE = re.compile(
    r'(\w[\w:-]*)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s">]+))',
    re.IGNORECASE,
)


def normalize_attrs(tag_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag_text):
        key = match.group(1).lower()
        value = match.group(3) or match.group(4) or match.group(5) or ""
        attrs[key] = value.strip()
    return attrs


def format_image_placeholder(attrs: dict[str, str]) -> str:
    pieces = []
    if "src" in attrs and attrs["src"]:
        pieces.append(f'src="{attrs["src"]}"')
    if "alt" in attrs and attrs["alt"]:
        pieces.append(f'alt="{attrs["alt"]}"')
    if not pieces:
        return " image "
    inner = " ".join(pieces)
    return f"<img {inner}>"


def strip_img_tags(value: Any, formatter=format_image_placeholder) -> Any:
    """Recursively remove <img> tags from any string in the structure."""
    if isinstance(value, str):
        def repl(match: re.Match) -> str:
            attrs = normalize_attrs(match.group(0))
            return formatter(attrs)

        return IMG_TAG_RE.sub(repl, value)
    if isinstance(value, list):
        return [strip_img_tags(item, formatter) for item in value]
    if isinstance(value, dict):
        return {key: strip_img_tags(val, formatter) for key, val in value.items()}
    return value


def process_file(input_name: str, output_name: str) -> None:
    src = BASE_DIR / input_name
    dst = BASE_DIR / output_name
    if not src.exists():
        raise FileNotFoundError(f"Khong tim thay file {src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    cleaned = strip_img_tags(data)
    dst.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Da tao {dst.name} tu {src.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove <img> tags from JSON files and write *_noimage outputs."
    )
    parser.add_argument(
        "--input",
        help="Duong dan toi file JSON can xu ly (mac dinh: su dung danh sach co dinh)",
    )
    parser.add_argument(
        "--output",
        help="Duong dan file JSON sau khi loai bo <img> (bat buoc neu dung --input)",
    )
    return parser.parse_args()


def build_tasks(args: argparse.Namespace) -> List[Tuple[str, str]]:
    if args.input and args.output:
        return [(args.input, args.output)]
    if args.input or args.output:
        raise SystemExit("Can cung cap ca --input va --output hoac khong tham so nao.")
    return TARGET_FILES


def main() -> None:
    args = parse_args()
    tasks = build_tasks(args)
    for input_name, output_name in tasks:
        process_file(input_name, output_name)


if __name__ == "__main__":
    main()
