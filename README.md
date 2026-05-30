# COMP4010-Project-2 | Mekong FloodLens

## Overview

This repository contains the working materials for **Mekong FloodLens**, a COMP4010 project focused on interactive water-risk visualization for the Vietnamese Mekong Delta.

The project has moved beyond a rainfall-only MVP. The current pipeline includes rainfall, surface-water/flood-proxy, cropland, population, and province-boundary data pulled from Google Earth Engine, processed into a dashboard-ready province-month panel, and visualized in a Python Shiny dashboard.

## Start Here

The most important project documents are:

- [Proposal write-up](COMP4010_Project2_Team3_proposal_writeup.pdf): project scope, motivation, and planned dashboard direction.
- [Wireframe](wireframe.png): current dashboard layout and interaction reference.
- [Project progress log](PROJECT_PROGRESS_UPDATED.md): live tracker for completed work, risks, and next tasks.

If you are new to the repo, read those three files first.

## Repository Contents

Current repository structure:

```text
COMP4010-Project-2/
|-- data/
|   |-- raw/
|   |   |-- mekong_province_month_rainfall_1981_2025.csv
|   |   |-- mekong_province_cropland_2021.csv
|   |   |-- mekong_province_month_water_1984_2021.csv
|   |   |-- mekong_province_population_2000_2021.csv
|   |   |-- mekong_provinces_boundary.geojson
|   |   |-- mekong_province_month_rainfall_2000_2024.csv        # older/reference file
|   |   `-- mekong_province_month_rainfall_2020_2024.csv        # older/reference file
|   |-- processed/
|   |   |-- province_month_rainfall.csv
|   |   |-- province_month_water.csv
|   |   |-- province_exposure.csv
|   |   `-- province_month_panel.csv
|-- scripts/
|   |-- 02_clean_rainfall.py
|   |-- 03_clean_water.py
|   |-- 04_clean_exposure.py
|   `-- 05_build_panel.py
|-- app_refactored.py                           # current refactored Shiny dashboard
|-- app.py                                      # earlier dashboard implementation
|-- requirements.txt
|-- COMP4010_Project2_Team3_proposal_writeup.pdf
|-- wireframe.png
|-- PROJECT_PROGRESS_UPDATED.md
|-- github.md
|-- precipitation_map.html
`-- README.md
```

## Key Documentation

### Proposal write-up

[COMP4010_Project2_Team3.pdf](COMP4010_Project2_Team3_proposal_writeup.pdf) is the primary proposal document for the project. It defines the project motivation, central question, planned data sources, visualization challenge, and dashboard direction.

### Wireframe

[wireframe.png](wireframe.png) is the current visual reference for the intended dashboard layout. It should be used when aligning implementation decisions with the planned interface and analytical flow.

### Progress tracking

[PROJECT_PROGRESS_UPDATED.md](PROJECT_PROGRESS_UPDATED.md) is the live project log. It records current status, completed milestones, next tasks, blockers, and decisions. Treat it as the source of truth for active project status.

## Data Files

The repository now contains several raw datasets pulled from Google Earth Engine.

### Raw data

Files in `data/raw/`:

- `mekong_province_month_rainfall_1981_2025.csv`  
  Monthly province-level rainfall table derived from CHIRPS Daily rainfall. This is the main rainfall dataset.

- `mekong_province_month_water_1984_2021.csv`  
  Monthly province-level surface-water area derived from JRC Global Surface Water Monthly History. This should be treated as **surface-water extent / flood proxy**, not official flood impact.

- `mekong_province_cropland_2021.csv`  
  Province-level cropland area derived from ESA WorldCover 2021. This is a static agricultural exposure context layer.

- `mekong_province_population_2000_2021.csv`  
  Province-year population totals derived from WorldPop. This is annual population exposure data.

- `mekong_provinces_boundary.geojson`  
  Province boundary file for the 13 Vietnamese Mekong Delta provinces, extracted from FAO GAUL.

Older rainfall files may still exist for testing or comparison:

- `mekong_province_month_rainfall_2000_2024.csv`
- `mekong_province_month_rainfall_2020_2024.csv`

## Dataset Coverage

