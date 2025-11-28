"""Check URLs for the presence of a specific text snippet and export results."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

import requests
import pandas as pd

TARGET_TEXT = "Thông số kỹ thuật"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

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
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return {"error": f"error: {exc}"}

    page_text = response.text.lower()
    return {
        target: ("found" if target.lower() in page_text else "not found")
        for target in targets
    }

def main() -> None:
    args = parse_args()
    targets = args.targets
    links = load_links(args.links_csv)
    if not links:
        raise SystemExit("No links found in the provided CSV file.")

    results = []
    for index, link in enumerate(links, start=1):
        result = check_link(link, targets, args.timeout)
        if "error" in result:
            status_text = result["error"]
        else:
            status_text = ", ".join(f"{target}: {result[target]}" for target in targets)
        print(f"[{index}/{len(links)}] {link} -> {status_text}")

        row = {"link": link}
        row.update(result)
        results.append(row)

    df = pd.DataFrame(results)
    df.to_excel(args.output, index=False)
    print(f"Saved results to {args.output}")

if __name__ == "__main__":
    main()
