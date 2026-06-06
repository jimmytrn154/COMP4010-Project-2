# COMP4010-Project-2 | Mekong FloodLens

## Overview

Mekong FloodLens is a COMP4010 project about province-level water-risk analysis for the Vietnamese Mekong Delta. The repository combines:

- multi-source environmental and exposure data
- a processing pipeline that builds a dashboard-ready province-month panel
- daily rainfall feature engineering
- a Python Shiny dashboard for exploratory analysis
- a province-level machine learning rainfall forecast preview

The current repo is no longer a rainfall-only MVP. It now supports rainfall, rainfall anomaly, dryness proxy metrics, surface-water extent, cropland exposure, population exposure, daily rainfall structure, and a 12-month daily rainfall forecast preview based on XGBoost outputs.

## Current Repo Idea

The dashboard is designed as an observational and exploratory analysis tool, not an operational warning system. Its current analytical framing is:

- what is happening across the Mekong provinces right now
- which provinces look wetter or drier than normal
- how rainfall relates to observed surface water
- how provinces compare on selected indicators
- what daily rainfall history and forecast output look like for each province

The current app intentionally emphasizes transparent indicators such as:

- `rainfall_mm`
- `rainfall_anomaly`
- `rainfall_zscore`
- `dry_index`
- `dry_day_ratio`
- `max_consecutive_dry_days`
- `water_area_km2`
- `water_area_pct`

The repo no longer centers the dashboard around a combined risk score story. The live app focuses on interpretable rainfall, dryness, and surface-water metrics.

## Current Progress

At the current repo state:

- raw data collection is complete for the main rainfall, surface-water, cropland, population, and boundary layers
- processed monthly rainfall, water, exposure, and merged panel outputs exist in `data/processed/`
- daily rainfall has been expanded into monthly extreme and persistence features
- daily rainfall has been split into per-province files for modeling
- province-level forecast result files for the next 12 months already exist in `modeling/result/`
- the main Shiny dashboard is implemented in `app_refactored.py`
- the dashboard includes an `ML Prediction` tab that visualizes observed daily history plus recursive XGBoost forecast output

For the running project log, see [PROJECT_PROGRESS_UPDATED.md](PROJECT_PROGRESS_UPDATED.md).

## Start Here

Recommended reading order:

1. [PROJECT_PROGRESS_UPDATED.md](PROJECT_PROGRESS_UPDATED.md)
2. [README.md](README.md)
3. [wireframe.png](wireframe.png)
4. [app_refactored.py](app_refactored.py)
5. [modeling/ml.md](modeling/ml.md)

Useful supporting assets:

- [COMP4010_Project2_Team3_proposal_writeup.pdf](COMP4010_Project2_Team3_proposal_writeup.pdf)
- [github.md](github.md)
- [precipitation_map.html](precipitation_map.html)

## Repository Layout

```text
COMP4010-Project-2/
|-- app_refactored.py
|-- app.py
|-- README.md
|-- PROJECT_PROGRESS_UPDATED.md
|-- requirements.txt
|-- data/
|   |-- raw/
|   `-- processed/
|-- scripts/
|   |-- 02_clean_rainfall.py
|   |-- 03_clean_water.py
|   |-- 04_clean_exposure.py
|   |-- 05_build_panel.py
|   |-- build_daily_extreme_features.py
|   `-- merge_daily_features_into_panel.py
|-- modeling/
|   |-- ml.md
|   |-- split_data.py
|   |-- train_all_models.ipynb
|   |-- data_splitted/
|   `-- result/
|-- context/
|-- eda_outputs/
|-- old/
`-- chun/
```

Notes:

- `app_refactored.py` is the main dashboard entry point.
- `app.py` is an older dashboard version kept for reference.
- `chun/` appears to be a local virtual environment.
- `old/` contains older documentation snapshots.

## Data Inventory

### Raw data

Main raw files in `data/raw/`:

- `mekong_province_month_rainfall_1981_2025.csv`
- `mekong_province_day_rainfall_1981_2025.csv`
- `mekong_province_month_water_1984_2021.csv`
- `mekong_province_cropland_2021.csv`
- `mekong_province_population_2000_2021.csv`
- `mekong_provinces_boundary.geojson`

Older rainfall extracts are still present for reference or comparison:

- `mekong_province_month_rainfall_2000_2024.csv`
- `mekong_province_month_rainfall_2020_2024.csv`

### Coverage summary

| Dataset | Coverage | Granularity | Current use |
|---|---|---|---|
| CHIRPS monthly rainfall | 1981-2025 | Province-month | Rainfall totals, anomaly, z-score |
| CHIRPS daily rainfall | 1981-2025 | Province-day | Daily extreme and persistence features, ML forecasting |
| JRC surface water | 1984-2021 | Province-month | Surface-water extent / flood proxy |
| ESA WorldCover cropland | 2021 | Province | Static exposure context |
| WorldPop population | 2000-2021 | Province-year | Population exposure context |
| FAO GAUL boundary | Static | Province geometry | Mapping |

### Coverage logic

Because the layers do not share the same time window, the dashboard should be interpreted with coverage constraints in mind:

- rainfall and dryness analysis can use the longest historical range
- rainfall plus surface-water comparisons are limited by JRC coverage
- exposure views depend on population year availability and static cropland context
- ML forecasting uses daily rainfall history only

## Processed Outputs

