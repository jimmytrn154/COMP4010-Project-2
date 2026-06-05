from pathlib import Path
import re

import pandas as pd


SOURCE_PATH = Path("data/raw/mekong_province_day_rainfall_1981_2025.csv")
OUTPUT_DIR = Path("modeling/data_splitted")


def slugify_province_name(province_name: str) -> str:
    cleaned = province_name.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def main() -> None:
    df = pd.read_csv(SOURCE_PATH)

    if "province_name" not in df.columns:
        raise ValueError("Missing required column: province_name")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    provinces = sorted(df["province_name"].dropna().astype(str).str.strip().unique())

    for province in provinces:
        province_df = df[df["province_name"].astype(str).str.strip() == province].copy()
        output_name = f"{slugify_province_name(province)}_rainfall_1981_2025.csv"
        output_path = OUTPUT_DIR / output_name
        province_df.to_csv(output_path, index=False)
        print(f"Saved {output_path} ({len(province_df)} rows)")

    print(f"Done. Exported {len(provinces)} province files to {OUTPUT_DIR}.")


if __name__ == "__main__":
    main()
