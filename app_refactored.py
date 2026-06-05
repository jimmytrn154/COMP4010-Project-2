from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np
import logging
from pathlib import Path

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MekongFloodLens")


# ==========================================================
# Data loading
# ==========================================================

PANEL_PATH = "data/processed/province_month_panel.csv"
BOUNDARY_PATH = "data/raw/mekong_provinces_boundary.geojson"
RAW_DAILY_PATH = "data/raw/mekong_province_day_rainfall_1981_2025.csv"
FORECAST_DAILY_PATH = "modeling/result/all_provinces_forecast_next_12_months.csv"
SPLIT_HISTORY_DIR = Path("modeling/data_splitted")
SPLIT_FORECAST_DIR = Path("modeling/result")

df = pd.read_csv(PANEL_PATH)
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
df["month"] = pd.to_numeric(df["month"], errors="coerce").astype(int)

# The panel has no `date` column, so build a clean monthly timeline from
# year + month. This guarantees the time-series views are always well defined.
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
    "rainfall_mm_from_daily": 0,
    "mean_daily_rainfall": 0,
    "max_1day_rainfall": 0,
    "rain_days_count": 0,
    "dry_days_count": 0,
    "heavy_rain_days_20mm": 0,
    "heavy_rain_days_50mm": 0,
    "max_consecutive_dry_days": 0,
    "max_consecutive_wet_days": 0,
    "rain_day_ratio": 0,
    "dry_day_ratio": 0,
    "days_observed": 0,
}

for col, default in default_columns.items():
    if col not in df.columns:
        df[col] = default

for col in default_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df["monthly_mean"].isna().all():
    df["monthly_mean"] = df.groupby(["province_name", "month"])["rainfall_mm"].transform("mean")


def minmax(series):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    spread = s.max() - s.min()
    if spread == 0:
        return pd.Series(0, index=s.index)
    return (s - s.min()) / spread


# Risk-score components (relative, heuristic — see the methodology block in the UI).
#   water_score    : surface-water extent (flood proxy)
#   rainfall_score : positive rainfall anomaly (wet signal)
#   drought_score  : negative rainfall anomaly (dry signal)
#   exposure_score : population + cropland concentration
df["rainfall_score"] = minmax(df["rainfall_zscore"].clip(lower=0))
df["water_score"] = minmax(df["water_area_pct"].fillna(0))
df["drought_score"] = minmax((-df["rainfall_zscore"]).clip(lower=0))
df["exposure_score"] = 0.6 * minmax(df["population_total"].fillna(0)) + 0.4 * minmax(
    df["cropland_area_km2"].fillna(0)
)

if df["combined_risk_score"].isna().all():
    # Weighted blend: surface water + rainfall get slightly higher weight.
    df["combined_risk_score"] = (
        0.35 * df["water_score"]
        + 0.25 * df["rainfall_score"]
        + 0.25 * df["drought_score"]
        + 0.15 * df["exposure_score"]
    )

df["has_population"] = df["population_total"].notna()
df["has_cropland"] = df["cropland_area_km2"].notna()

df = df.fillna(0)

daily_rain_df = pd.read_csv(RAW_DAILY_PATH)
daily_rain_df["date"] = pd.to_datetime(daily_rain_df["date"], errors="coerce")
daily_rain_df["year"] = pd.to_numeric(daily_rain_df["year"], errors="coerce").astype(int)
daily_rain_df["month"] = pd.to_numeric(daily_rain_df["month"], errors="coerce").astype(int)
daily_rain_df["day"] = pd.to_numeric(daily_rain_df["day"], errors="coerce").astype(int)
daily_rain_df["rainfall_mm"] = pd.to_numeric(daily_rain_df["rainfall_mm"], errors="coerce").fillna(0)
daily_rain_df["province_name"] = daily_rain_df["province_name"].astype(str).str.strip()

if Path(FORECAST_DAILY_PATH).exists():
    forecast_daily_df = pd.read_csv(FORECAST_DAILY_PATH)
    forecast_daily_df["date"] = pd.to_datetime(forecast_daily_df["date"], errors="coerce")
    forecast_daily_df["year"] = pd.to_numeric(forecast_daily_df["year"], errors="coerce").astype(int)
    forecast_daily_df["month"] = pd.to_numeric(forecast_daily_df["month"], errors="coerce").astype(int)
    forecast_daily_df["day"] = pd.to_numeric(forecast_daily_df["day"], errors="coerce").astype(int)
    forecast_daily_df["predicted_rainfall_mm"] = pd.to_numeric(
        forecast_daily_df["predicted_rainfall_mm"], errors="coerce"
    ).fillna(0)
    forecast_daily_df["province_name"] = forecast_daily_df["province_name"].astype(str).str.strip()
else:
    forecast_daily_df = pd.DataFrame(
        columns=["province_name", "date", "year", "month", "day", "predicted_rainfall_mm", "model_name"]
    )


def _load_split_daily_history():
    history_map = {}
    for file_path in sorted(SPLIT_HISTORY_DIR.glob("*_rainfall_1981_2025.csv")):
        province_df = pd.read_csv(file_path)
        if province_df.empty:
            continue
        province_df["date"] = pd.to_datetime(province_df["date"], errors="coerce")
        province_df["year"] = pd.to_numeric(province_df["year"], errors="coerce").astype(int)
        province_df["month"] = pd.to_numeric(province_df["month"], errors="coerce").astype(int)
        province_df["day"] = pd.to_numeric(province_df["day"], errors="coerce").astype(int)
        province_df["rainfall_mm"] = pd.to_numeric(province_df["rainfall_mm"], errors="coerce").fillna(0)
        province_df["province_name"] = province_df["province_name"].astype(str).str.strip()
        history_map[province_df["province_name"].iloc[0]] = (
            province_df[["province_name", "date", "year", "month", "day", "rainfall_mm"]]
            .sort_values("date")
            .reset_index(drop=True)
        )
    return history_map


def _load_split_daily_forecasts():
    forecast_map = {}
    for file_path in sorted(SPLIT_FORECAST_DIR.glob("*_forecast_next_12_months.csv")):
        if file_path.name == "all_provinces_forecast_next_12_months.csv":
            continue
        province_df = pd.read_csv(file_path)
        if province_df.empty:
            continue
        province_df["date"] = pd.to_datetime(province_df["date"], errors="coerce")
        province_df["year"] = pd.to_numeric(province_df["year"], errors="coerce").astype(int)
        province_df["month"] = pd.to_numeric(province_df["month"], errors="coerce").astype(int)
        province_df["day"] = pd.to_numeric(province_df["day"], errors="coerce").astype(int)
        province_df["predicted_rainfall_mm"] = pd.to_numeric(
            province_df["predicted_rainfall_mm"], errors="coerce"
        ).fillna(0)
        province_df["province_name"] = province_df["province_name"].astype(str).str.strip()
        forecast_map[province_df["province_name"].iloc[0]] = (
            province_df[["province_name", "date", "year", "month", "day", "predicted_rainfall_mm", "model_name"]]
            .sort_values("date")
            .reset_index(drop=True)
        )
    return forecast_map


split_daily_history = _load_split_daily_history()
split_daily_forecasts = _load_split_daily_forecasts()
forecast_provinces = sorted(set(split_daily_history.keys()) & set(split_daily_forecasts.keys()))

with open(BOUNDARY_PATH, encoding="utf-8") as f:
    geojson_data = json.load(f)


def collect_lon_lat(coords):
    if not coords:
        return []
    if isinstance(coords[0], (int, float)) and len(coords) >= 2:
        return [(coords[0], coords[1])]
    points = []
    for item in coords:
        points.extend(collect_lon_lat(item))
    return points


map_label_points = []
for feature in geojson_data.get("features", []):
    points = collect_lon_lat(feature.get("geometry", {}).get("coordinates", []))
    if not points:
        continue
    lons, lats = zip(*points)
    map_label_points.append({
        "province_name": feature.get("properties", {}).get("ADM1_NAME"),
        "lon": float(np.mean(lons)),
        "lat": float(np.mean(lats)),
    })
map_label_df = pd.DataFrame(map_label_points)

provinces = sorted(df["province_name"].dropna().unique().tolist())
years = sorted(df["year"].dropna().unique().tolist())
daily_years = sorted(daily_rain_df["year"].dropna().unique().tolist())
default_history_start_year = max(min(daily_years), max(daily_years) - 9) if daily_years else min(years)

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

metric_options = {
    "combined_risk_score": "Combined risk score",
    "rainfall_mm": "Rainfall (mm)",
    "rainfall_anomaly": "Rainfall anomaly",
    "water_area_km2": "Surface water area (km²)",
    "water_area_pct": "Surface water area (%)",
    "population_total": "Population context",
    "cropland_area_km2": "Cropland area (km²)",
}

