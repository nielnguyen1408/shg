"""Detect pages with long consecutive <img> sequences (e.g., >3 images in a row)."""
from __future__ import annotations

import argparse
import csv
from html.parser import HTMLParser
from pathlib import Path
from typing import List

import pandas as pd
import requests

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


class ImgRunParser(HTMLParser):
    """Track the longest run of consecutive <img> tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_run = 0
        self.max_run = 0

    def _reset_run(self) -> None:
        self.current_run = 0

    def handle_starttag(self, tag, attrs):  # type: ignore[override]
        if tag == "img":
            self.current_run += 1
            if self.current_run > self.max_run:
                self.max_run = self.current_run
        else:
            self._reset_run()

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if data.strip():
            self._reset_run()

    def handle_endtag(self, tag):  # type: ignore[override]
        if tag != "img":
            self._reset_run()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "links_csv",
        type=Path,
        help="CSV file containing one URL per line (first column is used).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("hot_product_result.xlsx"),
        help="Excel file to save results (default: hot_product_result.xlsx).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout in seconds (default: 15).",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=3,
        help="Minimum consecutive <img> count to flag (default: 3 -> flag when >3).",
    )
    return parser.parse_args()


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


def longest_img_run(html: str) -> int:
    parser = ImgRunParser()
    parser.feed(html)
    return parser.max_run


def check_link(url: str, timeout: float, threshold: int) -> dict[str, object]:
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
            "max_consecutive_imgs": 0,
            "hot_product": False,
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
            "max_consecutive_imgs": 0,
            "hot_product": False,
        }

    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or response.encoding

    max_run = longest_img_run(response.text)
    response.close()

    return {
        "status": "ok",
        "status_code": status_code,
        "detail": reason,
        "final_url": final_url,
        "redirected": redirected,
        "max_consecutive_imgs": max_run,
        "hot_product": max_run > threshold,
    }


def main() -> None:
    args = parse_args()
    links = load_links(args.links_csv)
    if not links:
        raise SystemExit("No links found in the provided CSV file.")

    results = []
    total = len(links)
    for index, link in enumerate(links, start=1):
        result = check_link(link, args.timeout, args.threshold)
        status = result.get("status", "ok")
        code = result.get("status_code")
        redirected = result.get("redirected")
        final_url = result.get("final_url")
        max_run = result.get("max_consecutive_imgs")
        hot_product = result.get("hot_product")
        detail = result.get("detail") or ""

        status_text = f"{status}"
        if code:
            status_text += f" ({code})"
        if detail:
            status_text += f": {detail}"
        if redirected and final_url:
            status_text += f" | redirected -> {final_url}"
        status_text += f" | max_img_run={max_run} | hot_product={hot_product}"
        print(f"[{index}/{total}] {link} -> {status_text}")

        row = {"link": link}
        row.update(result)
        results.append(row)

    df = pd.DataFrame(results)
    df.to_excel(args.output, index=False)
    print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
