
"""Quick status checker to flag live vs. error links."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

import pandas as pd
import requests

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


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
        default=Path("quick_check_result.xlsx"),
        help="Excel file to save results (default: quick_check_result.xlsx).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds (default: 10).",
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


def check_status(url: str, timeout: float) -> dict[str, str | int]:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            timeout=timeout,
            stream=True,
        )
    except requests.RequestException as exc:
        return {"status": "request_error", "detail": str(exc), "status_code": ""}

    status_code = response.status_code
    final_url = response.url
    redirected = bool(response.history)
    reason = response.reason or ""
    response.close()

    if status_code >= 400:
        return {
            "status": "http_error",
            "status_code": status_code,
            "detail": reason,
            "final_url": final_url,
            "redirected": redirected,
        }

    return {
        "status": "live",
        "status_code": status_code,
        "detail": reason,
        "final_url": final_url,
        "redirected": redirected,
    }


def main() -> None:
    args = parse_args()
    links = load_links(args.links_csv)
    if not links:
        raise SystemExit("No links found in the provided CSV file.")

    results = []
    total = len(links)
    for index, link in enumerate(links, start=1):
        result = check_status(link, args.timeout)
        status = result.get("status", "live")
        code = result.get("status_code")
        detail = result.get("detail") or ""
        status_text = status
        if code:
            status_text += f" ({code})"
        if detail:
            status_text += f": {detail}"
        if result.get("redirected"):
            status_text += f" | redirected -> {result.get('final_url')}"
        print(f"[{index}/{total}] {link} -> {status_text}")

        row = {"link": link}
        row.update(result)
        results.append(row)

    df = pd.DataFrame(results)
    df.to_excel(args.output, index=False)
    print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
