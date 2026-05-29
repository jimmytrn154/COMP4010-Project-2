import pandas as pd

def main():
    print("Loading processed datasets...")
    df_rain = pd.read_csv("data/processed/province_month_rainfall.csv")
    df_water = pd.read_csv("data/processed/province_month_water.csv")
    df_exp = pd.read_csv("data/processed/province_exposure.csv")
    
    # Ensure year and month are ints where they exist
    for df in [df_rain, df_water]:
        df["year"] = df["year"].astype(int)
        df["month"] = df["month"].astype(int)
    
    df_exp["year"] = df_exp["year"].astype(int)
    
    # Drop date columns before merging to avoid confusion or '_x', '_y' suffixes
    if "date" in df_rain.columns:
        df_rain = df_rain.drop(columns=["date"])
    if "date" in df_water.columns:
        df_water = df_water.drop(columns=["date"])
    if "date" in df_exp.columns:
        df_exp = df_exp.drop(columns=["date"])
        
    print("Merging rainfall and water data...")
    # Merge rainfall and water on province_name, year, month using outer join
    df_panel = pd.merge(df_rain, df_water, on=["province_name", "year", "month"], how="outer")
    
    print("Merging exposure data...")
    # Merge with exposure on province_name and year
    # Left join or outer join? We want all province-months.
    df_panel = pd.merge(df_panel, df_exp, on=["province_name", "year"], how="left")
    
    # Sort for final output
    df_panel = df_panel.sort_values(by=["province_name", "year", "month"]).reset_index(drop=True)
    
    # Export panel
    output_path = "data/processed/province_month_panel.csv"
    df_panel.to_csv(output_path, index=False)
    print(f"Saved {output_path}")
    print(df_panel.info())

if __name__ == "__main__":
    main()
