from pathlib import Path
import pandas as pd


PANEL_PATH = Path("data/processed/province_month_panel.csv")
FEATURES_PATH = Path("data/processed/province_month_rainfall_features.csv")
OUTPUT_PATH = Path("data/processed/province_month_panel.csv")
BACKUP_PATH = Path("data/processed/province_month_panel_before_daily_features.csv")


def main() -> None:
    panel = pd.read_csv(PANEL_PATH)
    features = pd.read_csv(FEATURES_PATH)

    # Standardize merge keys
    for df in [panel, features]:
        df["province_name"] = df["province_name"].astype(str).str.strip()
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
        df["month"] = pd.to_numeric(df["month"], errors="coerce").astype(int)

    feature_cols = [
        "province_name",
        "year",
        "month",
        "rainfall_mm_from_daily",
        "mean_daily_rainfall",
        "max_1day_rainfall",
        "rain_days_count",
        "dry_days_count",
        "heavy_rain_days_20mm",
        "heavy_rain_days_50mm",
        "max_consecutive_dry_days",
        "max_consecutive_wet_days",
        "rain_day_ratio",
        "dry_day_ratio",
        "days_observed",
    ]

    features = features[feature_cols]

    # Backup existing panel before overwriting
    panel.to_csv(BACKUP_PATH, index=False)

    merged = panel.merge(
        features,
        on=["province_name", "year", "month"],
        how="left"
    )

    merged.to_csv(OUTPUT_PATH, index=False)

    print(f"Backup saved: {BACKUP_PATH}")
    print(f"Updated panel saved: {OUTPUT_PATH}")
    print(f"Rows: {len(merged):,}")
    print("New columns added:")
    for col in feature_cols:
        if col not in ["province_name", "year", "month"]:
            print(f"- {col}")


if __name__ == "__main__":
    main()