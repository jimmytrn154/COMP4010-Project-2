import pandas as pd

def main():
    # Read raw datasets
    df_crop = pd.read_csv("data/raw/mekong_province_cropland_2021.csv")
    df_pop = pd.read_csv("data/raw/mekong_province_population_2000_2021.csv")
    
    # Drop province_area_km2 from crop to avoid collision during merge
    if "province_area_km2" in df_crop.columns:
        df_crop = df_crop.drop(columns=["province_area_km2"])
        
    # Merge on province_name and year (Outer join to keep all years)
    df_exposure = pd.merge(df_pop, df_crop, on=["province_name", "year"], how="outer")
    
    # Sort
    df_exposure = df_exposure.sort_values(by=["province_name", "year"]).reset_index(drop=True)
    
    # Export processed data
    output_path = "data/processed/province_exposure.csv"
    df_exposure.to_csv(output_path, index=False)
    print(f"Saved {output_path}")
    print(df_exposure.head())

if __name__ == "__main__":
    main()
