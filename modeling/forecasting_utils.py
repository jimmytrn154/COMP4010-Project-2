from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor


matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "province_month_panel.csv"


TASK_CONFIGS: dict[str, dict[str, Any]] = {
    "combined_risk": {
        "title": "Monthly Combined Risk Score",
        "folder": PROJECT_ROOT / "modeling" / "Monthly Combined Risk Score",
        "target_col": "combined_risk_score",
        "target_label": "Combined Risk Score",
        "summary_col": "combined_risk_score",
        "sort_ascending": False,
    },
    "rainfall_anomaly": {
        "title": "Rainfall Anomaly",
        "folder": PROJECT_ROOT / "modeling" / "Rainfall Anomaly",
        "target_col": "rainfall_zscore",
        "target_label": "Rainfall Z-Score",
        "summary_col": "rainfall_zscore",
        "sort_ascending": False,
    },
    "water_area": {
        "title": "Water Area",
        "folder": PROJECT_ROOT / "modeling" / "Water Area",
        "target_col": "water_area_pct",
        "target_label": "Water Area (%)",
        "summary_col": "water_area_pct",
        "sort_ascending": False,
    },
}


COMMON_LAGS = [1, 2, 3, 6, 12]
COMMON_WINDOWS = [3, 6, 12]
METRIC_ORDER = ["MAE", "RMSE", "R2"]


@dataclass
class TrainingArtifacts:
    task_key: str
    best_model_name: str
    artifact_path: Path
    metrics_path: Path
    chart_path: Path
    metrics_df: pd.DataFrame
    train_rows: int
    test_rows: int
    train_end: str
    test_start: str


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0)
    spread = values.max() - values.min()
    if spread == 0:
        return pd.Series(0, index=values.index)
    return (values - values.min()) / spread


def prepare_panel(panel_path: str | Path = PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(panel_path)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["month"] = pd.to_numeric(df["month"], errors="coerce").astype(int)
    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=1), errors="coerce"
    )

    default_columns = {
        "rainfall_mm": 0,
        "monthly_mean": np.nan,
        "rainfall_anomaly": 0,
        "rainfall_zscore": 0,
        "water_area_km2": np.nan,
        "water_area_pct": np.nan,
        "population_total": np.nan,
        "population_density_per_km2": np.nan,
        "cropland_area_km2": np.nan,
        "cropland_pct": np.nan,
        "combined_risk_score": np.nan,
    }

    for col, default in default_columns.items():
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df["monthly_mean"].isna().all():
        df["monthly_mean"] = (
            df.groupby(["province_name", "month"])["rainfall_mm"].transform("mean")
        )

    df["rainfall_score"] = minmax(df["rainfall_zscore"].clip(lower=0))
    df["water_score"] = minmax(df["water_area_pct"].fillna(0))
    df["drought_score"] = minmax((-df["rainfall_zscore"]).clip(lower=0))
    df["exposure_score"] = 0.6 * minmax(df["population_total"].fillna(0)) + 0.4 * minmax(
        df["cropland_area_km2"].fillna(0)
    )

    if df["combined_risk_score"].isna().all():
        df["combined_risk_score"] = (
            0.35 * df["water_score"]
            + 0.25 * df["rainfall_score"]
            + 0.25 * df["drought_score"]
            + 0.15 * df["exposure_score"]
        )

    return df.sort_values(["province_name", "date"]).reset_index(drop=True)


def feature_notes(task_key: str) -> list[str]:
    common = [
        "Autoregressive target features: current value plus lags 1, 2, 3, 6 and 12 months.",
        "Temporal stability features: rolling mean, std, min and max over 3, 6 and 12 months.",
        "Trend-change features: month-over-month and year-over-year deltas from lag 1 and lag 12.",
        "Seasonal features: forecast-month sine/cosine encoding, quarter and time index.",
        "Province encoding: one-hot province representation through the preprocessing pipeline.",
        "Historical priors: province-level and province-month target climatology.",
    ]

    task_specific = {
        "combined_risk": [
            "Known covariates: monthly rainfall climatology for the forecast month.",
            "Exposure priors: province-level population, cropland and exposure proxy averages.",
            "Water-context prior: province-month average water-area percentage.",
        ],
        "rainfall_anomaly": [
            "Known covariates: monthly rainfall climatology for the forecast month.",
            "Rainfall baseline prior: province-month average rainfall z-score.",
        ],
        "water_area": [
            "Known covariates: monthly rainfall climatology for the forecast month as a seasonal driver.",
            "Water baseline priors: province-level and province-month water-area percentage averages.",
        ],
    }
    return common + task_specific.get(task_key, [])


