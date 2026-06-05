# ML Forecasting Report

## Overview

This document summarizes the forecasting workflow implemented in [train_all_models.ipynb](C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/train_all_models.ipynb:1).

The current forecasting design uses one separate province-level pipeline for each of the 13 Mekong Delta provinces. The selected approach is:

- `two-stage daily forecasting`
- `recent-weighted training`
- `recursive daily prediction for the full 12-month horizon`
- `XGBoost` for both rain occurrence and rainfall amount

This design was chosen to make predictions look more like recent historical behavior instead of being pulled too strongly toward long-run climatology.

## Data Used

Input source:

- `data/raw/mekong_province_day_rainfall_1981_2025.csv`

Province-level modeling inputs:

- `modeling/data_splitted/*_rainfall_1981_2025.csv`

Each province file keeps the original structure:

- `province_name`
- `date`
- `year`
- `month`
- `day`
- `rainfall_mm`

## Training and Prediction Timeline

The raw rainfall history spans:

- Start date: `1981-01-01`
- End date: `2025-12-31`

However, the final model does **not** train equally on the entire historical period.

### Effective training window

For each province, the notebook first builds features using the full historical sequence, then keeps the most recent:

- `15 years` of valid feature rows

So the model is effectively trained on the recent period only, while still allowing long lags such as `lag_365` to be computed correctly.

### Forecast window

The forecast horizon is:

- Start date: `2026-01-01`
- End date: `2026-12-31`

This produces one predicted daily rainfall value for each day in the next 12 months.

## Forecasting Strategy

## 1. Two-stage prediction

Instead of using one single regression model, the workflow separates the task into two parts.

### Stage 1: Rain occurrence

Predict whether rain occurs on day `t`.

Target:

- `rain_occurrence = 1 if rainfall_mm >= 1.0 else 0`

Model:

- `XGBClassifier`

This stage controls how often the forecast produces rainy days.

### Stage 2: Rainfall amount

If the classifier predicts rain, a second model estimates how much rain falls.

Target:

- `sqrt(rainfall_mm)`

Model:

- `XGBRegressor`

The square-root target was selected because it usually preserves medium and large rainfall events better than a strongly compressed log target when the previous model underpredicts too much.

## 2. Full recursive daily forecasting

The model predicts the full horizon day by day.

For each future day:

1. Build features from the latest available sequence
2. Predict rain probability
3. Apply a tuned rain/no-rain threshold
4. If rain is predicted, estimate rainfall amount
5. Convert the square-root target back to rainfall in `mm`
6. Append the predicted rainfall back into history
7. Continue to the next future day

This means all forecast rows are produced by:

- `prediction_stage = recursive_daily`

There is no monthly-profile disaggregation in the current version.

## Feature Engineering

The notebook includes the following feature groups.

## 1. Lag features

The daily lags are:

- `lag_1`
- `lag_2`
- `lag_3`
- `lag_7`
- `lag_12`
- `lag_14`
- `lag_21`
- `lag_30`
- `lag_60`
- `lag_90`
- `lag_365`

These capture short-term persistence, seasonal recurrence, and long-memory behavior.

## 2. Rolling statistics

For windows `7`, `12`, and `30` days, the notebook computes:

- rolling mean
- rolling standard deviation
- rolling sum
- rolling maximum
- rolling minimum

Examples:

- `rolling_mean_7`
- `rolling_std_30`
- `rolling_sum_12`
- `rolling_max_30`
- `rolling_min_7`

## 3. Rolling rain-day counts

The notebook also counts rainy days in recent windows:

- `rolling_rain_count_7`
- `rolling_rain_count_14`
- `rolling_rain_count_30`

These help the model distinguish active wet periods from dry periods.

## 4. Rain-state memory

The event-state features are:

- `days_since_last_rain`
- `wet_streak_prev`
- `dry_streak_prev`

These describe how long the current wet or dry regime has lasted before the prediction day.

## 5. Seasonal features

The seasonal features are:

- `month_sin`
- `month_cos`
- `day_of_year_sin`
- `day_of_year_cos`
- `quarter`
- `season_4`
- `is_rainy_season`

These encode cyclical seasonality and monsoon timing.

## Recent-Weighted Training

The main modeling change in this version is that the model is intentionally biased toward recent rainfall behavior.

This happens in two ways:

### 1. Recent-year filtering

Only the most recent `15 years` of feature rows are used for fitting.

### 2. Sample weighting

The notebook assigns larger sample weights to:

- newer observations
- rainy days
- heavy-rain days
- extreme-rain days

For the rainfall-amount regressor, the sample weights are even larger for stronger rainfall events. This is intended to reduce the tendency to underpredict large rainfall values.

## Threshold and Amount Calibration

To make forecasts less conservative, the pipeline includes two calibration steps.

### 1. Rain threshold tuning

The rain/no-rain threshold is not fixed at `0.50`.

Instead, it is selected from a lower threshold grid:

- `0.18`
- `0.22`
- `0.26`
- `0.30`
- `0.34`
- `0.38`

The best threshold is chosen using a validation score based on:

- `F-beta` with `beta = 2`

This favors recall more than standard F1, so the model is less likely to miss rainy days.

### 2. Amount scaling

After the regressor is tuned on a validation slice, the notebook estimates a simple multiplicative scale factor:

- `amount_scale`

This scale adjusts predictions upward or downward so that rainy-day forecast magnitudes are less biased low on the validation period.

## Internal Validation

The notebook uses a chronological validation slice near the end of the recent training window.

This validation is used only for model selection and calibration:

- classifier tuning: `F-beta` and `log loss`
- regressor tuning: rainy-day `MAE`
- threshold selection
- amount scaling

This is not a benchmark report. It is an internal stability step before retraining on the full recent window.

## Output Files

Per-province outputs are saved in [result](C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/result:1), for example:

- [an_giang_forecast_next_12_months.csv](C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/result/an_giang_forecast_next_12_months.csv:1)
- [vinh_long_forecast_next_12_months.csv](C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/result/vinh_long_forecast_next_12_months.csv:1)

The combined export is:

- [all_provinces_forecast_next_12_months.csv](C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/result/all_provinces_forecast_next_12_months.csv:1)

Current output columns:

- `province_name`
- `date`
- `year`
- `month`
- `day`
- `predicted_rainfall_mm`
- `rain_probability`
- `prediction_stage`
- `model_name`

## Notes

- The workflow still uses only rainfall history, so forecast realism is still limited by the absence of external climate drivers.
- The current version is designed to better match recent rainfall behavior than the earlier long-horizon smoothing approach.
- Output filenames were kept unchanged so the dashboard can continue using the same result files.