metric_labels = {
    "combined_risk_score": "Risk score",
    "rainfall_mm": "Rainfall (mm)",
    "rainfall_anomaly": "Rainfall anomaly (mm)",
    "water_area_km2": "Water area (km²)",
    "water_area_pct": "Water area (%)",
    "population_total": "Population",
    "cropland_area_km2": "Cropland area (km²)",
}

metric_color_scales = {
    "combined_risk_score": "YlOrRd",
    "rainfall_mm": "Blues",
    "rainfall_anomaly": "RdBu",
    "water_area_km2": "Blues",
    "water_area_pct": "Blues",
    "population_total": "Purples",
    "cropland_area_km2": "Greens",
}

extreme_metric_options = {
    "max_1day_rainfall": "Max 1-day rainfall",
    "heavy_rain_days_20mm": "Heavy rain days >= 20 mm",
    "heavy_rain_days_50mm": "Extreme rain days >= 50 mm",
    "max_consecutive_dry_days": "Longest dry spell",
    "rain_days_count": "Rainy days",
    "dry_days_count": "Dry days",
    "rain_day_ratio": "Rainy-day share",
    "dry_day_ratio": "Dry-day share",
}

metric_options.update(extreme_metric_options)

metric_labels.update({
    "max_1day_rainfall": "Max 1-day rainfall (mm)",
    "heavy_rain_days_20mm": "Heavy rain days >= 20 mm",
    "heavy_rain_days_50mm": "Extreme rain days >= 50 mm",
    "max_consecutive_dry_days": "Longest dry spell (days)",
    "rain_days_count": "Rainy days",
    "dry_days_count": "Dry days",
    "rain_day_ratio": "Rainy-day share",
    "dry_day_ratio": "Dry-day share",
})

metric_color_scales.update({
    "max_1day_rainfall": "Blues",
    "heavy_rain_days_20mm": "Blues",
    "heavy_rain_days_50mm": "YlOrRd",
    "max_consecutive_dry_days": "YlOrBr",
    "rain_days_count": "Blues",
    "dry_days_count": "YlOrBr",
    "rain_day_ratio": "Blues",
    "dry_day_ratio": "YlOrBr",
})

metric_plot_formats = {
    "combined_risk_score": ":.2f",
    "rainfall_mm": ":,.1f",
    "rainfall_anomaly": ":+,.1f",
    "water_area_km2": ":,.1f",
    "water_area_pct": ":,.2f",
    "population_total": ":,.0f",
    "cropland_area_km2": ":,.1f",
    "max_1day_rainfall": ":,.1f",
    "heavy_rain_days_20mm": ":,.0f",
    "heavy_rain_days_50mm": ":,.0f",
    "max_consecutive_dry_days": ":,.0f",
    "rain_days_count": ":,.0f",
    "dry_days_count": ":,.0f",
    "rain_day_ratio": ":.0%",
    "dry_day_ratio": ":.0%",
    "days_observed": ":,.0f",
}

daily_hover_metrics = [
    "max_1day_rainfall",
    "rain_days_count",
    "heavy_rain_days_20mm",
    "max_consecutive_dry_days",
    "days_observed",
]


# ==========================================================
# Plot styling helpers (shared dark theme)
# ==========================================================

PALETTE = {
    "accent": "#38bdf8",
    "cyan": "#0ea5e9",
    "purple": "#8b5cf6",
    "rose": "#f43f5e",
    "amber": "#f59e0b",
    "green": "#34d399",
    "grid": "#1e293b",
    "muted": "#94a3b8",
    "text": "#cbd5e1",
}


def apply_dark_layout(fig, height, *, legend=False, font_size=11):
    """Apply the shared transparent dark-dashboard styling to a Plotly figure."""
    layout = dict(
        height=height,
        margin=dict(l=45, r=20, t=10, b=38),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], size=font_size),
    )
    if legend:
        layout["legend"] = dict(orientation="h", y=1.12, x=1, xanchor="right")
    else:
        layout["showlegend"] = False
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=True, gridcolor=PALETTE["grid"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=PALETTE["grid"], zeroline=False, automargin=True)
    return fig


def scaled_sizes(series, lo=9, hi=26):
    """Map a numeric series to a marker-size range so bubbles stay visible."""
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    spread = s.max() - s.min()
    if spread == 0:
        return pd.Series(float((lo + hi) / 2), index=s.index)
    return lo + (s - s.min()) / spread * (hi - lo)


def empty_fig(height, message="No data for this selection"):
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(color=PALETTE["muted"], size=13),
    )
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def metric_text_template(metric):
    return f"%{{text{metric_plot_formats.get(metric, ':.2f')}}}"


def format_metric_value(value, metric):
    value = pd.to_numeric(value, errors="coerce")
    value = 0 if pd.isna(value) else float(value)
    if metric in {"rain_day_ratio", "dry_day_ratio"}:
        return f"{value * 100:.0f}%"
    if metric in {
        "rain_days_count",
        "dry_days_count",
        "heavy_rain_days_20mm",
        "heavy_rain_days_50mm",
        "max_consecutive_dry_days",
        "max_consecutive_wet_days",
        "days_observed",
    }:
        return f"{value:,.0f} days"
    if metric in {"rainfall_mm", "rainfall_anomaly", "max_1day_rainfall", "mean_daily_rainfall", "rainfall_mm_from_daily"}:
        return f"{value:,.1f} mm"
    if metric in {"water_area_km2", "cropland_area_km2"}:
        return f"{value:,.1f} kmÂ²"
    if metric == "population_total":
        return f"{value:,.0f}"
    return f"{value:.2f}"


# ==========================================================
# Narrative / storytelling helpers
# ==========================================================

def _risk_level(pct):
    """Map a percentile (0-1) to a qualitative risk band."""
    if pct >= 0.75:
        return "elevated", PALETTE["rose"]
    if pct >= 0.45:
        return "moderate", PALETTE["amber"]
    return "lower", PALETTE["green"]


def build_narrative(province, year, month):
    """Return (headline, [bullets], badge_label, badge_color) for the selection."""
    mname = MONTH_NAMES[month - 1]
    month_df = df[(df["year"] == year) & (df["month"] == month)].copy()

    if month_df.empty:
        return (
            f"No records for {mname} {year}.",
            ["Try a different year or month — coverage varies by layer."],
            "no data", PALETTE["muted"],
        )

    # Province-wide context: which province leads this month?
    leader = month_df.sort_values("combined_risk_score", ascending=False).iloc[0]

    if province == "All Provinces":
        wettest = month_df.sort_values("rainfall_mm", ascending=False).iloc[0]
        bullets = [
            f"<b>{leader['province_name']}</b> shows the highest combined risk score "
            f"this month ({leader['combined_risk_score']:.2f}).",
            f"<b>{wettest['province_name']}</b> received the most rainfall "
            f"({wettest['rainfall_mm']:,.0f} mm).",
            "Pick a single province to unlock its trend, seasonality and "
            "risk-driver breakdown.",
        ]
        return (
            f"Delta-wide snapshot — {mname} {year}",
            bullets, "regional view", PALETTE["accent"],
        )

    row = month_df[month_df["province_name"] == province]
    if row.empty:
        return (
            f"{province} has no record for {mname} {year}.",
            ["This province/month layer may be missing — try another period."],
            "no data", PALETTE["muted"],
        )
    row = row.iloc[0]

    # Percentile of this province among all provinces this month.
    ranks = month_df["combined_risk_score"].rank(pct=True)
    pct = float(ranks.loc[row.name]) if row.name in ranks.index else 0.5
    level, level_color = _risk_level(pct)

    # Which driver dominates?
    drivers = {
        "surface water (flood-like)": row["water_score"],
        "wet rainfall anomaly (flood-like)": row["rainfall_score"],
        "rainfall deficit (drought-like)": row["drought_score"],
        "population & cropland exposure": row["exposure_score"],
    }
    dominant = max(drivers, key=drivers.get)

    anomaly = row["rainfall_anomaly"]
    anomaly_txt = (
        f"{anomaly:+,.0f} mm vs the long-run average"
        if abs(anomaly) > 0.5 else "close to the long-run average"
    )

    bullets = [
        f"Combined risk is <b>{level}</b> "
        f"(higher than {pct * 100:.0f}% of delta provinces this month).",
        f"The dominant driver is <b>{dominant}</b>.",
        f"Rainfall this month is {anomaly_txt}.",
    ]
    if row["water_area_km2"] > 0:
        bullets.append(
            f"Surface-water extent (flood proxy): {row['water_area_km2']:,.0f} km²."
        )

    headline = f"{province} — {mname} {year}"
    return headline, bullets, f"{level} risk", level_color


