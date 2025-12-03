"""Clean HTML-encoded product content exported from an info CSV/XLSX file."""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
from pathlib import Path
from typing import Dict, List

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_file",
        type=Path,
        nargs="?",
        default=Path("info.xlsx"),
        help="Source file (.xlsx or .csv). Default: info.xlsx",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("clean_info.csv"),
        help="Destination CSV file (default: clean_info.csv).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("clean_info.json"),
        help="Destination JSON file (default: clean_info.json).",
    )
    parser.add_argument(
        "--xlsx-output",
        type=Path,
        default=Path("clean_info.xlsx"),
        help="Destination Excel file (default: clean_info.xlsx).",
    )
    return parser.parse_args()


def normalize_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def read_input_rows(input_path: Path) -> List[Dict[str, object]]:
    suffix = input_path.suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(input_path, dtype=str)
        df = df.fillna("")
        return df.to_dict("records")

    with input_path.open("r", encoding="utf-8-sig", newline="") as fp:
        header = fp.readline()
        if not header:
            return []
        delimiter = "\t" if "\t" in header else ","
        fp.seek(0)
        reader = csv.DictReader(fp, delimiter=delimiter)
        return list(reader)


def load_rows(input_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    raw_rows = read_input_rows(input_path)
    if not raw_rows:
        raise SystemExit("No rows found in the input file.")

    sample_keys = {key for row in raw_rows for key in row.keys()}
    required = {"Code", "Content"}
    if not required.issubset(sample_keys):
        raise SystemExit("Input file must contain 'Code' and 'Content' columns.")

    for line_number, raw_row in enumerate(raw_rows, start=2):
        code = normalize_cell(raw_row.get("Code"))
        content_raw = normalize_cell(raw_row.get("Content"))
        if not code or not content_raw:
            continue
        try:
            content_data = json.loads(content_raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in Content column at line {line_number}: {exc}") from exc
        cleaned_content = {}
        for key, value in content_data.items():
            if isinstance(value, str):
                previous = None
                current = value
                # Repeatedly unescape until string stops changing (handles double encoding).
                while previous != current:
                    previous = current
                    current = html.unescape(current)
                cleaned_content[key] = current
            else:
                cleaned_content[key] = value
        row = {"Code": code, **cleaned_content}
        rows.append(row)
    if not rows:
        raise SystemExit("No usable rows found after parsing the input file.")
    return rows


def write_csv(rows: List[Dict[str, str]], csv_path: Path) -> None:
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: List[Dict[str, str]], json_path: Path) -> None:
    with json_path.open("w", encoding="utf-8") as fp:
        json.dump(rows, fp, ensure_ascii=False, indent=2)


def write_excel(rows: List[Dict[str, str]], xlsx_path: Path) -> None:
    df = pd.DataFrame(rows)
    df.to_excel(xlsx_path, index=False)


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input_file)
    write_csv(rows, args.csv_output)
    write_json(rows, args.json_output)
    write_excel(rows, args.xlsx_output)
    print(
        f"Wrote {len(rows)} rows to {args.csv_output}, "
        f"{args.json_output}, and {args.xlsx_output}"
    )


if __name__ == "__main__":
    main()
