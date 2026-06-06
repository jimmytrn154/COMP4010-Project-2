# COMP4010 Project 2 Progress Tracker

## Project

- Project name: `Mekong FloodLens`
- Course: `COMP4010`
- Team: `Group 3`
- Repository: `COMP4010-Project-2`
- Main application entry point: `app_refactored.py`
- Last updated: `2026-06-06`

## Current Repo Position

The project is no longer an early MVP. The current repository already contains:

- cleaned monthly rainfall, surface-water, and exposure layers
- a merged province-month analytical panel
- daily-derived rainfall persistence and extreme-event features
- province-level split daily rainfall files for modeling
- province-level 12-month rainfall forecast exports
- a multi-tab Python Shiny dashboard with an `ML Prediction` tab

The remaining work is mostly submission-facing:

- tighten narrative consistency across docs and report
- validate the final app walkthrough
- make teamwork evidence explicit
- decide whether to add any last small analytical polish

## 2b Application Status

Working assessment against rubric section `2b. Application`:

| Criterion | Current status | Notes |
|---|---|---|
| `2.6` Visualization quality & design | Good | Cohesive dark theme, clear tab structure, and stronger storytelling than a raw dashboard |
| `2.7` Chart requirements met | Excellent | Exceeds minimum chart count and chart-type variety |
| `2.8` Interactivity | Good -> improved | Global filters already existed; chart-click province filtering has now been added |
| `2.9` Technical complexity | Excellent | Multi-source pipeline, spatial view, daily feature engineering, and forecasting |
| `2.10` ML / analytics | Good -> improved | Forecast tab now includes model framing, inputs, horizon, and caveats |
| `2.11` Proper use of Python Shiny | Good -> improved | Added shared reactive helpers for repeated filtered subsets |
| `2.12` Reproducibility & code quality | Good -> improved | `requirements.txt` is now pinned to the local working environment |
| `2.13` Repository organization & documentation | Good -> improved | README and progress tracker now reflect the current repo state |
| `2.14` Teamwork & collaboration evidence | Still needs explicit evidence | Repo history exists, but final ownership mapping still needs confirmation |

## Current Dashboard Scope

Current dashboard tabs in `app_refactored.py`:

1. `Mekong Summary`
2. `Rainfall & Dryness`
3. `Surface Water`
4. `Province Comparison`
5. `ML Prediction`
6. `Methodology / Caveats`

Current interactive capabilities:

- global year, month, province, top-N, and metric filters
- chart-driven province filtering from province bar charts
- chart-driven province filtering from the rainfall anomaly vs surface-water scatter
- linked cross-tab province focus through the shared sidebar selection
- Plotly tooltips and highlighted selected province states

## Data and Pipeline Status

### Raw data status

| Dataset | File | Coverage | Role |
|---|---|---|---|
| CHIRPS monthly rainfall | `data/raw/mekong_province_month_rainfall_1981_2025.csv` | `1981-2025` | Monthly rainfall totals, anomaly, z-score |
| CHIRPS daily rainfall | `data/raw/mekong_province_day_rainfall_1981_2025.csv` | `1981-2025` | Daily rainfall history, derived monthly features, forecasting |
| JRC surface water | `data/raw/mekong_province_month_water_1984_2021.csv` | `1984-2021` | Surface-water extent / flood proxy |
| ESA WorldCover cropland | `data/raw/mekong_province_cropland_2021.csv` | `2021` snapshot | Static agricultural exposure context |
| WorldPop population | `data/raw/mekong_province_population_2000_2021.csv` | `2000-2021` | Annual exposure context |
| FAO GAUL boundary | `data/raw/mekong_provinces_boundary.geojson` | Static | Province geometry for mapping |

### Processed data status

| File | Status | Role |
|---|---|---|
| `data/processed/province_month_rainfall.csv` | Ready | Clean rainfall with anomaly and z-score |
| `data/processed/province_month_water.csv` | Ready | Monthly surface-water metrics |
| `data/processed/province_exposure.csv` | Ready | Population and cropland context |
| `data/processed/province_month_rainfall_features.csv` | Ready | Daily-derived monthly rainfall features |
| `data/processed/province_month_panel.csv` | Ready | Main merged dashboard panel |

### Processing flow

Monthly panel pipeline:

1. `scripts/02_clean_rainfall.py`
2. `scripts/03_clean_water.py`
3. `scripts/04_clean_exposure.py`
4. `scripts/05_build_panel.py`

Daily feature pipeline:

1. `scripts/build_daily_extreme_features.py`
2. `scripts/merge_daily_features_into_panel.py`

Modeling pipeline:

1. `modeling/split_data.py`
2. `modeling/train_all_models.ipynb`
3. `modeling/result/*_forecast_next_12_months.csv`