Main files in `data/processed/`:

- `province_month_rainfall.csv`
- `province_month_water.csv`
- `province_exposure.csv`
- `province_month_panel.csv`
- `province_month_rainfall_features.csv`
- `province_month_panel_before_daily_features.csv`

Current roles:

- `province_month_rainfall.csv`: cleaned monthly rainfall with anomaly and z-score
- `province_month_water.csv`: cleaned surface-water metrics
- `province_exposure.csv`: population and cropland exposure table
- `province_month_panel.csv`: main merged dashboard table
- `province_month_rainfall_features.csv`: monthly features derived from daily rainfall
- `province_month_panel_before_daily_features.csv`: backup created before daily features were merged into the panel

The daily-derived monthly features currently include:

- `rainfall_mm_from_daily`
- `mean_daily_rainfall`
- `max_1day_rainfall`
- `rain_days_count`
- `dry_days_count`
- `heavy_rain_days_20mm`
- `heavy_rain_days_50mm`
- `max_consecutive_dry_days`
- `max_consecutive_wet_days`
- `rain_day_ratio`
- `dry_day_ratio`
- `days_observed`

## Processing Pipeline

### Monthly data pipeline

The main monthly processing flow is:

1. `scripts/02_clean_rainfall.py`
2. `scripts/03_clean_water.py`
3. `scripts/04_clean_exposure.py`
4. `scripts/05_build_panel.py`

Outputs from those scripts feed `data/processed/province_month_panel.csv`.

### Daily feature pipeline

Daily rainfall is expanded with:

1. `scripts/build_daily_extreme_features.py`
2. `scripts/merge_daily_features_into_panel.py`

This adds the daily-derived monthly indicators into the main panel used by the dashboard.

## Modeling Pipeline

The repo now includes a province-level rainfall forecasting workflow in `modeling/`.

Main components:

- `modeling/split_data.py`: splits the full daily rainfall file into one file per province
- `modeling/train_all_models.ipynb`: trains and exports forecast outputs
- `modeling/ml.md`: explains the current modeling strategy
- `modeling/data_splitted/`: per-province daily rainfall history files
- `modeling/result/`: per-province and combined forecast outputs

The current forecast design, documented in [modeling/ml.md](modeling/ml.md), uses:

- two-stage daily forecasting
- recent-weighted training
- recursive daily prediction
- XGBoost for rain occurrence and rainfall amount

Current forecast output files include:

- `modeling/result/all_provinces_forecast_next_12_months.csv`
- one `*_forecast_next_12_months.csv` file for each province

## Dashboard

The main dashboard is [app_refactored.py](app_refactored.py).

Current dashboard tabs:

- `Mekong Summary`
- `Rainfall & Dryness`
- `Surface Water`
- `Province Comparison`
- `ML Prediction`
- `Methodology / Caveats`

Current dashboard capabilities:

- global filters for year, month, province, top-N, and metric
- chart-driven province filtering from province bars and the rainfall-vs-water scatter
- province choropleth map
- KPI cards
- rainfall anomaly ranking
- dryness ranking
- rainfall seasonality and year-vs-normal trend views
- rainfall anomaly heatmap
- surface-water trend and rainfall-vs-water scatter
- province comparison and timeline views
- daily rainfall history plus forecast preview for each province
- an `ML Prediction` tab summary that explains the forecast model, inputs, horizon, and caveats

Important interpretation notes:

- the dashboard is exploratory, not operational
- JRC water data should be treated as surface-water extent or flood proxy, not flood impact
- the `ML Prediction` tab is a model preview, not an official advisory
- the forecast view currently emphasizes interpretability and recent-pattern behavior; the app does not yet surface held-out error metrics

## Dependencies

Current dependencies in [requirements.txt](requirements.txt):

- `pandas==2.3.3`
- `shiny==1.6.2`
- `plotly==5.24.1`
- `geopandas==1.1.3`
- `htmltools==0.7.0`
- `shinywidgets==0.8.1`
- `scikit-learn==1.7.2`
- `xgboost==3.2.0`
- `ipykernel==7.2.0`

## Useful Commands

### Install dependencies

```bash
pip install -r requirements.txt
```

### Rebuild the monthly panel

```bash
python scripts/02_clean_rainfall.py
python scripts/03_clean_water.py
python scripts/04_clean_exposure.py
python scripts/05_build_panel.py
```

### Rebuild daily-derived monthly features

```bash
python scripts/build_daily_extreme_features.py
python scripts/merge_daily_features_into_panel.py
```

### Split daily rainfall by province

```bash
python modeling/split_data.py
```

### Run the dashboard

```bash
shiny run --reload app_refactored.py
```

## Current Status Summary

The repo is currently in a strong implementation state:

- data collection is done for the core layers
- monthly and daily processing outputs exist
- the main Shiny dashboard is implemented
- chart-click cross-filtering is implemented for province-focused exploration
- forecast files already exist and are wired into the dashboard
- the remaining work is mostly polish, validation, submission packaging, and any final analytical framing decisions

## Notes

- Keep `PROJECT_PROGRESS_UPDATED.md` aligned with any meaningful repo milestone.
- Avoid describing the dashboard as an official flood prediction tool.
- Avoid implying that static cropland or annual population data provide monthly hazard measurements.
- If the daily rainfall source changes, regenerate the daily-derived monthly features and any affected modeling outputs.