def analyze_data_coverage(panel: pd.DataFrame, target_col: str) -> dict[str, Any]:
    target_df = panel[panel[target_col].notna()].copy()
    return {
        "rows": int(len(target_df)),
        "province_count": int(target_df["province_name"].nunique()),
        "start": str(target_df["date"].min().date()),
        "end": str(target_df["date"].max().date()),
    }


def _lookup_tables(panel: pd.DataFrame, target_col: str) -> dict[str, pd.DataFrame]:
    valid = panel[panel[target_col].notna()].copy()
    month_target = (
        valid.groupby(["province_name", "month"], as_index=False)[target_col]
        .mean()
        .rename(columns={"month": "lookup_month", target_col: "target_month_avg"})
    )
    province_target = (
        valid.groupby("province_name", as_index=False)[target_col]
        .mean()
        .rename(columns={target_col: "target_province_avg"})
    )
    monthly_mean = (
        panel.groupby(["province_name", "month"], as_index=False)["monthly_mean"]
        .mean()
        .rename(columns={"month": "lookup_month", "monthly_mean": "monthly_mean_future"})
    )
    water_month = (
        panel.groupby(["province_name", "month"], as_index=False)["water_area_pct"]
        .mean()
        .rename(columns={"month": "lookup_month", "water_area_pct": "water_month_avg"})
    )
    province_meta = (
        panel.groupby("province_name", as_index=False)
        .agg(
            population_proxy=("population_total", "mean"),
            cropland_proxy=("cropland_area_km2", "mean"),
            exposure_proxy=("exposure_score", "mean"),
            water_province_avg=("water_area_pct", "mean"),
        )
        .fillna(0)
    )
    return {
        "month_target": month_target,
        "province_target": province_target,
        "monthly_mean": monthly_mean,
        "water_month": water_month,
        "province_meta": province_meta,
    }