| Dataset | File | Time coverage | Granularity | Dashboard role |
|---|---|---|---|---|
| CHIRPS rainfall | `mekong_province_month_rainfall_1981_2025.csv` | 1981-2025 | Province-month | Rainfall trend, anomaly, drought proxy |
| JRC surface water | `mekong_province_month_water_1984_2021.csv` | 1984-03 to 2021-12 | Province-month | Surface-water extent / flood proxy |
| ESA WorldCover cropland | `mekong_province_cropland_2021.csv` | 2021 | Province | Agricultural exposure context |
| WorldPop population | `mekong_province_population_2000_2021.csv` | 2000-2021 | Province-year | Population exposure context |
| FAO GAUL boundary | `mekong_provinces_boundary.geojson` | Static | Province geometry | Map boundary and spatial joins |

## Coverage Logic

Because the datasets have different time ranges, different dashboard views should use different valid windows:

- Rainfall-only analysis: `1981-2025`
- Rainfall + surface-water comparison: `1984-03` to `2021-12`
- Rainfall + surface-water + population analysis: `2000-2021`
- Cropland exposure analysis: static 2021 context merged by province

WorldPop should be merged by `province_name + year`. ESA WorldCover cropland should be merged by `province_name`.

## Processed Data Outputs

The main processed files in `data/processed/` are now built and used by the dashboard:

- `province_month_rainfall.csv`  
  Cleaned rainfall table with rainfall anomaly and z-score.

- `province_month_water.csv`  
  Cleaned monthly surface-water table with `water_area_km2` and `water_area_pct`.

- `province_exposure.csv`  
  Combined province-level exposure table from yearly WorldPop population and 2021 ESA WorldCover cropland context.

- `province_month_panel.csv`  
  Main dashboard table combining rainfall, water, population, and cropland variables by province-month. The current dashboard computes the composite risk score at runtime from this panel.

## Combined Risk Score Methodology

The dashboard uses a composite `combined_risk_score` to summarize relative water risk by province-month. In the current implementation, `province_month_panel.csv` does not store this column directly, so [app_refactored.py](app_refactored.py) computes it at runtime after loading the panel.

The score is a relative index, not a measured flood probability or official hazard estimate. It combines four normalized components: surface water, high rainfall, drought signal, and exposure.

### Rainfall anomaly and z-score

Rainfall is first converted into a monthly anomaly and z-score in [scripts/02_clean_rainfall.py](scripts/02_clean_rainfall.py).

For each `province_name + month`, the script calculates a long-run monthly climatology:

```text
monthly_mean = mean rainfall for the same province and calendar month
monthly_std = standard deviation of rainfall for the same province and calendar month
```

Then each province-month receives:

```text
rainfall_anomaly = rainfall_mm - monthly_mean
rainfall_zscore = rainfall_anomaly / monthly_std
```

Positive `rainfall_zscore` values mean wetter-than-normal conditions for that province and month. Negative values mean drier-than-normal conditions. Infinite or missing z-scores are replaced with `0`.

### Component score setup

Before combining the indicators, the app converts each component to a comparable 0-1 scale using min-max normalization:

```text
minmax(x) = (x - min(x)) / (max(x) - min(x))
```

If all values are the same, the normalized score is set to `0` to avoid division by zero. Missing values are filled with `0` before normalization. The normalization is applied across the loaded dashboard dataset, so each score should be interpreted as relative to the available province-month records.

The component scores are:

```text
rainfall_score = minmax(max(rainfall_zscore, 0))
```

This keeps only unusually wet conditions. Normal or drier-than-normal months do not increase the high-rainfall component.

```text
water_score = minmax(water_area_pct)
```

This uses surface-water percentage as the flood-proxy component. It is not z-scored in the current app; it is normalized directly because `water_area_pct` is already a province-area-adjusted measure.

```text
drought_score = minmax(max(-rainfall_zscore, 0))
```

This converts unusually dry rainfall anomalies into a positive drought signal. A strongly negative rainfall z-score becomes a high drought component.

```text
exposure_score =
    0.60 * minmax(population_total)
  + 0.40 * minmax(cropland_area_km2)
```

Exposure combines people and agricultural land. Population receives the larger share because direct human exposure is the primary planning concern, while cropland is still included as an economic and livelihood exposure layer.

### Final combined score

The final score is a weighted average:

```text
combined_risk_score =
    0.35 * water_score
  + 0.25 * rainfall_score
  + 0.25 * drought_score
  + 0.15 * exposure_score
```

The weights reflect the dashboard's purpose as a water-risk screening tool:

- `water_score` receives the largest weight (`0.35`) because observed surface-water extent is the closest available proxy for actual inundation conditions.
- `rainfall_score` receives `0.25` because unusually high rainfall is a direct driver of flood risk, but rainfall alone does not confirm flooding.
- `drought_score` receives `0.25` so the same dashboard can flag unusually dry conditions, not only flood-like conditions.
- `exposure_score` receives `0.15` because population and cropland describe who or what may be affected, but they do not by themselves indicate that a water hazard is occurring.

These weights are heuristic and should be treated as transparent dashboard assumptions. They are useful for comparison and prioritization, but they should be recalibrated if validated flood-impact, drought-impact, or damage data becomes available.

## Data-Cleaning Scripts

The processing pipeline is implemented in `scripts/`:

- [scripts/02_clean_rainfall.py](scripts/02_clean_rainfall.py)
- [scripts/03_clean_water.py](scripts/03_clean_water.py)
- [scripts/04_clean_exposure.py](scripts/04_clean_exposure.py)
- [scripts/05_build_panel.py](scripts/05_build_panel.py)

Current behavior:

- `02_clean_rainfall.py` reads CHIRPS rainfall, standardizes the rainfall column, converts date fields, computes province-month climatology, calculates rainfall anomaly and rainfall z-score, and writes `data/processed/province_month_rainfall.csv`.
- `03_clean_water.py` reads JRC surface-water output, keeps monthly water area and province-area-normalized water percentage, and writes `data/processed/province_month_water.csv`.
- `04_clean_exposure.py` combines WorldPop population and ESA WorldCover cropland exposure by province/year and writes `data/processed/province_exposure.csv`.
- `05_build_panel.py` merges rainfall, water, and exposure into the dashboard panel at `data/processed/province_month_panel.csv`.

## Dashboard

The Shiny dashboard is implemented. The current refactored dashboard entry point is:

```text
app_refactored.py
```

It includes:

- global filters: year, month, province, metric selector
- interactive Mekong Delta province map
- KPI cards for key water-risk indicators
- province ranking chart
- rainfall trend chart
- risk component breakdown
- anomaly heatmap
- province comparison chart

The repository also contains `app.py`, an earlier dashboard implementation kept for reference.

## Dependencies

Runtime dependencies are listed in [requirements.txt](requirements.txt):

```text
pandas
shiny
plotly
geopandas
htmltools
shinywidgets
```

## Useful Commands

### Install dependencies

```bash
pip install -r requirements.txt
```

### Rebuild rainfall data

```bash
python scripts/02_clean_rainfall.py
```

### Rebuild all processed data

```bash
python scripts/03_clean_water.py
python scripts/04_clean_exposure.py
python scripts/05_build_panel.py
```

Run `02_clean_rainfall.py` first if the rainfall source file has changed.

### Run the dashboard

```bash
shiny run --reload app_refactored.py
```

### Run Earth Engine test

```bash
python test.py
```

## Current Repo Status

- Proposal and wireframe assets are available.
- Raw data collection from Google Earth Engine is substantially complete.
- Boundary, rainfall, surface-water, cropland, and population data are now available.
- Processed rainfall, water, exposure, and merged panel datasets are available in `data/processed/`.
- The Python Shiny dashboard is implemented in `app_refactored.py`.
- Dependency management is available through `requirements.txt`.
- Remaining work is mainly final polish, submission materials, and optional calibration or validation of the composite risk score.

## Recommended Reading Order

1. [COMP4010_Project2_Team3_proposal_writeup.pdf](COMP4010_Project2_Team3_proposal_writeup.pdf)
2. [wireframe.png](wireframe.png)
3. [PROJECT_PROGRESS_UPDATED.md](PROJECT_PROGRESS_UPDATED.md)
4. `data/raw/`
5. [scripts/02_clean_rainfall.py](scripts/02_clean_rainfall.py)
6. [scripts/05_build_panel.py](scripts/05_build_panel.py)
7. [app_refactored.py](app_refactored.py)
8. `data/processed/`

## Notes

- The project should avoid calling JRC water data direct flood impact unless validated with event data.
- ESA WorldCover is a 2021 static land-cover snapshot and should not be used to claim historical cropland trends.
- WorldPop is annual, so population should be merged by province and year, not by month.
- `PROJECT_PROGRESS_UPDATED.md` should be updated whenever a new processed file, dashboard feature, or deployment milestone is completed.