def interpretation_note(province, year, month):
    """Short interpretation of flood-like vs drought-like vs exposure-driven risk."""
    if province == "All Provinces":
        return (
            "Select a single province for a tailored interpretation. Regionally, "
            "watch provinces where surface water and rainfall peak together — that "
            "combination is the strongest flood-like signal in this heuristic."
        )
    row = df[(df["province_name"] == province) & (df["year"] == year) & (df["month"] == month)]
    if row.empty:
        return "No data available to interpret for this selection."
    row = row.iloc[0]

    water, wet, dry, exp = (
        row["water_score"], row["rainfall_score"], row["drought_score"], row["exposure_score"],
    )
    if max(water, wet) >= max(dry, exp) and max(water, wet) > 0.25:
        kind = (
            "<b>flood-like risk</b>: elevated surface water and/or above-average "
            "rainfall dominate the score here."
        )
    elif dry >= max(water, wet, exp) and dry > 0.25:
        kind = (
            "<b>drought-like risk</b>: a rainfall deficit is the main contributor, "
            "not flooding."
        )
    elif exp >= max(water, wet, dry):
        kind = (
            "<b>exposure-driven risk</b>: physical hazard signals are modest, but "
            "dense population and cropland raise the stakes of any event."
        )
    else:
        kind = "<b>balanced / low risk</b>: no single driver clearly dominates."

    return (
        f"For {province} in {MONTH_NAMES[month - 1]} {year}, this reads as {kind} "
        "Remember the score is relative across the delta, not an absolute probability."
    )


# ==========================================================
# Styling
# ==========================================================

custom_css = """
:root {
    --bg: #07111f;
    --panel: #0d1b2e;
    --border: #22344d;
    --text: #f8fafc;
    --muted: #9fb0c7;
    --accent: #38bdf8;
}
html, body {
    background: var(--bg);
    color: var(--text);
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.app-shell {
    padding: 22px 28px 26px 28px;
    max-width: 1600px;
    margin: 0 auto;
}
.header {
    margin-bottom: 14px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 14px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 18px;
    flex-wrap: wrap;
}
.header h1 {
    margin: 0;
    font-size: 2.3rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.subtitle {
    margin-top: 5px;
    color: var(--muted);
    max-width: 760px;
    line-height: 1.45;
}
.header-tag {
    color: #cbd5e1;
    font-size: 0.78rem;
    text-align: right;
    line-height: 1.5;
}
.header-tag b { color: #e2e8f0; }
.story-strip, .flow-note {
    color: #cbd5e1;
    background: rgba(56, 189, 248, 0.08);
    border: 1px solid rgba(56, 189, 248, 0.20);
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 18px;
    font-size: 0.92rem;
    line-height: 1.5;
}
/* Section headers separate the four story acts */
.section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.18rem;
    font-weight: 800;
    color: #e2e8f0;
    margin: 6px 0 12px 0;
}
.section-title .step {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    font-size: 0.85rem;
    font-weight: 800;
    color: #07111f;
    background: linear-gradient(135deg, #38bdf8, #818cf8);
}
.section-title .section-hint {
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--muted);
    margin-left: auto;
}
/* Insight + filter row */
.control-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 0.62fr);
    gap: 18px;
    margin-bottom: 18px;
    align-items: stretch;
}
.filter-bar {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px 16px 6px 16px;
}
.filter-title {
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 8px;
}
.insight-card {
    background: linear-gradient(135deg, rgba(56,189,248,0.10), rgba(129,140,248,0.08));
    border: 1px solid rgba(129,140,248,0.30);
    border-radius: 16px;
    padding: 16px 18px;
}
.insight-card h4 {
    margin: 0 0 8px 0;
    font-size: 1rem;
    font-weight: 800;
    color: #f1f5f9;
}
.insight-card ul {
    margin: 0;
    padding-left: 18px;
    color: #cbd5e1;
    font-size: 0.88rem;
    line-height: 1.55;
}
.narrative-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 18px;
}
.narrative-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}
.narrative-head h4 {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 800;
    color: #f1f5f9;
}
.risk-badge {
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 3px 10px;
    border-radius: 999px;
    color: #07111f;
}
.narrative-card ul {
    margin: 0;
    padding-left: 18px;
    color: #cbd5e1;
    font-size: 0.9rem;
    line-height: 1.55;
}
.interp-note {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed var(--border);
    color: #aebfd6;
    font-size: 0.86rem;
    line-height: 1.5;
}
.warning-pill {
    display: inline-block;
    margin-top: 10px;
    font-size: 0.8rem;
    color: #fde68a;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 10px;
    padding: 6px 12px;
}
.card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.18);
}
.card.compact {
    padding: 15px;
}
.map-card {
    display: flex;
    flex-direction: column;
    min-height: 640px;
}
.map-widget-shell {
    flex: 1 1 auto;
    min-height: 580px;
}
.map-widget-shell > div,
.map-widget-shell .shiny-bound-output,
.map-widget-shell .html-widget,
.map-widget-shell .plotly,
.map-widget-shell .js-plotly-plot,
.map-widget-shell .plot-container,
.map-widget-shell .svg-container {
    width: 100% !important;
}
.card-title {
    font-size: 1.03rem;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 5px;
}
.card-subtitle {
    color: var(--muted);
    font-size: 0.82rem;
    margin-bottom: 12px;
    line-height: 1.45;
}
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 18px;
}
.kpi {
    border-radius: 18px;
    padding: 18px;
    min-height: 112px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: linear-gradient(135deg, #1d4ed8, #2563eb);
}
.kpi.cyan { background: linear-gradient(135deg, #0369a1, #0ea5e9); }
.kpi.purple { background: linear-gradient(135deg, #6d28d9, #8b5cf6); }
.kpi.orange { background: linear-gradient(135deg, #b45309, #f97316); }
.kpi-label {
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    font-weight: 800;
    opacity: 0.78;
}
.kpi-value {
    font-size: 1.9rem;
    font-weight: 850;
    line-height: 1.05;
    margin-top: 8px;
}
.kpi-note {
    font-size: 0.78rem;
    opacity: 0.82;
}
.extreme-grid {
    display: grid;
    gap: 18px;
}
.extreme-top-grid {
    display: grid;
    grid-template-columns: minmax(280px, 0.75fr) minmax(0, 1.1fr) minmax(0, 1.1fr);
    gap: 18px;
    align-items: stretch;
}
.extreme-second-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 18px;
    align-items: stretch;
}
.extreme-heatmap-card {
    grid-column: 1 / -1;
}
.extreme-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.extreme-kpi {
    border-top: 1px solid rgba(148, 163, 184, 0.18);
    padding-top: 12px;
}
.extreme-kpi:first-of-type {
    border-top: 0;
    padding-top: 0;
}
.extreme-kpi-label {
    color: var(--muted);
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.extreme-kpi-value {
    color: #f8fafc;
    font-size: 1.55rem;
    font-weight: 850;
    line-height: 1.1;
    margin-top: 3px;
}
.extreme-kpi-note {
    color: var(--muted);
    font-size: 0.78rem;
}
.overview-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.85fr);
    gap: 18px;
    align-items: stretch;
}
.side-grid {
    display: grid;
    grid-template-rows: auto auto;
    gap: 18px;
}
.duo-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
}
.forecast-control-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
    gap: 16px;
    margin-bottom: 12px;
    align-items: end;
}
.forecast-note {
    margin-top: 10px;
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.5;
}
.bottom-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
}
.coverage-note {
    color: #cbd5e1;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.24);
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 18px;
    font-size: 0.86rem;
    line-height: 1.5;
}
.coverage-note b {
    color: #f8fafc;
}
.shiny-input-container {
    margin-bottom: 10px;
    color: #cbd5e1;
}
.form-select, .form-control {
    background-color: #17243a !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
    border-radius: 10px !important;
}
.irs--shiny .irs-bar, .irs--shiny .irs-single {
    background: #38bdf8 !important;
    border-color: #38bdf8 !important;
}
.irs--shiny .irs-handle {
    border-color: #38bdf8 !important;
}
/* Methodology / transparency block */
.method-card details {
    color: #cbd5e1;
}
.method-card summary {
    cursor: pointer;
    font-weight: 800;
    color: #f1f5f9;
    font-size: 1.02rem;
    list-style: none;
}
.method-card summary::-webkit-details-marker { display: none; }
.method-card summary::before { content: "▸ "; color: var(--accent); }
.method-card details[open] summary::before { content: "▾ "; }
.method-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0,1fr));
    gap: 12px;
    margin-top: 14px;
}
.method-item {
    background: #0b1626;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
}
.method-item b { color: var(--accent); }
.method-item span {
    display: block;
    color: var(--muted);
    font-size: 0.82rem;
    margin-top: 4px;
    line-height: 1.45;
}
.method-weights {
    margin-top: 12px;
    color: var(--muted);
    font-size: 0.86rem;
    line-height: 1.5;
}
@media (max-width: 1200px) {
    .overview-grid, .bottom-grid, .kpi-grid, .control-grid, .duo-grid, .extreme-grid, .extreme-top-grid, .extreme-second-grid, .method-grid, .forecast-control-grid {
        grid-template-columns: 1fr;
    }
}
"""


