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
| Rainfall cleaning | Done / needs update | Existing cleaning script should be updated to use the new `1981-2025` rainfall file |
| Integrated panel dataset | Not started | Need to merge rainfall, water, cropland, population, and boundary data |
| Dashboard app | Not started | `mvp.py` or final Shiny app entry point still needs implementation |
| Dependency management | Not started | Need `requirements.txt` |
| Documentation | In progress | README and progress tracker updated to reflect new data status |

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
| Build integrated panel dataset | Not started | Next | Merge data into `province_month_panel.csv` |
| Build dashboard prototype | Not started | Next | Start with rainfall + water + exposure views |
| Add install instructions and dependencies | Not started | Next | Create `requirements.txt` |
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

| Task | Owner | Started | Status | Notes |
|---|---|---|---|---|
| Update documentation to reflect expanded dataset inventory | Team | 2026-05-29 | In progress | README and progress tracker updated; keep syncing with repo |
| Plan integrated data pipeline | Team | 2026-05-29 | In progress | Need merge script and final table schema |

## Next Tasks

| Priority | Task | Owner | Notes |
|---|---|---|---|
| High | Update rainfall cleaning script | Unassigned | Switch input to `mekong_province_month_rainfall_1981_2025.csv` |
| High | Create water cleaning script | Unassigned | Clean `mekong_province_month_water_1984_2021.csv`; check missing values and units |
| High | Create exposure cleaning script | Unassigned | Merge `mekong_province_cropland_2021.csv` and `mekong_province_population_2000_2021.csv` |
| High | Build integrated panel table | Unassigned | Create `province_month_panel.csv` by merging rainfall, water, population, and cropland |
| High | Add `requirements.txt` | Unassigned | Include Shiny, pandas, plotly, geopandas, pyarrow if used |
| High | Create dashboard app entry point | Unassigned | Replace empty `mvp.py` or create `app.py` |
| Medium | Add first dashboard charts | Unassigned | Map, rainfall trend, water trend, anomaly heatmap, province ranking |
| Medium | Add risk-score prototype | Unassigned | Start simple: rainfall anomaly + water area + exposure context |
| Medium | Document GEE extraction workflow | Unassigned | Add scripts or instructions for all five raw datasets |
| Low | Remove or archive outdated sample files | Unassigned | Keep old rainfall files only if useful for testing |

## Planned Processed Outputs

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
| No dashboard code yet | Risk | Open | Data pipeline is ahead of app implementation |
| No dependency file | Risk | Open | Setup is not yet reproducible in one step |
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

### Update - 2026-05-29

- What was completed: Pulled expanded GEE datasets: CHIRPS rainfall `1981-2025`, JRC surface water `1984-2021`, ESA WorldCover cropland `2021`, WorldPop population `2000-2021`, and FAO GAUL Mekong boundary GeoJSON.
- What is in progress: Updating documentation and planning the integrated data-processing pipeline.
- What is blocked: Dashboard implementation and processed panel construction have not started yet.
- Next action: Build `province_month_panel.csv`, create `requirements.txt`, and start the Python Shiny app.