def build_supervised_frame(panel: pd.DataFrame, task_key: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    config = TASK_CONFIGS[task_key]
    target_col = config["target_col"]
    lookups = _lookup_tables(panel, target_col)

    cols = list(
        dict.fromkeys(
            [
        "province_name",
        "date",
        "year",
        "month",
        target_col,
        "monthly_mean",
        "rainfall_mm",
        "water_area_pct",
        "population_total",
        "cropland_area_km2",
            ]
        )
    )
    work = panel[cols].copy()
    work = work[work[target_col].notna()].sort_values(["province_name", "date"]).reset_index(drop=True)

    by_province = work.groupby("province_name", group_keys=False)
    work["current_value"] = work[target_col]
    work["prediction_date"] = by_province["date"].shift(-1)
    work["target_next"] = by_province[target_col].shift(-1)

    for lag in COMMON_LAGS:
        work[f"lag_{lag}"] = by_province[target_col].shift(lag)

    rolling_source = by_province[target_col]
    for window in COMMON_WINDOWS:
        work[f"rolling_mean_{window}"] = rolling_source.transform(
            lambda s: s.rolling(window=window, min_periods=1).mean()
        )
        work[f"rolling_std_{window}"] = rolling_source.transform(
            lambda s: s.rolling(window=window, min_periods=2).std()
        )
        work[f"rolling_min_{window}"] = rolling_source.transform(
            lambda s: s.rolling(window=window, min_periods=1).min()
        )
        work[f"rolling_max_{window}"] = rolling_source.transform(
            lambda s: s.rolling(window=window, min_periods=1).max()
        )

    work["diff_lag_1"] = work["current_value"] - work["lag_1"]
    work["diff_lag_12"] = work["current_value"] - work["lag_12"]

    work = work.dropna(subset=["prediction_date", "target_next"]).copy()
    work["current_month"] = work["month"]
    work["pred_month"] = work["prediction_date"].dt.month
    work["pred_year"] = work["prediction_date"].dt.year
    work["pred_quarter"] = work["prediction_date"].dt.quarter

    start_date = work["prediction_date"].min()
    work["time_idx"] = (
        (work["prediction_date"].dt.year - start_date.year) * 12
        + (work["prediction_date"].dt.month - start_date.month)
    )
    work["month_sin"] = np.sin(2 * np.pi * work["pred_month"] / 12.0)
    work["month_cos"] = np.cos(2 * np.pi * work["pred_month"] / 12.0)

    work = work.merge(
        lookups["month_target"],
        left_on=["province_name", "pred_month"],
        right_on=["province_name", "lookup_month"],
        how="left",
    ).drop(columns=["lookup_month"])
    work = work.merge(
        lookups["monthly_mean"],
        left_on=["province_name", "pred_month"],
        right_on=["province_name", "lookup_month"],
        how="left",
    ).drop(columns=["lookup_month"])
    work = work.merge(
        lookups["water_month"],
        left_on=["province_name", "pred_month"],
        right_on=["province_name", "lookup_month"],
        how="left",
    ).drop(columns=["lookup_month"])
    work = work.merge(lookups["province_target"], on="province_name", how="left")
    work = work.merge(lookups["province_meta"], on="province_name", how="left")

    feature_cols = [
        "province_name",
        "current_value",
        "lag_1",
        "lag_2",
        "lag_3",
        "lag_6",
        "lag_12",
        "rolling_mean_3",
        "rolling_mean_6",
        "rolling_mean_12",
        "rolling_std_3",
        "rolling_std_6",
        "rolling_std_12",
        "rolling_min_3",
        "rolling_min_12",
        "rolling_max_3",
        "rolling_max_12",
        "diff_lag_1",
        "diff_lag_12",
        "pred_month",
        "pred_quarter",
        "pred_year",
        "time_idx",
        "month_sin",
        "month_cos",
        "target_month_avg",
        "target_province_avg",
        "monthly_mean_future",
        "water_month_avg",
        "water_province_avg",
        "population_proxy",
        "cropland_proxy",
        "exposure_proxy",
    ]

    if task_key == "rainfall_anomaly":
        feature_cols = [c for c in feature_cols if c not in ["water_month_avg", "water_province_avg", "population_proxy", "cropland_proxy", "exposure_proxy"]]
    elif task_key == "water_area":
        feature_cols = [c for c in feature_cols if c not in ["population_proxy", "cropland_proxy", "exposure_proxy"]]

    model_df = work[feature_cols + ["target_next", "prediction_date"]].copy()
    metadata = {
        "feature_cols": feature_cols,
        "categorical_cols": ["province_name"],
        "numeric_cols": [c for c in feature_cols if c != "province_name"],
        "lookups": {name: table.to_dict(orient="records") for name, table in lookups.items()},
        "coverage": analyze_data_coverage(panel, target_col),
    }
    return model_df, metadata


def time_split(model_df: pd.DataFrame, train_ratio: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    unique_dates = np.sort(model_df["prediction_date"].unique())
    split_idx = max(1, int(np.floor(len(unique_dates) * train_ratio)))
    cutoff = pd.Timestamp(unique_dates[split_idx - 1])
    train_df = model_df[model_df["prediction_date"] <= cutoff].copy()
    test_df = model_df[model_df["prediction_date"] > cutoff].copy()
    return train_df, test_df, cutoff


def _preprocessor(numeric_cols: list[str], categorical_cols: list[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric_pipe, numeric_cols),
            ("categorical", categorical_pipe, categorical_cols),
        ]
    )


def model_specs(random_state: int = 42) -> dict[str, Any]:
    return {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=14,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=1,
        ),
        "XGBoost": XGBRegressor(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="reg:squarederror",
            random_state=random_state,
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=random_state,
            verbosity=-1,
        ),
    }


def fit_and_evaluate(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    numeric_cols: list[str],
    categorical_cols: list[str],
) -> tuple[pd.DataFrame, dict[str, Pipeline], dict[str, np.ndarray]]:
    X_train = train_df[feature_cols]
    y_train = train_df["target_next"]
    X_test = test_df[feature_cols]
    y_test = test_df["target_next"]

    fitted: dict[str, Pipeline] = {}
    predictions: dict[str, np.ndarray] = {}
    metrics: list[dict[str, Any]] = []

    for name, estimator in model_specs().items():
        pipe = Pipeline(
            [
                ("preprocessor", _preprocessor(numeric_cols, categorical_cols)),
                ("model", estimator),
            ]
        )
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)
        fitted[name] = pipe
        predictions[name] = preds
        metrics.append(
            {
                "Model": name,
                "MAE": mean_absolute_error(y_test, preds),
                "RMSE": float(np.sqrt(mean_squared_error(y_test, preds))),
                "R2": r2_score(y_test, preds),
            }
        )

    metrics_df = pd.DataFrame(metrics).sort_values(["RMSE", "MAE"], ascending=[True, True]).reset_index(drop=True)
    return metrics_df, fitted, predictions


