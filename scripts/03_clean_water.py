import pandas as pd

def main():
    # Read raw water data
    df = pd.read_csv("data/raw/mekong_province_month_water_1984_2021.csv")
    
    # Ensure date/time types
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    
    # Select relevant columns
    df = df[
        [
            "province_name",
            "year",
            "month",
            "date",
            "water_area_km2",
            "province_area_km2",
            "water_area_pct",
        ]
    ]
    
    # Export processed data
    output_path = "data/processed/province_month_water.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved {output_path}")
    print(df.head())

if __name__ == "__main__":
    main()
