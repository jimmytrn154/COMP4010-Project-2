# Implementation Plan: Add “Xâm nhập mặn” / Salinity Intrusion Risk Feature

## 1. Feature Goal

Add a new dashboard feature for **xâm nhập mặn** (salinity intrusion risk) to Mekong FloodLens.

The feature should estimate **province-month salinity intrusion risk** for the Vietnamese Mekong Delta using Google Earth Engine data, then merge the result into the existing dashboard pipeline.

This should be presented as a **remote-sensing salinity-risk proxy**, not as official measured salinity intrusion, unless later calibrated with ground salinity station data.

---

## 2. Why This Feature Fits the Project

The current dashboard already focuses on Mekong Delta water-risk visualization using:

- Rainfall from CHIRPS
- Surface-water / flood-proxy data from JRC Global Surface Water
- Cropland exposure from ESA WorldCover
- Population exposure from WorldPop
- Province boundaries from FAO GAUL

The existing project structure uses Google Earth Engine exports, cleaned Python scripts, processed CSV outputs, and a Shiny dashboard. Salinity intrusion can follow the same pattern.

This feature expands the project from **flood and drought risk** toward a broader **multi-hazard water-risk dashboard**, which is especially relevant for the Mekong Delta because salinity intrusion affects agriculture, water supply, and coastal livelihoods during dry-season months.

---

## 3. Recommended Data Source

### Primary Option: Sentinel-2 Surface Reflectance from Google Earth Engine

Use:

```javascript
COPERNICUS/S2_SR_HARMONIZED
```

Recommended time coverage:

```text
2017-present
```

Reason:

- Sentinel-2 has suitable spatial resolution for province-level aggregation.
- It supports monthly compositing.
- It can be processed in Google Earth Engine similarly to previous datasets.
- It can generate salinity-related spectral proxy indicators.

Important limitation:

Sentinel-2 does **not directly measure water salinity**. It can only estimate salinity-related land/water stress proxies using spectral patterns.

---

## 4. Alternative Data Source

### Optional Context Layer: Global Soil Salinity Maps

Use:

```javascript
ee.ImageCollection("projects/sat-io/open-datasets/global_soil_salinity")
```

This dataset can provide historical soil salinity context, but it is not ideal for the main dashboard panel because it has limited year coverage and does not provide continuous province-month observations.

Recommended use:

- Static or historical context layer
- Background map
- Report discussion
- Optional validation/comparison layer

Not recommended as the main monthly dashboard feature.

---

## 5. Proposed Raw Data Output

Add a new raw CSV file:

```text
data/raw/mekong_province_month_salinity_2017_2025.csv
```

Suggested columns:

```text
province_name
year
month
date
salinity_index_mean
salinity_index_median
salinity_index_p75
salinity_risk_area_km2
salinity_risk_pct
valid_pixel_count
```

Where:

- `salinity_index_mean`: average salinity proxy value by province-month
- `salinity_index_median`: median proxy value by province-month
- `salinity_index_p75`: upper-quartile salinity proxy value, useful for detecting concentrated stress
- `salinity_risk_area_km2`: estimated area above a chosen salinity-risk threshold
- `salinity_risk_pct`: salinity-risk area divided by province area
- `valid_pixel_count`: quality-control field after cloud masking

---

## 6. Suggested Salinity Proxy Indices

Use one or more simple spectral indices from Sentinel-2 bands.

### Option A: Basic Salinity Index

```text
SI = sqrt(Blue * Red)
```

Sentinel-2 bands:

```text
Blue = B2
Red = B4
```

### Option B: Normalized Salinity Proxy

```text
NDSI_salinity = (Red - NIR) / (Red + NIR)
```

Sentinel-2 bands:

```text
Red = B4
NIR = B8
```

### Option C: Cropland-Masked Salinity Stress

Because the project already has cropland exposure, salinity should ideally focus on agricultural impact.

Possible approach:

1. Use ESA WorldCover cropland class as a mask.
2. Calculate salinity proxy only inside cropland areas.
3. Aggregate by province-month.

This creates a stronger project narrative:

```text
salinity risk affecting agricultural exposure
```

---

## 7. Google Earth Engine Workflow

### Step 1: Load Mekong Province Boundaries

Use the same FAO GAUL province boundary approach already used in the project.

Target provinces:

```text
13 Vietnamese Mekong Delta provinces
```

### Step 2: Load Sentinel-2 Surface Reflectance

Use:

```javascript
var s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
  .filterBounds(mekongProvinces)
  .filterDate("2017-01-01", "2025-12-31");
```

### Step 3: Apply Cloud Mask

Use the Sentinel-2 scene classification layer or cloud probability method.

Minimum requirement:

- Remove cloud pixels
- Remove cloud shadow pixels
- Remove invalid/no-data pixels

### Step 4: Build Monthly Composite

For each year-month:

```text
monthly_image = median cloud-masked Sentinel-2 image
```

### Step 5: Calculate Salinity Proxy

Example:

```javascript
var blue = image.select("B2").multiply(0.0001);
var red = image.select("B4").multiply(0.0001);
var nir = image.select("B8").multiply(0.0001);

var si = blue.multiply(red).sqrt().rename("salinity_index");
var ndsiSalinity = red.subtract(nir).divide(red.add(nir)).rename("ndsi_salinity");
```

### Step 6: Create Salinity-Risk Area

Choose a threshold after inspecting the distribution.

Example placeholder:

```text
salinity_risk = salinity_index > threshold
```

Then calculate:

```text
salinity_risk_area_km2
salinity_risk_pct
```

Important:

The threshold should be documented as a heuristic unless validated with observed salinity data.

### Step 7: Export Province-Month Table

Export as CSV to Google Drive, then place it into:

```text
data/raw/mekong_province_month_salinity_2017_2025.csv
```

---

## 8. New Cleaning Script

Add:

```text
scripts/06_clean_salinity.py
```

Responsibilities:

1. Read the raw GEE salinity CSV.
2. Standardize province names.
3. Convert `year`, `month`, and `date`.
4. Check missing values.
5. Remove invalid observations with too few valid pixels.
6. Create normalized salinity score.
7. Save processed output.

Output:

```text
data/processed/province_month_salinity.csv
```

Suggested processed columns:

```text
province_name
year
month
date
salinity_index_mean
salinity_index_p75
salinity_risk_area_km2
salinity_risk_pct
salinity_score
```

Example normalization:

```text
salinity_score = minmax(salinity_risk_pct)
```

Alternative:

```text
salinity_score = minmax(salinity_index_p75)
```

Recommended:

Use `salinity_risk_pct` if the threshold is reliable. Otherwise, use `salinity_index_p75` as a more conservative proxy.

---

## 9. Update Panel-Building Script

Update:

```text
scripts/05_build_panel.py
```

Current merge logic should be extended to include salinity data.

Merge key:

```text
province_name + year + month
```

Add:

```python
salinity = pd.read_csv("data/processed/province_month_salinity.csv")

panel = panel.merge(
    salinity,
    on=["province_name", "year", "month"],
    how="left"
)
```

Because Sentinel-2 starts later than rainfall and surface-water data, salinity columns will be missing before 2017.

Recommended handling:

```text
Do not fill pre-2017 salinity values with 0 in the raw panel.
Only fill or normalize them inside dashboard logic when needed.
```

This avoids falsely implying that earlier years had no salinity risk.

---

## 10. Update Dashboard

Update:

```text
app_refactored.py
```

### 10.1 Add Metric Selector Option

Add a new option:

```text
Salinity intrusion risk
```

Possible internal value:

```python
"salinity_score"
```

### 10.2 Add KPI Card

Add one KPI card such as:

```text
Average salinity risk score
```

or:

```text
Estimated high-salinity-risk area
```

Recommended KPI:

```text
High-salinity-risk area (km²)
```

### 10.3 Add Map Layer

Allow the province map to color by:

```text
salinity_score
salinity_risk_pct
salinity_index_p75
```

### 10.4 Add Dry-Season Filter or Annotation

Salinity intrusion is most relevant in the dry season.

Recommended dry-season months:

```text
December, January, February, March, April
```

Add either:

- A dry-season-only checkbox
- A note in the dashboard
- A chart that highlights dry-season months

### 10.5 Add Trend Chart

Add a chart:

```text
Province salinity risk trend over time
```

Suggested x-axis:

```text
date
```

Suggested y-axis:

```text
salinity_score
```

Suggested grouping:

```text
province_name
```

### 10.6 Add Heatmap

Add or reuse anomaly heatmap format:

```text
province_name x month/year
```

Metric:

```text
salinity_score
```

---

## 11. Risk Score Design

Do not directly mix salinity into the existing flood/drought score at first.

Recommended structure:

```text
combined_risk_score = existing flood/drought/exposure score
salinity_score = separate salinity intrusion risk proxy
multi_hazard_score = optional combined score
```

Optional multi-hazard score:

```text
multi_hazard_score =
    0.75 * combined_risk_score
  + 0.25 * salinity_score
```

Reason:

- Flood risk and salinity intrusion are different hazards.
- Salinity is strongest during dry periods, not necessarily wet/flood periods.
- Keeping it separate makes the dashboard easier to explain.

---

## 12. Documentation Updates

Update:

```text
README.md
PROJECT_PROGRESS_UPDATED.md
```

### README Additions

Add salinity to the dataset table:

```text
Sentinel-2 salinity proxy | mekong_province_month_salinity_2017_2025.csv | 2017-2025 | Province-month | Salinity intrusion risk proxy
```

Add caveat:

```text
The salinity intrusion feature is a satellite-derived proxy. It should not be interpreted as measured water salinity or official salinity intrusion depth without ground-station validation.
```

### Progress Log Additions

Add tasks:

```text
- Export Sentinel-2 salinity proxy from Google Earth Engine
- Clean province-month salinity data
- Merge salinity into province-month panel
- Add salinity metric to dashboard
- Add caveat explaining proxy interpretation
```

---

## 13. Validation Plan

Minimum validation:

1. Check whether high salinity proxy values appear mainly in coastal provinces.
2. Check whether values are higher in dry-season months.
3. Compare trends against known severe salinity years if available.
4. Check whether inland provinces have lower values than coastal provinces.
5. Compare salinity proxy with rainfall drought signal.

Expected pattern:

```text
High salinity risk should be more visible in dry months and coastal provinces.
```

Coastal provinces likely to pay special attention to:

```text
Ben Tre
Tra Vinh
Soc Trang
Bac Lieu
Ca Mau
Kien Giang
Tien Giang
Long An
```

---

## 14. Implementation Order

### Phase 1: Data Export

- Write GEE script for Sentinel-2 monthly composites.
- Calculate salinity proxy index.
- Aggregate by province-month.
- Export raw CSV.

### Phase 2: Data Cleaning

- Add `scripts/06_clean_salinity.py`.
- Standardize columns and province names.
- Calculate `salinity_score`.
- Save processed CSV.

### Phase 3: Panel Integration

- Update `scripts/05_build_panel.py`.
- Merge salinity data into `province_month_panel.csv`.
- Confirm missing values before 2017 are handled correctly.

### Phase 4: Dashboard Update

- Add salinity metric to selector.
- Add salinity KPI card.
- Add salinity map option.
- Add salinity trend or heatmap.
- Add explanatory tooltip/caveat.

### Phase 5: Documentation

- Update README.
- Update progress log.
- Mention limitations in final report/presentation.

---

## 15. Suggested File Changes

```text
data/raw/
  + mekong_province_month_salinity_2017_2025.csv

data/processed/
  + province_month_salinity.csv
  ~ province_month_panel.csv

scripts/
  + 06_clean_salinity.py
  ~ 05_build_panel.py

app_refactored.py
  ~ add salinity metric, KPI, map layer, and chart

README.md
  ~ add salinity dataset documentation and caveat

PROJECT_PROGRESS_UPDATED.md
  ~ add implementation progress
```

---

## 16. Recommended Final Wording for the Dashboard

Use:

```text
Salinity intrusion risk proxy
```

Avoid:

```text
Measured salinity intrusion
Official salinity intrusion
Confirmed salinity impact
```

Recommended tooltip:

```text
This layer estimates salinity intrusion risk using satellite-derived spectral proxy indicators. It is intended for relative screening across provinces and months, not as official measured water salinity.
```

---

## 17. Final Recommendation

Implement **xâm nhập mặn** as a separate dashboard feature first, not as a direct replacement for the existing combined risk score.

Best first version:

```text
Sentinel-2 monthly province-level salinity-risk proxy, 2017-2025
```

Best dashboard output:

```text
Map + KPI + dry-season trend chart
```

Best interpretation:

```text
Relative salinity intrusion risk screening for Mekong Delta provinces
```