def save_benchmark_outputs(metrics_df: pd.DataFrame, output_dir: Path, task_title: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "benchmark_metrics.csv"
    chart_path = output_dir / "benchmark_metrics.png"

    metrics_df.to_csv(metrics_path, index=False)

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    palette = sns.color_palette("Blues_r", n_colors=len(metrics_df))

    for idx, metric in enumerate(METRIC_ORDER):
        sns.barplot(
            data=metrics_df,
            x="Model",
            y=metric,
            hue="Model",
            dodge=False,
            legend=False,
            ax=axes[idx],
            palette=palette,
        )
        axes[idx].set_title(metric)
        axes[idx].set_xlabel("")
        axes[idx].tick_params(axis="x", rotation=25)
        if metric == "R2":
            axes[idx].axhline(0, color="#64748b", linewidth=1, linestyle="--")

    fig.suptitle(f"{task_title} model benchmarking", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return metrics_path, chart_path


def save_best_model(
    best_model_name: str,
    fitted_models: dict[str, Pipeline],
    metadata: dict[str, Any],
    config: dict[str, Any],
    model_dir: Path,
) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = model_dir / "best_model.pkl"
    artifact = {
        "task_key": next(key for key, value in TASK_CONFIGS.items() if value["target_col"] == config["target_col"]),
        "task_title": config["title"],
        "target_col": config["target_col"],
        "target_label": config["target_label"],
        "best_model_name": best_model_name,
        "model": fitted_models[best_model_name],
        "feature_cols": metadata["feature_cols"],
        "numeric_cols": metadata["numeric_cols"],
        "categorical_cols": metadata["categorical_cols"],
        "lookups": metadata["lookups"],
        "coverage": metadata["coverage"],
        "feature_notes": feature_notes(next(key for key, value in TASK_CONFIGS.items() if value["target_col"] == config["target_col"])),
    }
    joblib.dump(artifact, artifact_path)
    return artifact_path


def run_training_workflow(task_key: str, panel_path: str | Path = PANEL_PATH) -> TrainingArtifacts:
    if task_key not in TASK_CONFIGS:
        raise KeyError(f"Unknown task '{task_key}'. Expected one of: {list(TASK_CONFIGS)}")

    config = TASK_CONFIGS[task_key]
    panel = prepare_panel(panel_path)
    model_df, metadata = build_supervised_frame(panel, task_key)
    train_df, test_df, cutoff = time_split(model_df)
    metrics_df, fitted_models, _ = fit_and_evaluate(
        train_df,
        test_df,
        metadata["feature_cols"],
        metadata["numeric_cols"],
        metadata["categorical_cols"],
    )

    metrics_path, chart_path = save_benchmark_outputs(metrics_df, config["folder"] / "results", config["title"])
    best_model_name = metrics_df.iloc[0]["Model"]
    artifact_path = save_best_model(
        best_model_name,
        fitted_models,
        metadata,
        {
            "target_col": config["target_col"],
            "target_label": config["target_label"],
            "title": config["title"],
        },
        config["folder"] / "models",
    )

    return TrainingArtifacts(
        task_key=task_key,
        best_model_name=best_model_name,
        artifact_path=artifact_path,
        metrics_path=metrics_path,
        chart_path=chart_path,
        metrics_df=metrics_df,
        train_rows=len(train_df),
        test_rows=len(test_df),
        train_end=str(cutoff.date()),
        test_start=str(pd.Timestamp(test_df["prediction_date"].min()).date()),
    )


def load_model_artifact(task_key: str) -> dict[str, Any] | None:
    config = TASK_CONFIGS.get(task_key)
    if not config:
        return None
    artifact_path = config["folder"] / "models" / "best_model.pkl"
    if not artifact_path.exists():
        return None
    return joblib.load(artifact_path)


def _lookup_frame(artifact: dict[str, Any], name: str) -> pd.DataFrame:
    return pd.DataFrame(artifact["lookups"].get(name, []))


def _lookup_value(df: pd.DataFrame, province: str, month: int | None, value_col: str, fallback: float = 0.0) -> float:
    if df.empty:
        return fallback
    month_col = "month" if "month" in df.columns else "lookup_month" if "lookup_month" in df.columns else None
    if month is None or month_col is None:
        match = df[df["province_name"] == province]
    else:
        match = df[(df["province_name"] == province) & (df[month_col] == month)]
    if match.empty:
        return fallback
    value = match.iloc[0][value_col]
    if pd.isna(value):
        return fallback
    return float(value)


def _feature_row(
    artifact: dict[str, Any],
    province: str,
    pred_date: pd.Timestamp,
    history_values: list[float],
    time_idx: int,
) -> dict[str, Any]:
    month_target = _lookup_frame(artifact, "month_target")
    province_target = _lookup_frame(artifact, "province_target")
    monthly_mean = _lookup_frame(artifact, "monthly_mean")
    water_month = _lookup_frame(artifact, "water_month")
    province_meta = _lookup_frame(artifact, "province_meta")

    values = pd.Series(history_values, dtype="float64")
    current_value = float(values.iloc[-1]) if not values.empty else np.nan

    row: dict[str, Any] = {
        "province_name": province,
        "current_value": current_value,
        "pred_month": int(pred_date.month),
        "pred_quarter": int(((pred_date.month - 1) // 3) + 1),
        "pred_year": int(pred_date.year),
        "time_idx": int(time_idx),
        "month_sin": float(np.sin(2 * np.pi * pred_date.month / 12.0)),
        "month_cos": float(np.cos(2 * np.pi * pred_date.month / 12.0)),
        "target_month_avg": _lookup_value(month_target, province, pred_date.month, "target_month_avg"),
        "target_province_avg": _lookup_value(province_target, province, None, "target_province_avg"),
        "monthly_mean_future": _lookup_value(monthly_mean, province, pred_date.month, "monthly_mean_future"),
        "water_month_avg": _lookup_value(water_month, province, pred_date.month, "water_month_avg"),
        "water_province_avg": _lookup_value(province_meta, province, None, "water_province_avg"),
        "population_proxy": _lookup_value(province_meta, province, None, "population_proxy"),
        "cropland_proxy": _lookup_value(province_meta, province, None, "cropland_proxy"),
        "exposure_proxy": _lookup_value(province_meta, province, None, "exposure_proxy"),
    }

    for lag in COMMON_LAGS:
        row[f"lag_{lag}"] = float(values.iloc[-(lag + 1)]) if len(values) > lag else np.nan

    for window in COMMON_WINDOWS:
        tail = values.tail(window)
        row[f"rolling_mean_{window}"] = float(tail.mean()) if not tail.empty else np.nan
        row[f"rolling_std_{window}"] = float(tail.std()) if len(tail) >= 2 else 0.0
        row[f"rolling_min_{window}"] = float(tail.min()) if not tail.empty else np.nan
        row[f"rolling_max_{window}"] = float(tail.max()) if not tail.empty else np.nan

    row["diff_lag_1"] = current_value - row["lag_1"] if not np.isnan(current_value) and not np.isnan(row["lag_1"]) else np.nan
    row["diff_lag_12"] = current_value - row["lag_12"] if not np.isnan(current_value) and not np.isnan(row["lag_12"]) else np.nan

    feature_cols = artifact["feature_cols"]
    return {col: row.get(col, np.nan) for col in feature_cols}


def recursive_forecast(
    panel: pd.DataFrame,
    artifact: dict[str, Any],
    provinces: list[str],
    horizon: int,
) -> pd.DataFrame:
    target_col = artifact["target_col"]
    panel = prepare_panel(PANEL_PATH) if target_col not in panel.columns else panel.copy()
    panel = panel.sort_values(["province_name", "date"]).reset_index(drop=True)

    output_rows: list[dict[str, Any]] = []
    valid = panel[panel[target_col].notna()].copy()
    if valid.empty:
        return pd.DataFrame(columns=["province_name", "forecast_date", "step", "predicted_value"])

    base_start = valid["date"].min()

    for province in provinces:
        history = valid[valid["province_name"] == province][["date", target_col]].dropna().sort_values("date")
        if history.empty:
            continue

        history_values = history[target_col].astype(float).tolist()
        last_date = pd.Timestamp(history["date"].iloc[-1])

        for step in range(1, horizon + 1):
            pred_date = last_date + pd.DateOffset(months=step)
            time_idx = (pred_date.year - base_start.year) * 12 + (pred_date.month - base_start.month)
            feature_row = _feature_row(artifact, province, pred_date, history_values, time_idx)
            pred_value = float(artifact["model"].predict(pd.DataFrame([feature_row]))[0])
            history_values.append(pred_value)
            output_rows.append(
                {
                    "province_name": province,
                    "forecast_date": pred_date,
                    "step": step,
                    "predicted_value": pred_value,
                }
            )

    return pd.DataFrame(output_rows)
