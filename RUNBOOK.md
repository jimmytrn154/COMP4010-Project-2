# Mekong FloodLens Runbook

This runbook is a quick operational guide for running, checking, and demoing the project after pulling the latest `main` branch.

## When to Use This File

Use this file when you need to:

- run the Shiny dashboard locally
- recover after pulling new code from `main`
- install or refresh dependencies
- check whether the app is ready for a demo or submission
- diagnose common local environment errors

For project background and data explanation, read `README.md` first. For current submission progress, read `PROJECT_PROGRESS_UPDATED.md`.

## Main Entry Point

The current dashboard entry point is:

```bash
app_refactored.py
```

Run it with:

```bash
shiny run --reload app_refactored.py
```

`app.py` is an older dashboard version kept for reference.

## Recommended Startup Flow

From the repository root:

```bash
git status
git pull origin main
pip install -r requirements.txt
shiny run --reload app_refactored.py
```

If you are on a feature branch and want to update it from `main`:

```bash
git fetch origin
git merge origin/main
pip install -r requirements.txt
```

Use `git rebase origin/main` instead of `git merge origin/main` only if the team is comfortable with rebasing.

## Virtual Environment Notes

If you use the local `venv` folder:

```bash
.\venv\Scripts\activate
pip install -r requirements.txt
```

If the terminal shows both `(venv)` and `(base)`, it means the Python virtual environment is active while Conda base is also loaded. This can still work, but if dependency behavior looks strange, check which Python and pip are being used:

```bash
where python
where pip
python -m pip --version
```

Prefer installing with:

```bash
python -m pip install -r requirements.txt
```

This reduces the chance of installing packages into the wrong Python environment.

## Common Errors

### `ModuleNotFoundError: No module named 'pydeck'`

Cause:

- the latest app imports `pydeck`
- the current virtual environment does not have it installed yet

Fix:

```bash
python -m pip install -r requirements.txt
```

If that still fails:

```bash
python -m pip install pydeck==0.8.0
```

This usually means the code is using a new dependency and the local environment has not been refreshed. It is not automatically a code bug.

### App starts but charts or maps are empty

Check that these files exist:

```text
data/processed/province_month_panel.csv
data/raw/mekong_provinces_boundary.geojson
modeling/result/
```

Also check whether the selected year/month/province combination has data. Some datasets have different coverage windows:

- rainfall: 1981-2025
- surface water: 1984-2021
- population exposure: 2000-2021
- cropland exposure: 2021 snapshot

### `FileNotFoundError`

Likely causes:

- command was run from the wrong directory
- expected processed data has not been generated
- a pulled branch changed file paths

First confirm you are in the repository root:

```bash
pwd
```

Then check the expected folders:

```bash
ls data/processed
ls modeling/result
```

On Windows PowerShell, use:

```powershell
Get-ChildItem data\processed
Get-ChildItem modeling\result
```

### Package version conflicts

Refresh the environment from the pinned requirements:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the environment is badly tangled, create a fresh virtual environment:

```bash
python -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Data Pipeline Quick Reference

Monthly processing:

```bash
python scripts/02_clean_rainfall.py
python scripts/03_clean_water.py
python scripts/04_clean_exposure.py
python scripts/05_build_panel.py
```

Daily feature processing:

```bash
python scripts/build_daily_extreme_features.py
python scripts/merge_daily_features_into_panel.py
```

Modeling workflow:

```text
modeling/split_data.py
modeling/train_all_models.ipynb
modeling/result/*_forecast_next_12_months.csv
```

Do not rerun modeling unless the team intentionally wants to regenerate forecast outputs.

## Demo Checklist

Before a live demo or submission check:

- pull the latest `main`
- install `requirements.txt`
- run `shiny run --reload app_refactored.py`
- open every dashboard tab
- test year, month, province, metric, and top-N filters
- click at least one province bar chart and confirm linked filtering works
- check the rainfall anomaly vs surface-water scatter interaction
- open the `ML Prediction` tab and confirm forecast output appears
- open the `Methodology / Caveats` tab and confirm the limitations are visible
- verify the app narrative says the project is exploratory, not an official warning system

## Submission Checklist

Before final submission, confirm:

- `README.md` matches the current app scope
- `PROJECT_PROGRESS_UPDATED.md` reflects final progress
- `requirements.txt` includes every imported package used by `app_refactored.py`
- the contribution matrix has real team member ownership
- final report and slides use the same dataset coverage dates as the dashboard
- no one claims formal operational flood prediction unless validation evidence is included

## Quick Dependency Audit

To check whether a package imported by the app is missing from `requirements.txt`, search the imports:

```bash
python -m pip freeze
```

Then compare against imports near the top of:

```text
app_refactored.py
```

Current important app dependencies include:

- pandas
- shiny
- plotly
- pydeck
- geopandas
- htmltools
- shinywidgets
- scikit-learn
- xgboost

## Team Rule of Thumb

After every pull from `main`, run:

```bash
python -m pip install -r requirements.txt
```

This prevents most local breakages caused by newly added dependencies.