# ==========================================================
# Small UI builders
# ==========================================================

def section_header(step, title, hint):
    return ui.div(
        ui.span(str(step), class_="step"),
        ui.span(title),
        ui.span(hint, class_="section-hint"),
        class_="section-title",
    )


def chart_card(title, subtitle, widget_id, height, *, compact=False):
    return ui.div(
        ui.div(title, class_="card-title"),
        ui.div(subtitle, class_="card-subtitle"),
        output_widget(widget_id, height=f"{height}px"),
        class_="card compact" if compact else "card",
    )


# ==========================================================
# UI
# ==========================================================

app_ui = ui.page_fluid(
    ui.head_content(
        ui.tags.style(custom_css),
        ui.tags.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap",
            rel="stylesheet",
        ),
    ),
    ui.div(
        # ---- Header -------------------------------------------------
        ui.div(
            ui.div(
                ui.h1("Mekong FloodLens"),
                ui.div(
                    "An interactive water-risk story for the Vietnamese Mekong Delta — "
                    "blending monthly rainfall, daily-derived rainfall extremes, "
                    "satellite surface water, and human exposure into "
                    "one explorable heuristic risk score.",
                    class_="subtitle",
                ),
            ),
            ui.div(
                ui.HTML(
                    f"<b>{len(provinces)}</b> provinces &nbsp;·&nbsp; "
                    f"<b>{min(years)}–{max(years)}</b> &nbsp;·&nbsp; monthly panel<br>"
                    "Rainfall | Daily extremes | Surface water | Exposure"
                ),
                class_="header-tag",
            ),
            class_="header",
        ),
        # ---- Story flow strip --------------------------------------
        ui.div(
            ui.HTML(
                "<b>How to read this dashboard →</b> "
                "<b>1.</b> Where is risk concentrated? "
                "<b>2.</b> What drives it? "
                "<b>3.</b> What happened inside the month? "
                "<b>4.</b> How has it changed over time? "
                "<b>5.</b> Who and what is exposed?"
            ),
            class_="story-strip",
        ),
        # ---- Insight panel + filters -------------------------------
        ui.div(
            ui.div(
                ui.div("Global filters", class_="filter-title"),
                ui.row(
                    ui.column(3, ui.input_select("province", "Province", choices=["All Provinces"] + provinces, selected="All Provinces")),
                    ui.column(2, ui.input_select("year", "Year", choices=[str(y) for y in years], selected=str(max([y for y in years if y <= 2021] or years)))),
                    ui.column(3, ui.input_slider("month", "Month", 1, 12, 9)),
                    ui.column(4, ui.input_select("metric", "Map / ranking metric", choices=metric_options, selected="combined_risk_score")),
                ),
                class_="filter-bar",
            ),
            ui.div(
                ui.h4("What should I look at?"),
                ui.HTML(
                    "<ul>"
                    "<li>Start with the <b>map</b> — dark-to-bright shows where the chosen metric peaks.</li>"
                    "<li>Use the <b>ranking</b> + <b>driver breakdown</b> to see <i>why</i> a province stands out.</li>"
                    "<li>Use <b>rainfall extremes</b> to separate one-day events, repeated rainy days, and dry spells.</li>"
                    "<li>Scan the <b>trend</b> and <b>seasonality</b> charts for the timing of risk.</li>"
                    "<li>Close with <b>exposure</b> — who and what sits in harm's way.</li>"
                    "</ul>"
                ),
                class_="insight-card",
            ),
            class_="control-grid",
        ),
        # ---- Dynamic narrative -------------------------------------
        ui.output_ui("narrative"),
        # ---- KPI cards ---------------------------------------------
        ui.div(
            ui.div(ui.div("Average rainfall", class_="kpi-label"), ui.output_ui("kpi_rain"), ui.div("Selected context", class_="kpi-note"), class_="kpi"),
            ui.div(ui.div("Surface water extent", class_="kpi-label"), ui.output_ui("kpi_water"), ui.div("Flood proxy where available", class_="kpi-note"), class_="kpi cyan"),
            ui.div(ui.div("Population context", class_="kpi-label"), ui.output_ui("kpi_pop"), ui.div("Annual exposure layer", class_="kpi-note"), class_="kpi purple"),
            ui.div(ui.div("Highest selected metric", class_="kpi-label"), ui.output_ui("kpi_top"), ui.div("Strongest province signal", class_="kpi-note"), class_="kpi orange"),
            class_="kpi-grid",
        ),
        # ===========================================================
        # ACT 1 — WHERE is risk concentrated?
        # ===========================================================
        section_header(1, "Where is risk concentrated?", "Spatial pattern + provincial ranking"),
        ui.div(
            ui.div(
                ui.div("Interactive Mekong Delta map", class_="card-title"),
                ui.div("Locate spatial water-risk patterns by province for the selected metric, year and month.", class_="card-subtitle"),
                ui.div(output_widget("map_plot", height="580px", width="100%"), class_="map-widget-shell"),
                class_="card map-card",
            ),
            ui.div(
                chart_card(
                    "Province ranking",
                    "Provinces ranked by the selected metric — priority areas sit at the top.",
                    "ranking_plot", 255, compact=True,
                ),
                chart_card(
                    "Risk component breakdown",
                    "Is the signal driven by water, rainfall, drought, or exposure?",
                    "breakdown_plot", 255, compact=True,
                ),
                class_="side-grid",
            ),
            class_="overview-grid",
        ),
        # ===========================================================
        # ACT 2 — WHAT drives the risk?
        # ===========================================================
        section_header(2, "What drives the risk?", "Rainfall vs surface-water relationship"),
        ui.div(
            chart_card(
                "Rainfall anomaly vs surface water",
                "Each dot is a province this month. Upper-right = wet anomaly + high water (flood-like). Bubble size = population.",
                "scatter_plot", 360,
            ),
            chart_card(
                "Rainfall trend vs long-run average",
                "Selected-year rainfall (solid) against the historical monthly mean (dashed). The dotted line marks the selected month.",
                "rain_trend_plot", 360,
            ),
            class_="duo-grid",
        ),
        # ===========================================================
        # ACT 3 - RAINFALL extremes
        # ===========================================================
        section_header(3, "Rainfall extremes", "Daily rainfall structure inside each selected month"),
        ui.div(
            ui.div(
                ui.div(
                    ui.div("Daily-derived indicators", class_="card-title"),
                    ui.div("These metrics summarize daily CHIRPS rainfall inside the selected monthly record.", class_="card-subtitle"),
                    ui.input_select("extreme_metric", "Extreme rainfall metric", choices=extreme_metric_options, selected="max_1day_rainfall"),
                    ui.output_ui("extreme_kpis"),
                    class_="card extreme-card",
                ),
                chart_card(
                    "Rainfall structure inside selected month",
                    "Daily composition by dry days, rainy days, heavy-rain days, and extreme-rain days.",
                    "monthly_rain_structure_plot", 360,
                ),
                chart_card(
                    "Extreme signature",
                    "Normalized shape of one-day intensity, rainy share, heavy rain, dry spell, and wet spell.",
                    "extreme_signature_plot", 360,
                ),
                class_="extreme-top-grid",
            ),
            ui.div(
                chart_card(
                    "Extreme metric ranking",
                    "Provinces ranked by the selected daily-derived monthly indicator.",
                    "extreme_ranking_plot", 360,
                ),
                chart_card(
                    "Extreme metric trend",
                    "Selected-year monthly pattern for the selected province, or delta average.",
                    "extreme_trend_plot", 360,
                ),
                class_="extreme-second-grid",
            ),
            ui.div(
                ui.div("Extreme metric heatmap", class_="card-title"),
                ui.div("Province-by-month view for the selected year and daily-derived metric.", class_="card-subtitle"),
                output_widget("extreme_calendar_heatmap", height="360px"),
                class_="card extreme-heatmap-card",
            ),
            class_="extreme-grid",
        ),
        # ===========================================================
        # ACT 4 - HOW has it changed over time?
        # ===========================================================
        section_header(4, "How has it changed over time?", "Long-run trend | seasonality | anomalies"),
        ui.div(
            chart_card(
                "Combined risk over time",
                "Full monthly timeline of the combined risk score for the selected province (or delta average).",
                "risk_time_plot", 320,
            ),
            chart_card(
                "Rainfall seasonality",
                "Average rainfall by calendar month across all years — the selected month is highlighted.",
                "seasonality_plot", 320,
            ),
            chart_card(
                "Anomaly heatmap",
                "Month × province rainfall z-scores for the selected year. Red = wetter, blue = drier than normal.",
                "heatmap_plot", 320,
            ),
            class_="bottom-grid",
        ),
        ui.div(
            ui.div("Rainfall prediction preview", class_="card-title"),
            ui.div(
                "Daily rainfall history from the raw dataset linked with recursive XGBoost forecasts. "
                "Use the sliders to decide how much historical context and how many forecast months to show.",
                class_="card-subtitle",
            ),
            ui.div(
                ui.input_slider(
                    "history_year_range",
                    "Historical years to display",
                    min(daily_years),
                    max(daily_years),
                    value=(default_history_start_year, max(daily_years)),
                ),
                ui.input_slider(
                    "forecast_horizon_months",
                    "Prediction horizon (months)",
                    1,
                    12,
                    12,
                ),
                ui.input_select(
                    "forecast_province",
                    "Prediction province",
                    choices=forecast_provinces,
                    selected=forecast_provinces[0] if forecast_provinces else None,
                ),
                class_="forecast-control-grid",
            ),
            output_widget("rainfall_forecast_plot", height="420px"),
            ui.output_ui("forecast_window_note"),
            class_="card",
        ),
        # ===========================================================
        # ACT 5 - WHO / WHAT is exposed?
        # ===========================================================
        section_header(5, "Who and what is exposed?", "Separate exposure layers because coverage differs"),
        ui.div(
            ui.HTML(
                "<b>Population:</b> WorldPop yearly, available 2000-2020. "
                "<b>Cropland:</b> ESA WorldCover static snapshot, available 2021. "
                "Shown separately because these layers do not share a same-year coverage window."
            ),
            class_="coverage-note",
        ),
        ui.div(
            chart_card(
                "Population exposure",
                "Province ranking by population. Uses the latest available population year at or before the selected year.",
                "population_exposure_plot", 360,
            ),
            chart_card(
                "Cropland exposure",
                "Province ranking by cropland area from the static 2021 land-cover snapshot.",
                "cropland_exposure_plot", 360,
            ),
            class_="duo-grid",
        ),
        ui.div(
            chart_card(
                "Province comparison vs history",
                "Selected-month values benchmarked against each province's historical average for that month.",
                "comparison_plot", 360,
            ),
            class_="duo-grid",
        ),
        # ---- Methodology / transparency ----------------------------
        ui.div(
            ui.HTML(
                """
                <details open>
                  <summary>Methodology &amp; transparency — how the risk score is built</summary>
                  <div class="method-grid">
                    <div class="method-item"><b>water_score</b><span>Surface-water extent (%), min–max scaled. The flood proxy.</span></div>
                    <div class="method-item"><b>rainfall_score</b><span>Positive rainfall z-score (wet anomaly), scaled 0–1.</span></div>
                    <div class="method-item"><b>drought_score</b><span>Negative rainfall z-score (dry anomaly), scaled 0–1.</span></div>
                    <div class="method-item"><b>exposure_score</b><span>0.6 × population + 0.4 × cropland, each scaled 0–1.</span></div>
                  </div>
                  <div class="method-weights">
                    <b>combined_risk_score</b> = 0.35 · water + 0.25 · rainfall + 0.25 · drought + 0.15 · exposure.
                    All components are min–max normalised <i>across the whole panel</i>, so every value is
                    <b>relative to the delta</b>, not absolute. Daily-derived rainfall indicators explain
                    one-day extremes, rainy-day frequency, and dry spells, but they do not change this
                    combined risk formula.
                  </div>
                </details>
                """
            ),
            ui.div(
                "⚠ Surface water is a flood proxy from satellite water extent — not official "
                "flood-impact data. The combined score is a relative, heuristic indicator and "
                "must not be read as an official flood probability.",
                class_="warning-pill",
            ),
            class_="card method-card",
        ),
        ui.div(
            "All views are linked by the global filters. Rainfall has the longest coverage; "
            "daily-derived rainfall indicators stay monthly in the dashboard; surface-water "
            "and population layers are shown only where available.",
            class_="flow-note",
        ),
        class_="app-shell",
    ),
)


