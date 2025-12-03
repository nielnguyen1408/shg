"""Split clean_info.xlsx columns into per-criterion rows."""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

SECTION_COLUMNS = ["TongQuan", "ThietKe", "CongNang"]

LI_PATTERN = re.compile(r"<li\b[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL)
H3_PATTERN = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.IGNORECASE | re.DOTALL)


class TextExtractor(HTMLParser):
    """Convert HTML fragments into normalized plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: List[str] = []

    def handle_starttag(self, tag, attrs):  # type: ignore[override]
        if tag in {"br", "p", "div"}:
            self.chunks.append("\n")

    def handle_endtag(self, tag):  # type: ignore[override]
        if tag in {"p", "div"}:
            self.chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self.chunks.append(data)

    def get_text(self) -> str:
        text = "".join(self.chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s*\n\s*", "\n", text)
        return text.strip()


def html_to_text(fragment: str) -> str:
    parser = TextExtractor()
    parser.feed(fragment)
    return parser.get_text()


def split_plain_text(html_text: str) -> List[str]:
    text = html_to_text(html_text)
    if not text:
        return []
    pieces = [part.strip() for part in re.split(r"\n{2,}|\n", text) if part.strip()]
    return pieces or [text]


def extract_criteria(html_text: str) -> List[str]:
    content = html_text.strip()
    if not content:
        return []
    li_blocks = [html_to_text(block) for block in LI_PATTERN.findall(content)]
    li_blocks = [item for item in li_blocks if item]
    if li_blocks:
        return li_blocks

    h3_blocks = [html_to_text(block) for block in H3_PATTERN.findall(content)]
    h3_blocks = [item for item in h3_blocks if item]
    if h3_blocks:
        return h3_blocks

    return split_plain_text(content)


def flatten_sections(df: pd.DataFrame, sections: Iterable[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for _, record in df.iterrows():
        code = str(record.get("Code", "") or "").strip()
        if not code:
            continue
        for section in sections:
            html_text = str(record.get(section, "") or "")
            criteria = extract_criteria(html_text)
            for idx, item in enumerate(criteria, start=1):
                rows.append(
                    {
                        "Code": code,
                        "Section": section,
                        "Order": idx,
                        "Content": item,
                    }
                )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_file",
        type=Path,
        nargs="?",
        default=Path("clean_info.xlsx"),
        help="Source Excel/CSV file (default: clean_info.xlsx).",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("criteria_info.csv"),
        help="Destination CSV file (default: criteria_info.csv).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("criteria_info.json"),
        help="Destination JSON file (default: criteria_info.json).",
    )
    parser.add_argument(
        "--xlsx-output",
        type=Path,
        default=Path("criteria_info.xlsx"),
        help="Destination Excel file (default: criteria_info.xlsx).",
    )
    parser.add_argument(
        "--columns",
        nargs="*",
        default=SECTION_COLUMNS,
        help="Columns to split (default: TongQuan ThietKe CongNang).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    suffix = args.input_file.suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(args.input_file, dtype=str)
    else:
        df = pd.read_csv(args.input_file, dtype=str)
    df = df.fillna("")

    sections = args.columns if args.columns else SECTION_COLUMNS
    rows = flatten_sections(df, sections)
    if not rows:
        raise SystemExit("No criteria found. Check that columns contain HTML content.")

    result_df = pd.DataFrame(rows)
    result_df.to_csv(args.csv_output, index=False, encoding="utf-8")
    result_df.to_excel(args.xlsx_output, index=False)
    with args.json_output.open("w", encoding="utf-8") as fp:
        json.dump(rows, fp, ensure_ascii=False, indent=2)
    print(
        f"Wrote {len(rows)} criteria rows to "
        f"{args.csv_output}, {args.json_output}, and {args.xlsx_output}"
    )


if __name__ == "__main__":
    main()
