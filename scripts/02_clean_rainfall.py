import pandas as pd

df = pd.read_csv("data/raw/mekong_province_month_rainfall_1981_2025.csv")

# Rename GEE output column if needed
# Usually rainfall value may appear as "mean"
if "mean" in df.columns:
    df = df.rename(columns={"mean": "rainfall_mm"})

df["date"] = pd.to_datetime(df["date"])
df["year"] = df["year"].astype(int)
df["month"] = df["month"].astype(int)

# Compute province-month climatology
clim = (
    df.groupby(["province_name", "month"])["rainfall_mm"]
    .agg(["mean", "std"])
    .reset_index()
    .rename(columns={"mean": "monthly_mean", "std": "monthly_std"})
)

df = df.merge(clim, on=["province_name", "month"], how="left")

df["rainfall_anomaly"] = df["rainfall_mm"] - df["monthly_mean"]
df["rainfall_zscore"] = df["rainfall_anomaly"] / df["monthly_std"]

# Handle division by zero if any
df["rainfall_zscore"] = df["rainfall_zscore"].replace([float("inf"), -float("inf")], 0).fillna(0)

df = df[
    [
        "province_name",
        "year",
        "month",
        "date",
        "rainfall_mm",
        "monthly_mean",
        "rainfall_anomaly",
        "rainfall_zscore",
    ]
]

df.to_csv("data/processed/province_month_rainfall.csv", index=False)

print("Saved data/processed/province_month_rainfall.csv")
print(df.head())