# ==========================================================
# Server helper functions
# ==========================================================

def current_all_provinces_df(input):
    y = int(input.year())
    m = int(input.month())
    return df[(df["year"] == y) & (df["month"] == m)].copy()


def current_filter_df(input):
    d = current_all_provinces_df(input)
    p = input.province()
    if p != "All Provinces":
        d = d[d["province_name"] == p]
    return d


def latest_available_year(column, availability_column, selected_year):
    valid_years = sorted(
        df.loc[df[availability_column] & (df[column] > 0), "year"]
        .dropna()
        .unique()
        .tolist()
    )
    valid_years = [int(y) for y in valid_years if int(y) <= selected_year]
    return max(valid_years) if valid_years else None


def static_available_year(column, availability_column):
    valid_years = sorted(
        df.loc[df[availability_column] & (df[column] > 0), "year"]
        .dropna()
        .unique()
        .tolist()
    )
    return int(max(valid_years)) if valid_years else None


def selected_province_or_mean_year_df(input):
    y = int(input.year())
    p = input.province()

    if p == "All Provinces":
        d = (
            df[df["year"] == y]
            .groupby("month", as_index=False)
            .agg(
                rainfall_mm=("rainfall_mm", "mean"),
                monthly_mean=("monthly_mean", "mean"),
                water_area_km2=("water_area_km2", "sum"),
                combined_risk_score=("combined_risk_score", "mean"),
            )
        )
        return d

    return df[(df["year"] == y) & (df["province_name"] == p)].copy()


def selected_daily_history_df(input):
    selected_years = input.history_year_range()
    start_year = int(selected_years[0])
    end_year = int(selected_years[1])
    p = input.forecast_province()
    province_df = split_daily_history.get(p, pd.DataFrame())
    if province_df.empty:
        return province_df.copy()
    return (
        province_df[(province_df["year"] >= start_year) & (province_df["year"] <= end_year)][["date", "rainfall_mm"]]
        .sort_values("date")
        .reset_index(drop=True)
    )


def selected_daily_forecast_df(input):
    p = input.forecast_province()
    horizon_months = int(input.forecast_horizon_months())
    d = split_daily_forecasts.get(p, pd.DataFrame()).copy()

    if d.empty:
        return d

    forecast_start = pd.Timestamp(d["date"].min())
    forecast_end = min(
        pd.Timestamp(d["date"].max()),
        forecast_start + pd.DateOffset(months=horizon_months) - pd.Timedelta(days=1),
    )
    return d[(d["date"] >= forecast_start) & (d["date"] <= forecast_end)].copy()


# ==========================================================
# Server
# ==========================================================

