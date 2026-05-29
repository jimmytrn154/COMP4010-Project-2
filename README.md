# COMP4010-Project-2 | Mekong FloodLens

## Overview

This repository contains the working materials for **Mekong FloodLens**, a COMP4010 project focused on interactive water-risk visualization for the Vietnamese Mekong Delta.

The project has moved beyond a rainfall-only MVP. The current dataset collection now includes rainfall, surface-water/flood-proxy, cropland, population, and province-boundary data pulled from Google Earth Engine. The next major step is to merge these datasets into a dashboard-ready province-month panel and build the Python Shiny app.

## Start Here

The most important project documents are:

- [Proposal write-up](COMP4010_Project2_Team3_proposal_writeup.pdf): project scope, motivation, and planned dashboard direction.
- [Wireframe](wireframe.png): current dashboard layout and interaction reference.
- [Project progress log](PROJECT_PROGRESS.md): live tracker for completed work, risks, and next tasks.

If you are new to the repo, read those three files first.

## Repository Contents

Expected repository structure:

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
|   |   |-- province_month_water.csv              # planned
|   |   |-- province_exposure.csv                 # planned
|   |   `-- province_month_panel.csv             # planned main dashboard table
|-- scripts/
|   |-- 02_clean_rainfall.py
|   |-- 03_clean_water.py                       # planned
|   |-- 04_clean_exposure.py                    # planned
|   `-- 05_build_panel.py                       # planned
|-- app.py                                      # planned Shiny app entry point
|-- requirements.txt                            # planned
|-- COMP4010_Project2_Team3.pdf
|-- wireframe.png
|-- PROJECT_PROGRESS.md
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

[PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) is the live project log. It records current status, completed milestones, next tasks, blockers, and decisions. Treat it as the source of truth for active project status.

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

## Processed Data Plan

The next data-processing target is to build the following files in `data/processed/`:

- `province_month_rainfall.csv`  
  Cleaned rainfall table with rainfall anomaly and z-score.

- `province_month_water.csv`  
  Cleaned monthly surface-water table with `water_area_km2` and `water_area_pct`.

- `province_exposure.csv`  
  Combined province-level exposure table from cropland and population context. This may include yearly population and static cropland variables.

- `province_month_panel.csv`  
  Main dashboard table combining rainfall, water, population, cropland, and derived risk metrics.

## Data-Cleaning Scripts

The current implemented cleaning script is:

- [scripts/02_clean_rainfall.py](scripts/02_clean_rainfall.py)

Current behavior:

- reads a raw rainfall CSV
- standardizes the rainfall column name when needed
- converts date and time fields
- computes monthly climatology by province
- calculates rainfall anomaly and rainfall z-score
- writes `data/processed/province_month_rainfall.csv`

This script should be updated to use:

```text
data/raw/mekong_province_month_rainfall_1981_2025.csv
```

Planned scripts:

- `scripts/03_clean_water.py`: clean JRC surface-water table
- `scripts/04_clean_exposure.py`: combine WorldPop and ESA WorldCover exposure layers
- `scripts/05_build_panel.py`: merge all processed data into `province_month_panel.csv`

## Planned Dashboard

The Shiny dashboard should follow the wireframe and include:

- global filters: year, month, province, metric selector
- interactive Mekong Delta province map
- KPI cards for key water-risk indicators
- province ranking chart
- rainfall or risk trend chart
- anomaly heatmap
- province comparison chart

Planned app entry point:

```text
app.py
```

Current status: dashboard implementation has not started yet.

## Useful Commands

### Rebuild rainfall data

```bash
python scripts/02_clean_rainfall.py
```

### Planned commands

```bash
python scripts/03_clean_water.py
python scripts/04_clean_exposure.py
python scripts/05_build_panel.py
shiny run --reload app.py
```

### Run Earth Engine test

```bash
python test.py
```

## Current Repo Status

- Proposal and wireframe assets are available.
- Raw data collection from Google Earth Engine is substantially complete.
- Boundary, rainfall, surface-water, cropland, and population data are now available.
- The next major development task is to create the integrated processed dataset.
- Dashboard implementation and dependency management still need to be started.

## Recommended Reading Order

1. [COMP4010_Project2_Team3_proposal_writeup.pdf](COMP4010_Project2_Team3_proposal_writeup.pdf)
2. [wireframe.png](wireframe.png)
3. [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md)
4. `data/raw/`
5. [scripts/02_clean_rainfall.py](scripts/02_clean_rainfall.py)
6. `data/processed/`

## Notes

- The project should avoid calling JRC water data direct flood impact unless validated with event data.
- ESA WorldCover is a 2021 static land-cover snapshot and should not be used to claim historical cropland trends.
- WorldPop is annual, so population should be merged by province and year, not by month.
- `PROJECT_PROGRESS.md` should be updated whenever a new processed file, dashboard feature, or deployment milestone is completed.
