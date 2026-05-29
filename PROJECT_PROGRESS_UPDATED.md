# COMP4010 Project 2 Progress Tracker

## Project

- Project name: `Mekong FloodLens`
- Course: `COMP4010`
- Team: `Group 3`
- Repository: `COMP4010-Project-2`
- Last updated: `2026-05-29`

## Current Goal

Build an interactive Python Shiny dashboard for the Vietnamese Mekong Delta that combines rainfall, surface-water/flood-proxy, cropland, population, and province-boundary data into one province-level water-risk analysis pipeline.

## Overall Status

| Area | Status | Notes |
|---|---|---|
| Repository setup | Done | Base repo structure is in place |
| Proposal and wireframe | Done | Proposal and dashboard wireframe are available |
| Raw data collection | Done | Rainfall, surface-water, cropland, population, and boundary datasets have been pulled from Google Earth Engine |
| Boundary data | Done | `mekong_provinces_boundary.geojson` extracted from FAO GAUL |
| Rainfall data | Done | CHIRPS monthly province-level rainfall extracted for `1981-2025` |
| Surface-water data | Done | JRC Global Surface Water monthly province-level water area extracted for `1984-2021` |
| Cropland data | Done | ESA WorldCover 2021 province-level cropland area extracted |
| Population data | Done | WorldPop province-year population extracted for `2000-2021` |
| Rainfall cleaning | Done | Existing cleaning script updated to use the new `1981-2025` rainfall file |
| Integrated panel dataset | Done | Merged rainfall, water, cropland, population, and boundary data into one panel |
| Dashboard app | Done | Full interactive Shiny app with Mapbox choropleth and premium dark aesthetics implemented |
| Dependency management | Done | `requirements.txt` added with `shiny`, `pandas`, `plotly`, `geopandas`, and `shinywidgets` |
| Documentation | Done | README, progress tracker, and walkthroughs updated to reflect completion |

## Data Inventory

Raw datasets collected from Google Earth Engine:

| Dataset | File | Source | Time coverage | Granularity | Main use |
|---|---|---|---|---|---|
| Rainfall | `mekong_province_month_rainfall_1981_2025.csv` | CHIRPS Daily | 1981-2025 | Province-month | Rainfall trends, anomaly, drought proxy |
| Cropland | `mekong_province_cropland_2021.csv` | ESA WorldCover | 2021 | Province | Agricultural exposure context |
| Surface water | `mekong_province_month_water_1984_2021.csv` | JRC Global Surface Water Monthly History | 1984-03 to 2021-12 | Province-month | Surface-water extent / flood proxy |
| Population | `mekong_province_population_2000_2021.csv` | WorldPop | 2000-2021 | Province-year | Population exposure context |
| Boundary | `mekong_provinces_boundary.geojson` | FAO GAUL | Static boundary | Province geometry | Mapping and spatial joins |

## Time-Coverage Logic

Different datasets have different valid periods, so the dashboard should use different analysis windows depending on the selected view:

| Analysis view | Recommended coverage | Reason |
|---|---|---|
| Rainfall-only analysis | 1981-2025 | CHIRPS provides the longest coverage |
| Rainfall anomaly / drought proxy | 1981-2025 or 1981-2024 | Use long historical rainfall baseline; exclude incomplete latest years if needed |
| Rainfall + surface-water comparison | 1984-03 to 2021-12 | Overlap between CHIRPS and JRC water data |
| Rainfall + water + population | 2000-2021 | Overlap between CHIRPS, JRC, and WorldPop |
| Cropland exposure context | 2021 snapshot | ESA WorldCover is used as a static land-cover context layer |

## Milestones

| Milestone | Status | Target | Notes |
|---|---|---|---|
| Confirm project scope | Done | May 2026 | Mekong water-risk dashboard confirmed as group topic |
| Validate Google Earth Engine access | Done | May 2026 | GEE data extraction successfully tested |
| Collect rainfall data | Done | May 2026 | CHIRPS rainfall exported for 1981-2025 |
| Collect province boundaries | Done | May 2026 | FAO GAUL Mekong Delta boundary exported |
| Collect JRC surface-water data | Done | May 2026 | Monthly surface-water/flood-proxy data exported for 1984-2021 |
| Collect ESA WorldCover cropland data | Done | May 2026 | Province-level cropland area exported for 2021 |
| Collect WorldPop population data | Done | May 2026 | Province-year population exported for 2000-2021 |
| Update documentation | Done / ongoing | May 2026 | README and progress tracker updated |
| Build integrated panel dataset | Done | May 2026 | Merged data into `province_month_panel.csv` |
| Build dashboard prototype | Done | May 2026 | Built rainfall + water + exposure views with interactive map and trend charts |
| Add install instructions and dependencies | Done | May 2026 | Created `requirements.txt` |
| Final polish and submission assets | Not started | TBD | README, slides, report, demo |

## Completed Work

### Data

Collected and stored the following raw files:

- `data/raw/mekong_province_month_rainfall_1981_2025.csv`
- `data/raw/mekong_province_cropland_2021.csv`
- `data/raw/mekong_province_month_water_1984_2021.csv`
- `data/raw/mekong_province_population_2000_2021.csv`
- `data/raw/mekong_provinces_boundary.geojson`

Previously collected rainfall files may still exist for reference:

- `data/raw/mekong_province_month_rainfall_2020_2024.csv`
- `data/raw/mekong_province_month_rainfall_2000_2024.csv`

### Code

- Implemented initial rainfall cleaning pipeline in `scripts/02_clean_rainfall.py`
- Added Earth Engine smoke test in `test.py`
- Exported sample map to `precipitation_map.html`

### Documentation

- Added team Git workflow notes in `github.md`
- Updated `README.md` to reflect the expanded multi-dataset status
- Updated this progress tracker with new GEE data pulls and next-step planning

## In Progress

| Final polish and submission assets | Team | TBD | Not started | Prepare README, slides, report, demo |

## Next Tasks

| Priority | Task | Owner | Notes |
|---|---|---|---|
| High | Final polish and submission | Unassigned | README, slides, report, demo |
| Medium | Add risk-score prototype | Unassigned | Explore advanced risk metrics: rainfall anomaly + water area + exposure context |
| Low | Remove or archive outdated sample files | Unassigned | Keep old rainfall files only if useful for testing |

## Processed Outputs

Target files in `data/processed/`:

| File | Purpose |
|---|---|
| `province_month_rainfall.csv` | Cleaned rainfall with anomaly and z-score |
| `province_month_water.csv` | Cleaned monthly surface-water metrics |
| `province_exposure.csv` | Combined population and cropland exposure table |
| `province_month_panel.csv` | Main merged table for dashboard views |
| `mekong_provinces_boundary.geojson` | Dashboard-ready province boundary file |

## Risks and Blockers

| Item | Type | Status | Notes |
|---|---|---|---|
| Mixed dataset time coverage | Risk | Open | Rainfall, water, population, and cropland have different time ranges |
| Surface water is not direct flood impact | Limitation | Open | JRC should be labeled as surface-water extent or flood proxy |
| Earth Engine project access may vary by teammate | Blocker | Open | Raw data already exported, but re-extraction may need GEE access |

## Decisions Log

| Date | Decision | Reason |
|---|---|---|
| 2026-05-18 | Keep current scope documented as rainfall MVP | Matched repo contents at the time |
| 2026-05-18 | Track progress in a dedicated Markdown file | Easier to update during development |
| 2026-05-29 | Expand from rainfall MVP to multi-layer water-risk dashboard | Team collected rainfall, water, cropland, population, and boundary datasets |
| 2026-05-29 | Treat JRC as surface-water/flood proxy, not official flood impact | Avoid overclaiming what the dataset measures |
| 2026-05-29 | Use ESA WorldCover 2021 as static cropland exposure context | WorldCover is a snapshot layer, not a long historical series |
| 2026-05-29 | Use WorldPop as annual exposure data for 2000-2021 | Population is yearly and should be merged by province and year |

## Useful Commands

### Rebuild processed rainfall data

```bash
python scripts/02_clean_rainfall.py
```

### Run Earth Engine test

```bash
python test.py
```

### Planned commands

```bash
python scripts/03_clean_water.py
python scripts/04_clean_exposure.py
python scripts/05_build_panel.py
shiny run --reload app.py
```

## Update Template

Use this block when adding a new weekly or milestone update:

```md
### Update - YYYY-MM-DD

- What was completed:
- What is in progress:
- What is blocked:
- Next action:
```

## Activity Log

### Update - 2026-05-18

- What was completed: README updated to match the repository contents at that time.
- What is in progress: Project tracking and documentation cleanup.
- What is blocked: Dashboard implementation has not started yet.
- Next action: Add dependency file and start the MVP dashboard structure.

### Update - 2026-05-29 (Part 1)

- What was completed: Pulled expanded GEE datasets: CHIRPS rainfall `1981-2025`, JRC surface water `1984-2021`, ESA WorldCover cropland `2021`, WorldPop population `2000-2021`, and FAO GAUL Mekong boundary GeoJSON.
- What is in progress: Updating documentation and planning the integrated data-processing pipeline.
- What is blocked: Dashboard implementation and processed panel construction have not started yet.
- Next action: Build `province_month_panel.csv`, create `requirements.txt`, and start the Python Shiny app.

### Update - 2026-05-29 (Part 2)

- What was completed: Data cleaning scripts created for water and exposure. Built the integrated `province_month_panel.csv`. `requirements.txt` added. `app.py` completely rewritten into a premium, responsive dashboard with a custom dark UI, glassmorphism aesthetics, interactive Plotly Mapbox choropleth, and trend charts.
- What is in progress: Exploring a risk-score prototype combining multiple layers.
- What is blocked: None.
- Next action: Final polish and preparation of submission assets (slides, report, demo).
