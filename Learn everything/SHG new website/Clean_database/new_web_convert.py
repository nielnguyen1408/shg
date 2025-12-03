"""
Convert the legacy new_website_tinhnang XLS file into cleaner JSON/XLSX exports.

Each Attribute row becomes a feature entry, grouped by ProductCode. The script
expects one of the following files to be present in the same directory:
    - new_website_tinhnang.xls
    - new_website_tinhnanh.xls   (common typo)

Outputs:
    - new_website_tinhnang.json : grouped structure for the new frontend
    - new_website_tinhnang.xlsx : flattened table (Code, Title, Content, Image)
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_CANDIDATES = [
    "new_website_tinhnang.xls",
    "new_website_tinhnanh.xls",
]
JSON_OUTPUT = BASE_DIR / "new_website_tinhnang.json"
XLSX_OUTPUT = BASE_DIR / "new_website_tinhnang.xlsx"

COLUMN_MAPPING: Dict[str, str] = {
    "ProductCode": "Code",
    "AttributeTitle": "Title",
    "AttributeContentText": "Content",
    "AttributeImageFile": "Image",
}


def resolve_input_file() -> Path:
    for candidate in INPUT_CANDIDATES:
        path = BASE_DIR / candidate
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Khong tim thay file dau vao. Vui long dat 1 trong cac file: {INPUT_CANDIDATES}"
    )


def load_dataframe(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    missing = [col for col in COLUMN_MAPPING if col not in df.columns]
    if missing:
        raise ValueError(f"Thieu cot bat buoc trong file {path.name}: {missing}")
    df = df[list(COLUMN_MAPPING.keys())].copy()
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    df.fillna("", inplace=True)
    # strip whitespace to avoid duplicates caused by trailing spaces
    for column in df.columns:
        df[column] = df[column].astype(str).str.strip()
    return df


def group_features(df: pd.DataFrame) -> List[Dict[str, object]]:
    grouped: "OrderedDict[str, List[Dict[str, str]]]" = OrderedDict()
    for _, row in df.iterrows():
        code = row["Code"]
        if not code:
            continue
        feature = {
            "Title": row["Title"],
            "Content": row["Content"],
            "Image": row["Image"],
        }
        if not any(feature.values()):
            continue  # skip empty blocks
        grouped.setdefault(code, []).append(feature)
    result = [{"Code": code, "Features": features} for code, features in grouped.items()]
    return result


def export_outputs(df: pd.DataFrame, json_data: Iterable[Dict[str, object]]) -> None:
    JSON_OUTPUT.write_text(json.dumps(list(json_data), ensure_ascii=False, indent=2), encoding="utf-8")
    df.to_excel(XLSX_OUTPUT, index=False)


def main() -> None:
    input_path = resolve_input_file()
    df = load_dataframe(input_path)
    json_data = group_features(df)
    export_outputs(df, json_data)
    print(f"Da tao {JSON_OUTPUT.name} va {XLSX_OUTPUT.name} tu {input_path.name}")


if __name__ == "__main__":
    main()