## ML Forecasting Status

The forecasting workflow is already integrated into the app as an exploratory preview.

Current model framing:

- province-level forecasting
- two-stage recursive daily prediction
- `XGBoost` for rain occurrence and rainfall amount
- recent-weighted fitting on the most recent `15 years` of valid feature rows
- feature groups include lags, rolling rainfall statistics, wet/dry streak memory, and seasonal encodings

Current app-side presentation improvements:

- the `ML Prediction` tab explains what the model predicts
- it states what data and feature families are used
- it shows the selected display horizon
- it states that the preview is exploratory and does not expose held-out accuracy metrics in the UI yet

## Application Architecture Snapshot

```text
Raw monthly data ─┐
                  ├─> monthly cleaning scripts ─┐
Raw water data ───┘                             │
                                                ├─> province_month_panel.csv ─┐
Exposure data ──────────────────────────────────┘                             │
                                                                              ├─> app_refactored.py
Raw daily rainfall ─> daily feature pipeline ─────────────────────────────────┘
Raw daily rainfall ─> split_data.py ─> train_all_models.ipynb ─> modeling/result/*.csv
```

## Reproducibility Status

Current reproducibility posture:

- the main app entry point is clear: `app_refactored.py`
- the processed panel and forecast result files already exist in-repo
- `requirements.txt` is pinned to the versions currently installed in the local environment

Current limitation:

- `chun/` appears to be a local virtual environment kept inside the repo
- notebook execution environment details are still lighter than the app environment story

Recommended submission stance:

- keep `app_refactored.py` as the documented app entry point
- treat `app.py` as a legacy reference file
- avoid claiming the repository is environment-clean while `chun/` remains committed

## Documentation Alignment Checklist

These items should stay consistent across `README.md`, the final report, and the presentation:

- the app is observational and exploratory, not an official prediction tool
- surface water is a proxy observation, not direct flood-impact measurement
- daily rainfall is used both for monthly feature engineering and the forecast preview
- the current app has six tabs, including `ML Prediction`
- forecast outputs come from `modeling/result/`
- the app does not yet present formal held-out model accuracy metrics

## Teamwork Evidence Status

Visible Git history exists, but it is not yet a clean final contribution story.

Observed author identities in `git shortlog -sne HEAD`:

| Commits | Author identity |
|---|---|
| 19 | `jimmytrn154 <chuong033679@stu.vinschool.edu.vn>` |
| 9 | `Jimmy Tran <125101569+jimmytrn154@users.noreply.github.com>` |
| 3 | `Mancupfire <mancupsea@gmail.com>` |
| 1 | `chikien07012006 <kienduong160@gmail.com>` |

Implications:

- one contributor appears under multiple Git identities
- commit counts alone are not enough evidence for balanced teamwork

### Submission-ready contribution matrix

This should be confirmed by the team before final submission.

| Team member | Data collection / cleaning | Dashboard / UI | Modeling | Documentation / presentation | Evidence |
|---|---|---|---|---|---|
| Member 1 | Confirm | Confirm | Confirm | Confirm | PRs, commits, report sections |
| Member 2 | Confirm | Confirm | Confirm | Confirm | PRs, commits, report sections |
| Member 3 | Confirm | Confirm | Confirm | Confirm | PRs, commits, report sections |

### Teamwork actions still needed

1. Normalize Git author identity before final submission if possible.
2. Fill the contribution matrix with confirmed ownership.
3. Mirror that same ownership story in slides or report appendix.

## Remaining Submission Tasks

| Priority | Task | Status | Notes |
|---|---|---|---|
| High | Run final end-to-end app check | Pending | Verify tabs, interactions, and forecast tab behavior |
| High | Align report wording with current dashboard | Pending | Match README and app scope exactly |
| High | Finalize contribution matrix | Pending | Needs confirmed teammate ownership |
| Medium | Add one final demo script / walkthrough | Pending | Useful for live rubric coverage |
| Medium | Decide whether to expose explicit validation metrics in-app | Optional | Only if a reliable metric artifact is available |
| Low | Clean or archive legacy files | Optional | `app.py`, `old/`, and local env artifacts are non-critical |

## Useful Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the dashboard:

```bash
shiny run --reload app_refactored.py
```

Rebuild the monthly panel:

```bash
python scripts/02_clean_rainfall.py
python scripts/03_clean_water.py
python scripts/04_clean_exposure.py
python scripts/05_build_panel.py
```

Rebuild daily-derived monthly features:

```bash
python scripts/build_daily_extreme_features.py
python scripts/merge_daily_features_into_panel.py
```

Regenerate per-province modeling files:

```bash
python modeling/split_data.py
```
