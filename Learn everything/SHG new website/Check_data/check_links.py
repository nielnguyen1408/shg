"""Check URLs for the presence of a specific text snippet and export results."""
from __future__ import annotations

import argparse
import csv
from html.parser import HTMLParser
from pathlib import Path
from typing import List
import unicodedata

import pandas as pd
import requests

TARGET_TEXT = "Thông số kỹ thuật"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


class VisibleTextParser(HTMLParser):
    """Extract visible text, ignoring script & style tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: List[str] = []

    def handle_starttag(self, tag, attrs):  # type: ignore[override]
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):  # type: ignore[override]
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.parts)


def extract_visible_text(html: str) -> str:
    parser = VisibleTextParser()
    parser.feed(html)
    text = parser.get_text().replace("\xa0", " ")
    return " ".join(text.split())


def normalize_text(text: str) -> str:
    """Normalize text for reliable matching (NFC + lowercase)."""
    return unicodedata.normalize("NFC", text).lower()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "links_csv",
        type=Path,
        help="Path to the CSV file that contains one URL per line.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("links_result.xlsx"),
        help="Destination Excel file (default: links_result.xlsx)",
    )
    parser.add_argument(
        "--target",
        dest="targets",
        action="append",
        help="Text snippet to search for (can be passed multiple times).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout in seconds (default: 15)",
    )
    args = parser.parse_args()
    if not args.targets:
        args.targets = [TARGET_TEXT]
    return args

def load_links(csv_path: Path) -> List[str]:
    links: List[str] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.reader(fp)
        for row in reader:
            if not row:
                continue
            url = row[0].strip()
            if not url or url.startswith("#"):
                continue
            links.append(url)
    return links

def check_link(url: str, targets: List[str], timeout: float) -> dict[str, str]:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return {
            "status": "request_error",
            "detail": str(exc),
            "status_code": "",
            "final_url": "",
            "redirected": False,
        }

    status_code = response.status_code
    final_url = response.url
    redirected = bool(response.history)
    reason = response.reason or ""

    if status_code >= 400:
        response.close()
        return {
            "status": "http_error",
            "status_code": status_code,
            "detail": reason,
            "final_url": final_url,
            "redirected": redirected,
        }

    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or response.encoding

    page_text = normalize_text(extract_visible_text(response.text))
    normalized_targets = [normalize_text(target) for target in targets]
    result: dict[str, str] = {
        target: ("found" if normalized_target in page_text else "not found")
        for target, normalized_target in zip(targets, normalized_targets)
    }
    response.close()

    result["status"] = "ok"
    result["status_code"] = status_code
    result["detail"] = reason
    result["final_url"] = final_url
    result["redirected"] = redirected
    return result

def main() -> None:
    args = parse_args()
    targets = args.targets
    links = load_links(args.links_csv)
    if not links:
        raise SystemExit("No links found in the provided CSV file.")

    results = []
    for index, link in enumerate(links, start=1):
        result = check_link(link, targets, args.timeout)
        status = result.get("status", "ok")
        if status != "ok":
            parts = [status]
            code = result.get("status_code")
            if code:
                parts.append(f"({code})")
            if result.get("redirected"):
                parts.append(f"redirected -> {result.get('final_url')}")
            detail = result.get("detail")
            if detail:
                parts.append(f": {detail}")
            status_text = " ".join(parts)
        else:
            status_text = ", ".join(f"{target}: {result[target]}" for target in targets)
            extras = []
            code = result.get("status_code")
            if code:
                extras.append(f"status={code}")
            if result.get("redirected"):
                extras.append(f"redirected -> {result.get('final_url')}")
            detail = result.get("detail")
            if detail:
                extras.append(detail)
            if extras:
                status_text += " | " + "; ".join(extras)
        print(f"[{index}/{len(links)}] {link} -> {status_text}")

        row = {"link": link}
        row.update(result)
        results.append(row)

    df = pd.DataFrame(results)
    df.to_excel(args.output, index=False)
    print(f"Saved results to {args.output}")

if __name__ == "__main__":
    main()
