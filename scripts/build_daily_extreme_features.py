from pathlib import Path
import pandas as pd
import numpy as np


RAW_DAILY_PATH = Path("data/raw/mekong_province_day_rainfall_1981_2025.csv")
OUTPUT_PATH = Path("data/processed/province_month_rainfall_features.csv")


def longest_run(mask: pd.Series) -> int:
    """
    Return the longest consecutive True run in a boolean Series.
    Example: [True, True, False, True] -> 2
    """
    if mask.empty:
        return 0

    max_run = 0
    current_run = 0

    for value in mask.fillna(False).astype(bool):
        if value:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0

    return int(max_run)


def main() -> None:
    df = pd.read_csv(RAW_DAILY_PATH)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    df["rainfall_mm"] = pd.to_numeric(df["rainfall_mm"], errors="coerce").fillna(0)

    # Basic daily flags
    df["is_rain_day"] = df["rainfall_mm"] >= 1.0
    df["is_dry_day"] = df["rainfall_mm"] < 1.0
    df["is_heavy_20mm"] = df["rainfall_mm"] >= 20.0
    df["is_heavy_50mm"] = df["rainfall_mm"] >= 50.0

    group_cols = ["province_name", "year", "month"]

    # Standard monthly aggregations
    monthly = (
        df.groupby(group_cols)
        .agg(
            rainfall_mm_from_daily=("rainfall_mm", "sum"),
            mean_daily_rainfall=("rainfall_mm", "mean"),
            max_1day_rainfall=("rainfall_mm", "max"),
            rain_days_count=("is_rain_day", "sum"),
            dry_days_count=("is_dry_day", "sum"),
            heavy_rain_days_20mm=("is_heavy_20mm", "sum"),
            heavy_rain_days_50mm=("is_heavy_50mm", "sum"),
            days_observed=("date", "count"),
        )
        .reset_index()
    )

    # Consecutive dry/wet spell features
    spell_features = (
        df.sort_values(["province_name", "date"])
        .groupby(group_cols)
        .apply(
            lambda g: pd.Series(
                {
                    "max_consecutive_dry_days": longest_run(g["is_dry_day"]),
                    "max_consecutive_wet_days": longest_run(g["is_rain_day"]),
                }
            )
        )
        .reset_index()
    )

    monthly = monthly.merge(spell_features, on=group_cols, how="left")

    # Optional normalized features
    monthly["rain_day_ratio"] = monthly["rain_days_count"] / monthly["days_observed"]
    monthly["dry_day_ratio"] = monthly["dry_days_count"] / monthly["days_observed"]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print(monthly.head())
    print(f"Rows: {len(monthly):,}")


if __name__ == "__main__":
    main()