from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Iterable, List, Literal, Sequence

import pandas as pd


EXCEL_PATH = Path(__file__).with_name("product_filter.xlsx")
OUTPUT_PATH = Path(__file__).with_name("product_filter_clean.xlsx")
IMG_SRC_RE = re.compile(r'<img[^>]+src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
IFRAME_SRC_RE = re.compile(r'<iframe[^>]+src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
YOUTUBE_KEYWORDS = ("youtube.com", "youtu.be")
LinkType = Literal["image", "video"]


def normalize_url(url: str) -> str:
    """Ensure URLs are trimmed and default protocol is https for protocol-relative links."""
    url = url.strip()
    if url.startswith("//"):
        return f"https:{url}"
    return url


def try_parse_json(text: str):
    text = text.strip()
    if not text:
        return None
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return None


def is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def iter_text_fragments(value) -> Iterable[str]:
    """Yield string fragments from plain text or JSON-like blobs."""
    if is_missing(value):
        return
    if isinstance(value, str):
        parsed = try_parse_json(value)
        if parsed is None:
            yield value
        else:
            yield from iter_text_fragments(parsed)
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_text_fragments(v)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from iter_text_fragments(item)
    else:
        yield str(value)


def extract_links_from_text(text: str, collector) -> None:
    clean = unescape(text)
    for match in IMG_SRC_RE.findall(clean):
        collector("image", normalize_url(match))
    for match in IFRAME_SRC_RE.findall(clean):
        normalized = normalize_url(match)
        if any(keyword in normalized.lower() for keyword in YOUTUBE_KEYWORDS):
            collector("video", normalized)


def normalize_product_code(value) -> str:
    if is_missing(value):
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def extract_links(path: Path) -> Sequence[dict]:
    df = pd.read_excel(path)
    results: List[dict] = []

    for _, row in df.iterrows():
        product_code = normalize_product_code(row.get("Product Code"))

        def add_link(link_type: LinkType, url: str) -> None:
            if not url:
                return
            results.append(
                {
                    "Product Code": product_code,
                    "Content Type": link_type,
                    "Link": url,
                }
            )

        for cell in row:
            for fragment in iter_text_fragments(cell):
                extract_links_from_text(fragment, add_link)

    return results


def main() -> None:
    records = extract_links(EXCEL_PATH)
    output_df = pd.DataFrame(records, columns=["Product Code", "Content Type", "Link"])
    output_df.to_excel(OUTPUT_PATH, index=False)
    print(f"Wrote {len(output_df)} row(s) to {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
