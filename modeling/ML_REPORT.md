# ML Forecasting Report

## Scope

This report documents the machine-learning forecasting layer added to the Mekong Lens Python Shiny dashboard for three prediction tasks:

1. Monthly Combined Risk Score
2. Rainfall Anomaly (`rainfall_zscore`)
3. Water Area (`water_area_pct`)

The canonical training notebooks are:

- [Monthly Combined Risk Score notebook](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Monthly%20Combined%20Risk%20Score/training.ipynb)
- [Rainfall Anomaly notebook](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Rainfall%20Anomaly/training.ipynb)
- [Water Area notebook](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Water%20Area/training.ipynb)

## Data analysis summary

- Source dataset: [province_month_panel.csv](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/data/processed/province_month_panel.csv:1)
- Panel size: 7,020 province-month rows across 13 Mekong Delta provinces
- Rainfall anomaly coverage: 1981-01 to 2025-12
- Water-area coverage: 1984-03 to 2021-12
- Population coverage: 2000-01 to 2020-12
- Cropland coverage: 2021 only

Because the panel is strongly seasonal and relatively small, the forecasting approach was designed as a recursive one-step-ahead panel forecaster with time-based validation rather than a random split.

## Feature engineering

The same overall recipe was used across all three tasks, with task-specific known covariates layered on top.

Common features:

- Current target value as the immediate autoregressive anchor
- Lagged target features at 1, 2, 3, 6, and 12 months
- Rolling mean, standard deviation, minimum, and maximum over 3, 6, and 12 months
- Month-over-month and year-over-year change features (`diff_lag_1`, `diff_lag_12`)
- Forecast-month seasonality encoding with `month_sin`, `month_cos`, and quarter
- `time_idx` and forecast year to capture long-run drift
- Province one-hot encoding through the preprocessing pipeline
- Province-level and province-month historical target averages as climatology-style priors

Task-specific additions:

- Combined Risk Score:
  - Forecast-month rainfall climatology from `monthly_mean`
  - Province-month water climatology
  - Province-level exposure priors from population, cropland, and the derived `exposure_score`
- Rainfall Anomaly:
  - Forecast-month rainfall climatology from `monthly_mean`
  - Province-month rainfall-zscore priors
- Water Area:
  - Forecast-month rainfall climatology from `monthly_mean`
  - Province-level and province-month water-area percentage priors

Design choice:

- Models are trained to predict the next month (`t+1`) from information available at month `t`.
- Multi-month forecasts in the dashboard are produced recursively: each new prediction is appended to the target history and used to generate the next step.

## Train/test strategy

- Split method: 80/20 by time using ordered unique prediction dates
- No random shuffling
- Evaluation metrics: MAE, RMSE, R2

This setup keeps the benchmark closer to real dashboard usage, where the model must forecast future months from past observations only.

## Benchmarking results

### Task 1: Monthly Combined Risk Score

| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| Linear Regression | 0.0466 | 0.0562 | 0.3845 |
| Random Forest | 0.0679 | 0.0867 | -0.4678 |
| XGBoost | 0.0719 | 0.0880 | -0.5127 |
| LightGBM | 0.0799 | 0.0976 | -0.8576 |

Selected model: `Linear Regression`

Reason:

- Lowest RMSE and MAE
- Only model with clearly positive R2
- Stable choice for a bounded, relatively smooth heuristic score

Artifacts:

- Metrics CSV: [benchmark_metrics.csv](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Monthly%20Combined%20Risk%20Score/results/benchmark_metrics.csv)
- Benchmark chart: [benchmark_metrics.png](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Monthly%20Combined%20Risk%20Score/results/benchmark_metrics.png)
- Saved model: [best_model.pkl](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Monthly%20Combined%20Risk%20Score/models/best_model.pkl)

### Task 2: Rainfall Anomaly (`rainfall_zscore`)

| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| Linear Regression | 0.7919 | 0.9890 | -0.0028 |
| XGBoost | 1.2503 | 1.4454 | -1.1421 |
| Random Forest | 1.2731 | 1.4661 | -1.2038 |
| LightGBM | 1.3138 | 1.5100 | -1.3378 |

Selected model: `Linear Regression`

Reason:

- Best RMSE and MAE by a large margin
- Although R2 is close to zero, it still outperforms the non-linear models on this panel
- Suggests rainfall z-score is noisy and difficult to model beyond seasonal priors and recent lags

Artifacts:

- Metrics CSV: [benchmark_metrics.csv](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Rainfall%20Anomaly/results/benchmark_metrics.csv)
- Benchmark chart: [benchmark_metrics.png](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Rainfall%20Anomaly/results/benchmark_metrics.png)
- Saved model: [best_model.pkl](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Rainfall%20Anomaly/models/best_model.pkl)

### Task 3: Water Area (`water_area_pct`)

| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| Linear Regression | 3.8926 | 5.6639 | 0.5835 |
| Random Forest | 4.0128 | 6.2593 | 0.4913 |
| LightGBM | 4.3226 | 7.0233 | 0.3596 |
| XGBoost | 4.4527 | 7.2926 | 0.3095 |

Selected model: `Linear Regression`

Reason:

- Lowest RMSE and MAE
- Highest R2
- Best fit for the relatively smooth seasonal structure of the water-area percentage series

Artifacts:

- Metrics CSV: [benchmark_metrics.csv](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Water%20Area/results/benchmark_metrics.csv)
- Benchmark chart: [benchmark_metrics.png](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Water%20Area/results/benchmark_metrics.png)
- Saved model: [best_model.pkl](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/modeling/Water%20Area/models/best_model.pkl)

## Model selection summary

| Task | Selected model | Why it won |
|---|---|---|
| Combined Risk Score | Linear Regression | Best RMSE/MAE and positive R2 |
| Rainfall Anomaly | Linear Regression | Lowest errors; tree models overfit the panel |
| Water Area | Linear Regression | Best RMSE/MAE and strongest R2 |

Overall interpretation:

- The forecasting panel is modest in size and heavily seasonal.
- Simple linear structure plus lagged/seasonal features generalized better than the more flexible tree ensembles.
- The non-linear models likely overfit province-specific fluctuations under the strict time split.

## Dashboard visualization

The dashboard now includes a new section in [app_refactored.py](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/app_refactored.py:692) named `Future risk forecast`.

It provides:

- Task selector: Combined Risk / Rainfall Anomaly / Water Area
- Forecast horizon selector: 1 to 12 months
- Province multi-select
- Predicted hotspot map colored by average forecast across the selected horizon
- Historical + forecast trend chart with solid history and dashed forecast lines
- Top-5 hotspot ranking across the selected forecast window
- Detailed province-month prediction table

Visualization logic:

- Models are loaded from each task's `models/best_model.pkl`
- Forecasts are generated recursively from the latest available province history
- The map aggregates forecast values to province-level averages over the chosen horizon
- The top-5 view ranks provinces by the same aggregated predicted score

Screenshot note:

- A screenshot was not auto-captured in this run, but the forecast section starts successfully when the app is launched locally with `shiny run --reload app_refactored.py`.

## How to rerun training

Recommended:

1. Open the notebook for the task you want to retrain.
2. Run all cells using the same Python environment that runs `shiny`.
3. Confirm the outputs are written into that task's `results/` and `models/` folders.

Important environment note:

- On this machine, `shiny` uses Python 3.8.
- Model artifacts should be trained and saved from the same Python environment to avoid `joblib`/`scikit-learn` version mismatch during dashboard startup.

Optional command-line shortcut:

```bash
c:\users\administrator\appdata\local\programs\python\python38\python.exe -c "from modeling.forecasting_utils import run_training_workflow; run_training_workflow('combined_risk')"
c:\users\administrator\appdata\local\programs\python\python38\python.exe -c "from modeling.forecasting_utils import run_training_workflow; run_training_workflow('rainfall_anomaly')"
c:\users\administrator\appdata\local\programs\python\python38\python.exe -c "from modeling.forecasting_utils import run_training_workflow; run_training_workflow('water_area')"
```

## How to use on the dashboard

1. Install dependencies from [requirements.txt](/C:/Users/Administrator/Desktop/DataViz_FinalPrj/COMP4010-Project-2/requirements.txt:1).
2. Start the app:

```bash
shiny run --reload app_refactored.py
```

3. Scroll to `Future risk forecast`.
4. Pick a task, horizon, and one or more provinces.
5. Use the map for spatial comparison and the trend chart for temporal interpretation.