def server(input, output, session):

    @reactive.effect
    def _log_filters():
        logger.info(
            f"User filter updated: Province={input.province()}, Year={input.year()}, "
            f"Month={input.month()}, Metric={input.metric()}"
        )

    # ---- Dynamic narrative -------------------------------------
    @output
    @render.ui
    def narrative():
        p = input.province()
        y = int(input.year())
        m = int(input.month())
        headline, bullets, badge, color = build_narrative(p, y, m)
        note = interpretation_note(p, y, m)

        return ui.div(
            ui.div(
                ui.div(
                    ui.h4(headline),
                    ui.span(badge, class_="risk-badge", style=f"background:{color};"),
                    class_="narrative-head",
                ),
                ui.HTML("<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>"),
                ui.div(ui.HTML(note), class_="interp-note"),
                class_="narrative-card",
            )
        )

    # ---- KPI cards ---------------------------------------------
    @output
    @render.ui
    def kpi_rain():
        d = current_filter_df(input)
        if d.empty:
            return ui.div("N/A", class_="kpi-value")
        return ui.div(f"{d['rainfall_mm'].mean():,.1f} mm", class_="kpi-value")

    @output
    @render.ui
    def kpi_water():
        d = current_filter_df(input)
        d = d.dropna(subset=["water_area_km2"])
        if d.empty:
            return ui.div("N/A", class_="kpi-value")
        return ui.div(f"{d['water_area_km2'].sum():,.1f} km²", class_="kpi-value")

    @output
    @render.ui
    def kpi_pop():
        d = current_filter_df(input)
        d = d.dropna(subset=["population_total"])
        if d.empty:
            return ui.div("N/A", class_="kpi-value")
        return ui.div(f"{d['population_total'].sum():,.0f}", class_="kpi-value")

    @output
    @render.ui
    def kpi_top():
        d = current_all_provinces_df(input)
        metric = input.metric()
        d = d.dropna(subset=[metric])
        if d.empty:
            return ui.div("N/A", class_="kpi-value")
        top_row = d.sort_values(metric, ascending=False).iloc[0]
        return ui.div(str(top_row["province_name"]), class_="kpi-value")

    # ---- ACT 1: map + ranking + breakdown ----------------------
    @output
    @render_widget
    def map_plot():
        d = current_all_provinces_df(input)
        metric = input.metric()
        label = metric_labels.get(metric, metric)
        color_scale = metric_color_scales.get(metric, "Viridis")
        hover_data = {
            "rainfall_mm": ":,.1f",
            "rainfall_anomaly": ":,.1f",
            "water_area_km2": ":,.1f",
            "water_area_pct": ":,.2f",
            "population_total": ":,.0f",
            "cropland_area_km2": ":,.1f",
            "province_name": False,
        }
        for daily_metric in daily_hover_metrics:
            hover_data[daily_metric] = metric_plot_formats.get(daily_metric, ":.2f")
        hover_data[metric] = metric_plot_formats.get(metric, ":.2f")

        fig = px.choropleth_mapbox(
            d,
            geojson=geojson_data,
            locations="province_name",
            featureidkey="properties.ADM1_NAME",
            color=metric,
            hover_name="province_name",
            hover_data=hover_data,
            color_continuous_scale=color_scale,
            mapbox_style="carto-darkmatter",
            center={"lat": 9.95, "lon": 105.65},
            zoom=6.7,
            opacity=0.78,
        )
        fig.update_traces(
            marker_line_width=1.15,
            marker_line_color="rgba(248,250,252,0.55)",
            selector=dict(type="choroplethmapbox"),
        )

        labels = map_label_df[map_label_df["province_name"].isin(d["province_name"])].copy()
        if not labels.empty:
            fig.add_trace(go.Scattermapbox(
                lon=labels["lon"],
                lat=labels["lat"],
                text=labels["province_name"],
                mode="text",
                textfont=dict(size=16, color="rgba(2,6,23,0.92)"),
                hoverinfo="skip",
                showlegend=False,
            ))
            fig.add_trace(go.Scattermapbox(
                lon=labels["lon"],
                lat=labels["lat"],
                text=labels["province_name"],
                mode="text",
                textfont=dict(size=12, color="#fff7ed"),
                hoverinfo="skip",
                showlegend=False,
            ))
        fig.update_layout(
            height=580,
            autosize=True,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f8fafc"),
            coloraxis_colorbar=dict(
                title=label,
                thickness=14,
                len=0.65,
                y=0.5,
                x=0.96,
                bgcolor="rgba(15,23,42,0.7)",
            ),
        )
        return fig

    @output
    @render_widget
    def ranking_plot():
        d = current_all_provinces_df(input)
        metric = input.metric()
        label = metric_labels.get(metric, metric)
        selected_p = input.province()

        d = (
            d[["province_name", metric]]
            .dropna()
            .sort_values(metric, ascending=True)
            .tail(13)
        )
        if d.empty:
            return empty_fig(255)

        # Highlight the selected province within the ranking.
        colors = [
            PALETTE["amber"] if (selected_p != "All Provinces" and p == selected_p)
            else PALETTE["accent"]
            for p in d["province_name"]
        ]

        fig = px.bar(
            d, x=metric, y="province_name", orientation="h", text=metric,
            labels={metric: label, "province_name": ""},
        )
        fig.update_traces(
            marker_color=colors, texttemplate=metric_text_template(metric),
            textposition="outside", cliponaxis=False,
        )
        fig.update_layout(
            margin=dict(l=5, r=45, t=5, b=25), height=255,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=11), showlegend=False,
            xaxis=dict(showgrid=True, gridcolor=PALETTE["grid"], zeroline=False),
            yaxis=dict(showgrid=False, automargin=True),
        )
        return fig

    @output
    @render_widget
    def breakdown_plot():
        d = current_filter_df(input)
        comps = ["water_score", "rainfall_score", "drought_score", "exposure_score"]
        labels = ["Water", "Rainfall", "Drought", "Exposure"]
        colors = [PALETTE["cyan"], PALETTE["accent"], PALETTE["amber"], PALETTE["purple"]]
        if d.empty:
            vals = [0, 0, 0, 0]
        else:
            vals = [float(d[c].mean()) for c in comps]

        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"{v:.2f}" for v in vals], textposition="outside",
        ))
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=25), height=255,
            yaxis=dict(range=[0, 1.08], showgrid=True, gridcolor=PALETTE["grid"], title="Normalized score"),
            xaxis=dict(showgrid=False),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=11), showlegend=False,
        )
        return fig

    # ---- ACT 2: scatter + rainfall trend -----------------------
    @output
    @render_widget
    def scatter_plot():
        d = current_all_provinces_df(input)
        d = d[(d["water_area_km2"] > 0) | (d["rainfall_anomaly"] != 0)].copy()
        if d.empty:
            return empty_fig(360, "No rainfall/water pairs for this month")

        selected_p = input.province()
        sizes = scaled_sizes(d["population_total"])
        line_colors = [
            "#f8fafc" if (selected_p != "All Provinces" and p == selected_p) else "rgba(0,0,0,0)"
            for p in d["province_name"]
        ]

        fig = go.Figure(go.Scatter(
            x=d["rainfall_anomaly"],
            y=d["water_area_km2"],
            mode="markers+text",
            text=d["province_name"],
            textposition="top center",
            textfont=dict(size=9, color=PALETTE["muted"]),
            marker=dict(
                size=sizes,
                color=d["combined_risk_score"],
                colorscale="YlOrRd",
                showscale=True,
                line=dict(width=2, color=line_colors),
                colorbar=dict(title="Risk", thickness=12, len=0.7),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>Rain anomaly: %{x:,.0f} mm"
                "<br>Water: %{y:,.0f} km²<extra></extra>"
            ),
        ))
        fig.add_vline(x=0, line_dash="dot", line_color=PALETTE["muted"])
        apply_dark_layout(fig, 360)
        fig.update_xaxes(title="Rainfall anomaly (mm)")
        fig.update_yaxes(title="Surface water (km²)")
        return fig

    @output
    @render_widget
    def rain_trend_plot():
        d = selected_province_or_mean_year_df(input)
        selected_m = int(input.month())
        if d.empty:
            return empty_fig(360)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=d["month"], y=d["rainfall_mm"], mode="lines+markers",
            name="Selected year", line=dict(color=PALETTE["accent"], width=3),
        ))
        fig.add_trace(go.Scatter(
            x=d["month"], y=d["monthly_mean"], mode="lines+markers",
            name="Historical monthly mean", line=dict(color=PALETTE["rose"], width=2, dash="dash"),
        ))
        fig.add_vline(x=selected_m, line_dash="dot", line_color="#e2e8f0")
        apply_dark_layout(fig, 360, legend=True)
        fig.update_xaxes(title="Month", dtick=1)
        fig.update_yaxes(title="Rainfall (mm)")
        return fig

    # ---- ACT 3: daily-derived rainfall extremes ----------------
    @output
    @render.ui
    def extreme_kpis():
        d = current_filter_df(input)
        if d.empty:
            max_rain = heavy_days = dry_spell = "N/A"
        else:
            max_rain = format_metric_value(d["max_1day_rainfall"].max(), "max_1day_rainfall")
            heavy_days = format_metric_value(d["heavy_rain_days_20mm"].mean(), "heavy_rain_days_20mm")
            dry_spell = format_metric_value(d["max_consecutive_dry_days"].max(), "max_consecutive_dry_days")

        return ui.div(
            ui.div(
                ui.div("Max 1-day rain", class_="extreme-kpi-label"),
                ui.div(max_rain, class_="extreme-kpi-value"),
                ui.div("Largest daily rainfall inside the selected month.", class_="extreme-kpi-note"),
                class_="extreme-kpi",
            ),
            ui.div(
                ui.div("Heavy rain days", class_="extreme-kpi-label"),
                ui.div(heavy_days, class_="extreme-kpi-value"),
                ui.div("Average count of days with at least 20 mm rainfall.", class_="extreme-kpi-note"),
                class_="extreme-kpi",
            ),
            ui.div(
                ui.div("Longest dry spell", class_="extreme-kpi-label"),
                ui.div(dry_spell, class_="extreme-kpi-value"),
                ui.div("Longest run of daily rainfall below 1 mm.", class_="extreme-kpi-note"),
                class_="extreme-kpi",
            ),
        )

    @output
    @render_widget
    def monthly_rain_structure_plot():
        d = current_filter_df(input)
        if d.empty:
            return empty_fig(360)

        dry_days = float(d["dry_days_count"].mean())
        extreme_days = float(d["heavy_rain_days_50mm"].mean())
        heavy_days = max(float(d["heavy_rain_days_20mm"].mean()) - extreme_days, 0)
        rainy_light_days = max(float(d["rain_days_count"].mean()) - float(d["heavy_rain_days_20mm"].mean()), 0)
        observed_days = float(d["days_observed"].mean())

        parts = [
            ("Dry <1 mm", dry_days, "#f59e0b"),
            ("Rain 1-19 mm", rainy_light_days, "#38bdf8"),
            ("Heavy 20-49 mm", heavy_days, "#2563eb"),
            ("Extreme >=50 mm", extreme_days, "#f43f5e"),
        ]
        labels, values, colors = zip(*parts)

        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.58,
            marker=dict(colors=colors, line=dict(color="#0d1b2e", width=2)),
            textinfo="label+percent",
            textposition="outside",
            hovertemplate="<b>%{label}</b><br>%{value:.1f} days<extra></extra>",
            sort=False,
        ))
        fig.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=10, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"], size=11),
            legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
            showlegend=True,
        )
        fig.add_annotation(
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
            text=f"{observed_days:.1f}<br>observed<br>days",
            font=dict(color="#f8fafc", size=13),
            align="center",
        )
        return fig

    @output
    @render_widget
    def extreme_signature_plot():
        d = current_filter_df(input)
        if d.empty:
            return empty_fig(360)

        signature_metrics = [
            ("Max 1-day", "max_1day_rainfall"),
            ("Rainy share", "rain_day_ratio"),
            ("Heavy days", "heavy_rain_days_20mm"),
            ("Dry spell", "max_consecutive_dry_days"),
            ("Wet spell", "max_consecutive_wet_days"),
        ]

        values = []
        for _, col in signature_metrics:
            raw_value = float(d[col].mean())
            col_min = float(df[col].min())
            col_max = float(df[col].max())
            values.append(0 if col_max == col_min else (raw_value - col_min) / (col_max - col_min))

        labels = [label for label, _ in signature_metrics]
        fig = go.Figure(go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            line=dict(color=PALETTE["accent"], width=3),
            fillcolor="rgba(56,189,248,0.22)",
            marker=dict(color=PALETTE["amber"], size=7),
            hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
        ))
        fig.update_layout(
            height=360,
            margin=dict(l=35, r=35, t=20, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"], size=11),
            showlegend=False,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(range=[0, 1], showticklabels=True, tickfont=dict(size=9), gridcolor=PALETTE["grid"]),
                angularaxis=dict(gridcolor=PALETTE["grid"]),
            ),
        )
        return fig

    @output
    @render_widget
    def extreme_ranking_plot():
        d = current_all_provinces_df(input)
        metric = input.extreme_metric()
        label = metric_labels.get(metric, metric)
        selected_p = input.province()

        d = (
            d[["province_name", metric]]
            .dropna()
            .sort_values(metric, ascending=True)
            .tail(13)
        )
        if d.empty:
            return empty_fig(360)

        colors = [
            PALETTE["amber"] if (selected_p != "All Provinces" and p == selected_p)
            else PALETTE["accent"]
            for p in d["province_name"]
        ]
        fig = px.bar(
            d, x=metric, y="province_name", orientation="h", text=metric,
            labels={metric: label, "province_name": ""},
        )
        fig.update_traces(
            marker_color=colors,
            texttemplate=metric_text_template(metric),
            textposition="outside",
            cliponaxis=False,
        )
        apply_dark_layout(fig, 360)
        fig.update_layout(margin=dict(l=5, r=45, t=5, b=38))
        fig.update_xaxes(title=label)
        fig.update_yaxes(showgrid=False, automargin=True)
        return fig

    @output
    @render_widget
    def extreme_trend_plot():
        y = int(input.year())
        p = input.province()
        metric = input.extreme_metric()
        label = metric_labels.get(metric, metric)
        selected_m = int(input.month())

        if p == "All Provinces":
            d = (
                df[df["year"] == y]
                .groupby("month", as_index=False)[metric]
                .mean()
                .sort_values("month")
            )
            name = "Delta average"
        else:
            d = (
                df[(df["year"] == y) & (df["province_name"] == p)]
                [["month", metric]]
                .sort_values("month")
            )
            name = p
        d = d.set_index("month").reindex(range(1, 13)).reset_index()
        if d[metric].dropna().empty:
            return empty_fig(360)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=d["month"],
            y=d[metric],
            mode="lines+markers",
            name=name,
            line=dict(color=PALETTE["accent"], width=3),
            marker=dict(size=8),
            hovertemplate=f"Month %{{x}}<br>{label}: %{{y{metric_plot_formats.get(metric, ':.2f')}}}<extra></extra>",
        ))
        selected = d[d["month"] == selected_m]
        if not selected.empty:
            fig.add_trace(go.Scatter(
                x=selected["month"],
                y=selected[metric],
                mode="markers",
                name="Selected month",
                marker=dict(color=PALETTE["amber"], size=13),
                hovertemplate=f"Selected month<br>{label}: %{{y{metric_plot_formats.get(metric, ':.2f')}}}<extra></extra>",
            ))
        fig.add_vline(x=selected_m, line_dash="dot", line_color="#e2e8f0")
        apply_dark_layout(fig, 360, legend=True)
        fig.update_xaxes(title="Month", dtick=1)
        fig.update_yaxes(title=label)
        if metric in {"rain_day_ratio", "dry_day_ratio"}:
            fig.update_yaxes(tickformat=".0%")
        return fig

    @output
    @render_widget
    def extreme_calendar_heatmap():
        y = int(input.year())
        metric = input.extreme_metric()
        label = metric_labels.get(metric, metric)
        d = df[df["year"] == y].copy()
        if d.empty:
            return empty_fig(360)

        pivot = d.pivot_table(
            index="province_name",
            columns="month",
            values=metric,
            aggfunc="mean",
        ).reindex(provinces)
        if pivot.dropna(how="all").empty:
            return empty_fig(360)

        fig = px.imshow(
            pivot,
            labels=dict(x="Month", y="", color=label),
            color_continuous_scale=metric_color_scales.get(metric, "Viridis"),
            aspect="auto",
        )
        fig.update_layout(
            margin=dict(l=80, r=10, t=10, b=35),
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=10),
            coloraxis_colorbar=dict(title=label, thickness=10, len=0.75),
            xaxis=dict(dtick=1),
        )
        return fig

    # ---- ACT 4: risk-over-time + seasonality + heatmap ---------
    @output
    @render_widget
    def risk_time_plot():
        p = input.province()
        if p == "All Provinces":
            t = (
                df.groupby("date", as_index=False)["combined_risk_score"].mean()
                .sort_values("date")
            )
            name = "Delta average"
        else:
            t = df[df["province_name"] == p].sort_values("date")
            name = p
        if t.empty:
            return empty_fig(320)

        sel_date = pd.Timestamp(year=int(input.year()), month=int(input.month()), day=1)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=t["date"], y=t["combined_risk_score"], mode="lines",
            name=name, line=dict(color=PALETTE["accent"], width=2),
            fill="tozeroy", fillcolor="rgba(56,189,248,0.12)",
        ))
        # Mark the currently selected period.
        sel = t[t["date"] == sel_date]
        if not sel.empty:
            fig.add_trace(go.Scatter(
                x=sel["date"], y=sel["combined_risk_score"], mode="markers",
                name="Selected", marker=dict(color=PALETTE["amber"], size=12, symbol="circle"),
            ))
        apply_dark_layout(fig, 320)
        fig.update_yaxes(title="Combined risk score")
        fig.update_xaxes(title="")
        return fig

    @output
    @render_widget
    def seasonality_plot():
        p = input.province()
        base = df if p == "All Provinces" else df[df["province_name"] == p]
        clim = base.groupby("month", as_index=False)["rainfall_mm"].mean()
        clim = clim.set_index("month").reindex(range(1, 13)).fillna(0).reset_index()
        if clim["rainfall_mm"].sum() == 0:
            return empty_fig(320)

        selected_m = int(input.month())
        colors = [
            PALETTE["amber"] if mth == selected_m else PALETTE["cyan"]
            for mth in clim["month"]
        ]
        fig = go.Figure(go.Bar(
            x=[MONTH_NAMES[m - 1][:3] for m in clim["month"]],
            y=clim["rainfall_mm"], marker_color=colors,
            hovertemplate="%{x}: %{y:,.0f} mm<extra></extra>",
        ))
        apply_dark_layout(fig, 320)
        fig.update_yaxes(title="Avg rainfall (mm)")
        fig.update_xaxes(title="", showgrid=False)
        return fig

    @output
    @render_widget
    def rainfall_forecast_plot():
        history = selected_daily_history_df(input)
        forecast = selected_daily_forecast_df(input)
        if history.empty and forecast.empty:
            return empty_fig(420, "No historical or forecast rainfall data available")

        selected_name = input.forecast_province()
        fig = go.Figure()

        if not history.empty:
            fig.add_trace(go.Scatter(
                x=history["date"],
                y=history["rainfall_mm"],
                mode="lines",
                name=f"{selected_name} history",
                line=dict(color=PALETTE["accent"], width=1.8),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Observed rainfall: %{y:,.1f} mm<extra></extra>",
            ))

        if not forecast.empty:
            fig.add_trace(go.Scatter(
                x=forecast["date"],
                y=forecast["predicted_rainfall_mm"],
                mode="lines",
                name=f"{selected_name} forecast",
                line=dict(color=PALETTE["amber"], width=2.5, dash="dash"),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Predicted rainfall: %{y:,.1f} mm<extra></extra>",
            ))
            forecast_start = pd.Timestamp(forecast["date"].min())
            forecast_end = pd.Timestamp(forecast["date"].max())
            fig.add_vline(x=forecast_start, line_dash="dot", line_color=PALETTE["amber"])
            fig.add_vrect(
                x0=forecast_start,
                x1=forecast_end,
                fillcolor="rgba(245, 158, 11, 0.08)",
                line_width=0,
                layer="below",
            )

        apply_dark_layout(fig, 420, legend=True)
        fig.update_yaxes(title="Daily rainfall (mm)")
        fig.update_xaxes(title="", rangeslider=dict(visible=True), type="date")
        return fig

    @output
    @render.ui
    def forecast_window_note():
        history = selected_daily_history_df(input)
        forecast = selected_daily_forecast_df(input)
        history_text = "No historical slice selected."
        forecast_text = "No forecast file found."

        if not history.empty:
            history_text = (
                f"Historical window: <b>{history['date'].min():%Y-%m-%d}</b> to "
                f"<b>{history['date'].max():%Y-%m-%d}</b>."
            )
        if not forecast.empty:
            forecast_text = (
                f"Forecast window: <b>{forecast['date'].min():%Y-%m-%d}</b> to "
                f"<b>{forecast['date'].max():%Y-%m-%d}</b> "
                f"({int(input.forecast_horizon_months())} month(s) ahead)."
            )

        return ui.div(
            ui.HTML(
                f"{history_text} {forecast_text} "
                "Observed data comes from the raw daily rainfall file; future values come from the recursive XGBoost outputs in modeling/result."
            ),
            class_="forecast-note",
        )

    @output
    @render_widget
    def heatmap_plot():
        y = int(input.year())
        d = df[df["year"] == y].copy()
        if d.empty:
            return empty_fig(320)
        pivot = d.pivot_table(
            index="province_name", columns="month",
            values="rainfall_zscore", aggfunc="mean",
        ).reindex(provinces)

        fig = px.imshow(
            pivot, labels=dict(x="Month", y="", color="Z-score"),
            color_continuous_scale="RdBu", zmin=-2, zmax=2, aspect="auto",
        )
        fig.update_layout(
            margin=dict(l=80, r=5, t=10, b=35), height=320,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=10),
            coloraxis_colorbar=dict(title="Anomaly", thickness=10, len=0.75),
            xaxis=dict(dtick=1),
        )
        return fig

    # ---- ACT 4: exposure + comparison --------------------------
    @output
    @render_widget
    def exposure_plot():
        y = int(input.year())
        d = (
            df[df["year"] == y]
            .groupby("province_name", as_index=False)
            .agg(
                population_total=("population_total", "mean"),
                cropland_area_km2=("cropland_area_km2", "mean"),
                combined_risk_score=("combined_risk_score", "mean"),
            )
        )
        d = d[(d["population_total"] > 0) | (d["cropland_area_km2"] > 0)]
        if d.empty:
            return empty_fig(360, "No exposure data for this year")

        selected_p = input.province()
        sizes = scaled_sizes(d["combined_risk_score"])
        line_colors = [
            "#f8fafc" if (selected_p != "All Provinces" and p == selected_p) else "rgba(0,0,0,0)"
            for p in d["province_name"]
        ]
        fig = go.Figure(go.Scatter(
            x=d["population_total"], y=d["cropland_area_km2"],
            mode="markers+text", text=d["province_name"],
            textposition="top center", textfont=dict(size=9, color=PALETTE["muted"]),
            marker=dict(
                size=sizes, color=d["combined_risk_score"], colorscale="YlOrRd",
                showscale=True, line=dict(width=2, color=line_colors),
                colorbar=dict(title="Risk", thickness=12, len=0.7),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>Population: %{x:,.0f}"
                "<br>Cropland: %{y:,.0f} km²<extra></extra>"
            ),
        ))
        apply_dark_layout(fig, 360)
        fig.update_xaxes(title="Population")
        fig.update_yaxes(title="Cropland area (km²)")
        return fig

    @output
    @render_widget
    def population_exposure_plot():
        selected_year = int(input.year())
        pop_year = latest_available_year("population_total", "has_population", selected_year)
        if pop_year is None:
            return empty_fig(360, "No population exposure data available")

        d = (
            df[(df["year"] == pop_year) & df["has_population"]]
            .groupby("province_name", as_index=False)
            .agg(population_total=("population_total", "mean"))
            .sort_values("population_total", ascending=True)
        )
        d = d[d["population_total"] > 0]
        if d.empty:
            return empty_fig(360, "No population exposure data available")

        selected_p = input.province()
        colors = [
            PALETTE["amber"] if (selected_p != "All Provinces" and p == selected_p)
            else PALETTE["purple"]
            for p in d["province_name"]
        ]
        fig = go.Figure(go.Bar(
            x=d["population_total"],
            y=d["province_name"],
            orientation="h",
            marker_color=colors,
            text=[f"{v/1_000_000:.2f}M" for v in d["population_total"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Population: %{x:,.0f}<extra></extra>",
        ))
        apply_dark_layout(fig, 360)
        fig.update_layout(margin=dict(l=90, r=55, t=30, b=38))
        fig.update_xaxes(title=f"Population ({pop_year})")
        fig.update_yaxes(showgrid=False)
        fig.add_annotation(
            x=1, y=1.08, xref="paper", yref="paper", showarrow=False,
            text=f"Displaying WorldPop {pop_year}",
            font=dict(color=PALETTE["muted"], size=11),
            xanchor="right",
        )
        return fig

    @output
    @render_widget
    def cropland_exposure_plot():
        crop_year = static_available_year("cropland_area_km2", "has_cropland")
        if crop_year is None:
            return empty_fig(360, "No cropland exposure data available")

        d = (
            df[(df["year"] == crop_year) & df["has_cropland"]]
            .groupby("province_name", as_index=False)
            .agg(cropland_area_km2=("cropland_area_km2", "mean"))
            .sort_values("cropland_area_km2", ascending=True)
        )
        d = d[d["cropland_area_km2"] > 0]
        if d.empty:
            return empty_fig(360, "No cropland exposure data available")

        selected_p = input.province()
        colors = [
            PALETTE["amber"] if (selected_p != "All Provinces" and p == selected_p)
            else PALETTE["green"]
            for p in d["province_name"]
        ]
        fig = go.Figure(go.Bar(
            x=d["cropland_area_km2"],
            y=d["province_name"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:,.0f}" for v in d["cropland_area_km2"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Cropland: %{x:,.1f} kmÂ²<extra></extra>",
        ))
        apply_dark_layout(fig, 360)
        fig.update_layout(margin=dict(l=90, r=55, t=30, b=38))
        fig.update_xaxes(title=f"Cropland area (kmÂ²), {crop_year} snapshot")
        fig.update_yaxes(showgrid=False)
        fig.add_annotation(
            x=1, y=1.08, xref="paper", yref="paper", showarrow=False,
            text=f"Displaying ESA WorldCover {crop_year}",
            font=dict(color=PALETTE["muted"], size=11),
            xanchor="right",
        )
        return fig

    @output
    @render_widget
    def comparison_plot():
        y = int(input.year())
        m = int(input.month())
        metric = input.metric()
        label = metric_labels.get(metric, metric)

        selected = df[(df["year"] == y) & (df["month"] == m)][["province_name", metric]].copy()
        avg = (
            df[df["month"] == m]
            .groupby("province_name", as_index=False)[metric]
            .mean()
            .rename(columns={metric: "historical_average"})
        )

        merged = selected.merge(avg, on="province_name", how="left").dropna()
        if merged.empty:
            return empty_fig(360)
        merged = merged.sort_values(metric, ascending=False).head(10)
        merged = merged.sort_values(metric, ascending=True)

        fig = go.Figure()
        for _, row in merged.iterrows():
            fig.add_shape(
                type="line", x0=row["historical_average"], x1=row[metric],
                y0=row["province_name"], y1=row["province_name"],
                line=dict(color="#334155", width=2),
            )
        fig.add_trace(go.Scatter(
            x=merged["historical_average"], y=merged["province_name"], mode="markers",
            name="Historical avg", marker=dict(color=PALETTE["muted"], size=9, symbol="circle-open"),
        ))
        fig.add_trace(go.Scatter(
            x=merged[metric], y=merged["province_name"], mode="markers",
            name="Selected month", marker=dict(color=PALETTE["accent"], size=10),
        ))
        apply_dark_layout(fig, 360, legend=True)
        fig.update_xaxes(title=label)
        fig.update_yaxes(title="", showgrid=False)
        return fig


app = App(app_ui, server)
