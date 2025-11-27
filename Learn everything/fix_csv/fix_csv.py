#!/usr/bin/env python3
"""
Utility for cleaning CSV files where Vietnamese text was decoded with the
wrong encoding (typically UTF-8 bytes interpreted as cp1252/latin-1).

Example:
    python fix_csv.py Query.csv
    python fix_csv.py Query.csv -o Query_clean.csv --force
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Tuple

DEFAULT_BAD_ENCODING = "cp1252"
# If not provided via CLI we fall back to DEFAULT_BAD_ENCODING so we simulate
# the incorrect decode before attempting repairs.
DEFAULT_INPUT_ENCODING = None
DEFAULT_OUTPUT_ENCODING = "utf-8"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair mojibake Vietnamese text inside a CSV file."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to the corrupted CSV file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Location for the cleaned CSV (defaults to <source>_clean.csv).",
    )
    parser.add_argument(
        "--input-encoding",
        default=DEFAULT_INPUT_ENCODING,
        help=(
            "Encoding used to read the CSV before repair. "
            "Defaults to the value passed via --bad-decoding."
        ),
    )
    parser.add_argument(
        "--output-encoding",
        default=DEFAULT_OUTPUT_ENCODING,
        help=f"Encoding used to write the cleaned CSV (default: {DEFAULT_OUTPUT_ENCODING}).",
    )
    parser.add_argument(
        "--bad-decoding",
        default=DEFAULT_BAD_ENCODING,
        help=(
            "Encoding that was incorrectly applied to the original UTF-8 text. "
            f"Default: {DEFAULT_BAD_ENCODING}."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def fix_cell(value: str, wrong_encoding: str, target_encoding: str) -> Tuple[str, bool]:
    """
    Attempt to recover UTF-8 text that was previously decoded with `wrong_encoding`.

    Returns the possibly corrected value and whether a change was made.
    """
    if not value:
        return value, False

    try:
        # Treat the already-decoded text as if it were bytes from the wrong encoding,
        # then decode those bytes with the real encoding (UTF-8 by default).
        repaired = value.encode(wrong_encoding).decode(target_encoding)
    except UnicodeError:
        return value, False

    if repaired == value:
        return value, False

    return repaired, True


def clean_csv(
    source: Path,
    destination: Path,
    reader_encoding: str,
    writer_encoding: str,
    wrong_encoding: str,
) -> Tuple[int, int]:
    """
    Clean the CSV and return counts of (rows_processed, cells_fixed).
    """
    rows_processed = 0
    cells_fixed = 0

    with source.open("r", encoding=reader_encoding, errors="replace", newline="") as src:
        reader = csv.reader(src)
        with destination.open(
            "w", encoding=writer_encoding, errors="strict", newline=""
        ) as dst:
            writer = csv.writer(dst)
            for row in reader:
                rows_processed += 1
                cleaned_row = []
                for cell in row:
                    repaired, changed = fix_cell(cell, wrong_encoding, writer_encoding)
                    if changed:
                        cells_fixed += 1
                    cleaned_row.append(repaired)
                writer.writerow(cleaned_row)

    return rows_processed, cells_fixed


def main() -> None:
    args = parse_args()

    source_path = args.source.expanduser().resolve()
    if not source_path.is_file():
        raise SystemExit(f"File not found: {source_path}")

    if args.output:
        destination_path = args.output.expanduser().resolve()
    else:
        destination_path = source_path.with_name(f"{source_path.stem}_clean.csv")

    if destination_path.exists() and not args.force:
        raise SystemExit(
            f"Destination '{destination_path}' exists. Use --force to overwrite."
        )

    reader_encoding = args.input_encoding or args.bad_decoding

    rows, cells = clean_csv(
        source=source_path,
        destination=destination_path,
        reader_encoding=reader_encoding,
        writer_encoding=args.output_encoding,
        wrong_encoding=args.bad_decoding,
    )

    print(
        f"Done. Wrote {rows} rows to '{destination_path}' "
        f"and fixed {cells} cells that contained mojibake."
    )

    if cells == 0:
        print(
            "No cells changed. If the text is still corrupted, double-check "
            "the --input-encoding/--bad-decoding options."
        )


if __name__ == "__main__":
    main()
