# Daily Rainfall Update — Mekong FloodLens

## Purpose

This document summarizes the recent change to extend the rainfall pipeline from monthly rainfall aggregation to daily rainfall extraction and daily-derived monthly extreme indicators.

The goal is not to replace the monthly dashboard structure. Daily rainfall is added as a supporting layer so the dashboard can explain whether a risky month is driven by many rainy days, one extreme rainfall event, or long dry spells.

## Why We Added Daily Rainfall

The existing dataset `mekong_province_month_rainfall_1981_2025.csv` gives monthly rainfall totals by province. This is useful for long-term patterns, seasonal comparison, anomaly analysis, and dashboard overview.

However, monthly rainfall alone cannot explain the internal structure of a month. Two provinces may have the same monthly rainfall total, but one may have steady rainfall across many days while the other may have one extreme rainfall event. Daily rainfall allows us to compute indicators such as rainy days, heavy-rain days, maximum one-day rainfall, and longest dry spell.

## New Raw Dataset

Planned raw output:

```text
data/raw/mekong_province_day_rainfall_1981_2025.csv
```

Expected structure:

```text
province_name
date
year
month
day
rainfall_mm
```

Each row represents:

```text
1 province × 1 day
```

Expected approximate size:

```text
13 provinces × 45 years × 365 days ≈ 213,000 rows
```

## Google Earth Engine Extraction Logic

The extraction uses CHIRPS Daily rainfall:

```javascript
ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
```

The planned date range is:

```text
1981-01-01 to 2026-01-01
```

Because Earth Engine uses an exclusive end date, this covers complete years:

```text
1981–2025
```

For each daily CHIRPS image, rainfall is spatially averaged across the 13 Mekong Delta province boundaries using `reduceRegions`. The exported table contains daily province-level rainfall values.

## New Processed Dataset

Daily rainfall will be transformed into monthly extreme indicators.

Expected processed output:

```text
data/processed/province_month_rainfall_features.csv
```

Expected structure:

```text
province_name
year
month
rainfall_mm_from_daily
mean_daily_rainfall
max_1day_rainfall
rain_days_count
dry_days_count
heavy_rain_days_20mm
heavy_rain_days_50mm
max_consecutive_dry_days
max_consecutive_wet_days
rain_day_ratio
dry_day_ratio
days_observed
```

Each row represents:

```text
1 province × 1 month
```

Expected row count:

```text
13 provinces × 45 years × 12 months = 7020 rows
```

## Feature Definitions

| Feature | Meaning |
|---|---|
| `rainfall_mm_from_daily` | Monthly rainfall total recomputed from daily rainfall |
| `mean_daily_rainfall` | Average daily rainfall within the month |
| `max_1day_rainfall` | Highest rainfall observed in a single day in that month |
| `rain_days_count` | Number of days with rainfall greater than or equal to 1 mm |
| `dry_days_count` | Number of days with rainfall below 1 mm |
| `heavy_rain_days_20mm` | Number of days with rainfall greater than or equal to 20 mm |
| `heavy_rain_days_50mm` | Number of days with rainfall greater than or equal to 50 mm |
| `max_consecutive_dry_days` | Longest consecutive dry-day sequence within the month |
| `max_consecutive_wet_days` | Longest consecutive rainy-day sequence within the month |
| `rain_day_ratio` | Share of observed days that are rainy days |
| `dry_day_ratio` | Share of observed days that are dry days |
| `days_observed` | Number of daily observations available for the province-month |

## New Processing Scripts

### `scripts/03_build_daily_extreme_features.py`

Purpose:

- Read raw province-day rainfall data.
- Create daily rainfall flags.
- Aggregate daily observations into province-month indicators.
- Compute extreme rainfall and dry/wet spell features.
- Export `province_month_rainfall_features.csv`.

### `scripts/04_merge_daily_features_into_panel.py`

Purpose:

- Read `province_month_panel.csv`.
- Read `province_month_rainfall_features.csv`.
- Merge by `province_name`, `year`, and `month`.
- Back up the previous panel.
- Write the updated `province_month_panel.csv`.

Expected backup:

```text
data/processed/province_month_panel_before_daily_features.csv
```

## Merge Strategy

The daily-derived monthly features are merged into the main dashboard table:

```text
province_month_panel.csv
```

Merge key:

```text
province_name + year + month
```

Pipeline:

```text
mekong_province_day_rainfall_1981_2025.csv
→ province_month_rainfall_features.csv
→ merge into province_month_panel.csv
```

This keeps the dashboard at monthly resolution while allowing it to display daily-derived extreme rainfall indicators.

## Dashboard Implications

The dashboard should remain monthly by default. Daily data should support extra analytical metrics rather than become the main display level.

Recommended new dashboard metrics:

```text
max_1day_rainfall
heavy_rain_days_20mm
heavy_rain_days_50mm
max_consecutive_dry_days
rain_days_count
dry_days_count
```

Possible uses:

| Dashboard component | Use |
|---|---|
| Map | Show provinces with high one-day rainfall or long dry spells |
| Ranking chart | Rank provinces by extreme rain days |
| KPI cards | Display maximum one-day rainfall or longest dry spell |
| Trend chart | Track monthly extreme rainfall indicators |
| Heatmap | Show heavy-rain-day or dry-spell patterns across provinces and months |
| Province comparison | Compare selected month against historical averages |

## Analytical Value

Monthly rainfall tells us:

```text
How wet or dry was this province-month overall?
```

Daily-derived indicators tell us:

```text
Why was it risky?
```

For example, a month may be risky because of many rainy days, one extreme rainfall day, or long dry spells. This gives Mekong FloodLens a stronger analytical story.

## Important Limitation

Daily rainfall is only available for the CHIRPS rainfall layer in the current project design.

Other datasets remain at coarser temporal resolutions:

| Dataset | Resolution |
|---|---|
| CHIRPS rainfall | Daily, aggregated to monthly |
| JRC Global Surface Water | Monthly |
| WorldPop | Yearly |
| ESA WorldCover | Static 2021 snapshot |
| FAO GAUL boundaries | Static |

Therefore, the final dashboard should not force all layers into daily resolution. The recommended design is:

```text
Monthly dashboard backbone + daily-derived rainfall indicators
```

## Current Next Steps

1. Export `mekong_province_day_rainfall_1981_2025.csv` from Google Earth Engine.
2. Add `scripts/03_build_daily_extreme_features.py`.
3. Generate `province_month_rainfall_features.csv`.
4. Add `scripts/04_merge_daily_features_into_panel.py`.
5. Merge daily-derived indicators into `province_month_panel.csv`.
6. Update the Shiny dashboard metric selector to include extreme rainfall and dry-spell indicators.
7. Add a dashboard note explaining that daily data is used to create monthly extreme indicators.
