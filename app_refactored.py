from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import json
import numpy as np
import logging
from pathlib import Path

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MekongFloodLens")


# ==========================================================
# Data loading  (kept robust - tolerant of missing columns)
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

# Default values for any column the panel might not ship with. Keeps every
# chart defined even if the upstream CSV schema drifts.
default_columns = {
    "rainfall_mm": 0,
    "monthly_mean": np.nan,
    "rainfall_anomaly": 0,
    "rainfall_zscore": 0,
    "water_area_km2": np.nan,
    "water_area_pct": np.nan,
    "population_total": np.nan,
    "cropland_area_km2": np.nan,
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

# Long-run monthly climatology (per province / calendar month) - used as the
# "normal" baseline for the seasonal and trend views.
if df["monthly_mean"].isna().all():
    df["monthly_mean"] = df.groupby(["province_name", "month"])["rainfall_mm"].transform("mean")


def minmax(series):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    spread = s.max() - s.min()
    if spread == 0:
        return pd.Series(0, index=s.index)
    return (s - s.min()) / spread


# ----------------------------------------------------------
# Dryness index (PROXY) - built only from rainfall columns.
# It keeps the non-negative rainfall deficit signal (negative anomaly z-score),
# then rescales it to 0-1 across the panel. It is a *relative* indicator,
# NOT an official drought classification.
# ----------------------------------------------------------
deficit = (-df["rainfall_zscore"]).clip(lower=0)
df["dry_index"] = minmax(deficit)

# Availability flags so exposure / water layers degrade gracefully.
df["has_population"] = df["population_total"].notna()
df["has_cropland"] = df["cropland_area_km2"].notna()
df["has_water"] = df["water_area_km2"].notna()

# Keep a copy with real NaNs for water (so "no coverage" stays distinct from 0)
df["water_area_km2_raw"] = df["water_area_km2"]
df["water_area_pct_raw"] = df["water_area_pct"]

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
WATER_YEARS = sorted(df.loc[df["has_water"], "year"].unique().tolist())

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ==========================================================
# Metric registry - rainfall / dryness / surface-water focused.
# Combined risk score is intentionally NOT offered as a story metric.
# ==========================================================

metric_options = {
    "rainfall_mm": "Rainfall (mm)",
    "rainfall_anomaly": "Rainfall anomaly (mm)",
    "rainfall_zscore": "Rainfall anomaly (z-score)",
    "dry_index": "Dryness index (proxy)",
    "dry_day_ratio": "Dry-day share",
    "max_consecutive_dry_days": "Longest dry spell (days)",
    "water_area_km2": "Surface water area (km^2)",
    "water_area_pct": "Surface water (%)",
}

metric_labels = dict(metric_options)

ANOMALY_COLORSCALE = [
    [0.0, "#9a3412"],
    [0.22, "#c2410c"],
    [0.5, "#f8fafc"],
    [0.78, "#38bdf8"],
    [1.0, "#14b8a6"],
]

metric_color_scales = {
    "rainfall_mm": "Blues",
    "rainfall_anomaly": ANOMALY_COLORSCALE,
    "rainfall_zscore": ANOMALY_COLORSCALE,
    "dry_index": "YlOrBr",
    "dry_day_ratio": "YlOrBr",
    "max_consecutive_dry_days": "YlOrBr",
    "water_area_km2": "Blues",
    "water_area_pct": "Blues",
}

metric_plot_formats = {
    "rainfall_mm": ":,.1f",
    "rainfall_anomaly": ":+,.1f",
    "rainfall_zscore": ":+,.2f",
    "dry_index": ":.2f",
    "dry_day_ratio": ":.0%",
    "max_consecutive_dry_days": ":,.0f",
    "water_area_km2": ":,.1f",
    "water_area_pct": ":,.2f",
}

# Metrics where a HIGHER value means drier conditions (used for narration).
DRY_METRICS = {"dry_index", "dry_day_ratio", "max_consecutive_dry_days"}
WATER_METRICS = {"water_area_km2", "water_area_pct"}


# ==========================================================
# Plot styling helpers (shared dark theme)
# ==========================================================

PALETTE = {
    "accent": "#14b8a6",
    "cyan": "#38bdf8",
    "purple": "#0f2032",
    "rose": "#c2410c",
    "rust": "#c2410c",
    "amber": "#f59e0b",
    "green": "#22c55e",
    "grid": "#31445f",
    "muted": "#9fb0c7",
    "text": "#e2e8f0",
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
    if metric in {"dry_day_ratio", "rain_day_ratio"}:
        return f"{value * 100:.0f}%"
    if metric in {"max_consecutive_dry_days", "rain_days_count", "dry_days_count"}:
        return f"{value:,.0f} days"
    if metric in {"rainfall_mm", "rainfall_anomaly", "max_1day_rainfall"}:
        return f"{value:,.1f} mm"
    if metric == "rainfall_zscore":
        return f"{value:+,.2f}"
    if metric == "water_area_km2":
        return f"{value:,.1f} km^2"
    if metric == "water_area_pct":
        return f"{value:,.2f}%"
    if metric == "dry_index":
        return f"{value:.2f}"
    return f"{value:.2f}"


# ==========================================================
# Narrative helpers - rainfall / dryness / water story
# (No combined-risk language.)
# ==========================================================

def month_label(m):
    return MONTH_NAMES[int(m) - 1]


def summary_bullets(province, year, month):
    """Plain-English observations for the selected period (delta or province)."""
    mname = month_label(month)
    mdf = df[(df["year"] == year) & (df["month"] == month)].copy()
    if mdf.empty:
        return ["No records for this period - try a different year or month."]

    wettest = mdf.sort_values("rainfall_mm", ascending=False).iloc[0]
    driest = mdf.sort_values("dry_index", ascending=False).iloc[0]
    water_df = mdf[mdf["has_water"]]

    if province == "All Provinces":
        bullets = [
            f"Across the delta in {mname} {year}, average rainfall was "
            f"<b>{mdf['rainfall_mm'].mean():,.0f} mm</b>.",
            f"<b>{wettest['province_name']}</b> was the wettest "
            f"({wettest['rainfall_mm']:,.0f} mm); "
            f"<b>{driest['province_name']}</b> looked driest on the dryness proxy.",
        ]
        if not water_df.empty:
            top_water = water_df.sort_values("water_area_km2", ascending=False).iloc[0]
            bullets.append(
                f"Mapped surface water totalled "
                f"<b>{water_df['water_area_km2'].sum():,.0f} km^2</b>, led by "
                f"<b>{top_water['province_name']}</b>."
            )
        bullets.append("Pick a single province in the sidebar to follow its own story over time.")
        return bullets

    row = mdf[mdf["province_name"] == province]
    if row.empty:
        return [f"{province} has no record for {mname} {year}."]
    row = row.iloc[0]

    anomaly = row["rainfall_anomaly"]
    if anomaly > 5:
        wet_txt = f"<b>wetter than normal</b> ({anomaly:+,.0f} mm vs the long-run average)"
    elif anomaly < -5:
        wet_txt = f"<b>drier than normal</b> ({anomaly:+,.0f} mm vs the long-run average)"
    else:
        wet_txt = "close to its long-run average"

    rain_rank = int((mdf["rainfall_mm"] > row["rainfall_mm"]).sum()) + 1
    bullets = [
        f"{province} received <b>{row['rainfall_mm']:,.0f} mm</b> in {mname} {year}, "
        f"{wet_txt}.",
        f"That ranks <b>#{rain_rank} of {len(mdf)}</b> provinces for rainfall this month.",
        f"Rainfall-deficit proxy: <b>{row['dry_index']:.2f}</b>. "
        f"Separate daily context: dry-day share {row['dry_day_ratio'] * 100:.0f}%, "
        f"longest dry spell {row['max_consecutive_dry_days']:.0f} days.",
    ]
    if row["has_water"] and row["water_area_km2"] > 0:
        bullets.append(
            f"Observed surface-water extent: <b>{row['water_area_km2']:,.0f} km^2</b> "
            "(satellite proxy)."
        )
    return bullets


# ==========================================================
# Styling
# ==========================================================

custom_css = """
:root {
    --bg: #08131f;
    --panel: #0f2032;
    --border: #29405c;
    --text: #e2e8f0;
    --muted: #9fb0c7;
    --accent: #14b8a6;
    --accent-2: #38bdf8;
}
html, body, .bslib-page-sidebar {
    background: var(--bg) !important;
    color: var(--text);
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
/* Header */
.app-header {
    padding: 18px 26px 14px 26px;
    border-bottom: 1px solid var(--border);
}
.app-header h1 {
    margin: 0;
    font-size: 2.0rem;
    font-weight: 800;
    letter-spacing: 0;
    background: linear-gradient(90deg, #14b8a6, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.app-header .subtitle {
    margin-top: 5px;
    color: var(--muted);
    max-width: 880px;
    line-height: 1.45;
    font-size: 0.92rem;
}
/* Sidebar */
.bslib-sidebar-layout > .sidebar {
    background: var(--panel) !important;
    border-right: 1px solid var(--border);
}
.bslib-sidebar-layout > .sidebar .sidebar-content { color: var(--text); }
.sidebar-section-title {
    font-weight: 800;
    color: #e2e8f0;
    font-size: 0.95rem;
    margin: 4px 0 2px 0;
}
.sidebar-hint {
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.4;
    margin-bottom: 6px;
}
.filter-action-row { margin: 2px 0 10px 0; }
.filter-action-row .btn {
    width: 100%;
    background: #14324b;
    border: 1px solid #32506f;
    color: #e2e8f0;
    border-radius: 10px;
    font-weight: 700;
}
.filter-action-row .btn:hover {
    background: #18415f;
    border-color: #4b6888;
    color: #f8fafc;
}
/* Tabs / cards */
.nav-tabs .nav-link {
    color: var(--muted) !important;
    border: none !important;
    font-weight: 700;
}
.nav-tabs .nav-link.active {
    color: #f8fafc !important;
    background: transparent !important;
    border-bottom: 2px solid var(--accent) !important;
}
.card, .bslib-card {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    color: var(--text);
}
.story-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.18);
}
.chart-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 16px;
}
.card-title {
    font-size: 1.03rem;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 4px;
}
.card-subtitle {
    color: var(--muted);
    font-size: 0.82rem;
    margin-bottom: 12px;
    line-height: 1.45;
}
.lead-note {
    color: #cbd5e1;
    background: rgba(20, 184, 166, 0.09);
    border: 1px solid rgba(20, 184, 166, 0.24);
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 16px;
    font-size: 0.9rem;
    line-height: 1.55;
}
.lead-note b { color: #e2e8f0; }
.obs-list { margin: 0; padding-left: 18px; color: #cbd5e1; font-size: 0.92rem; line-height: 1.6; }
.obs-list b { color: #f1f5f9; }
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 16px;
}
.kpi {
    border-radius: 16px;
    padding: 16px;
    min-height: 104px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: linear-gradient(135deg, #0f766e, #14b8a6);
}
.kpi.cyan { background: linear-gradient(135deg, #0f5f89, #38bdf8); }
.kpi.amber { background: linear-gradient(135deg, #b45309, #f59e0b); }
.kpi.green { background: linear-gradient(135deg, #166534, #22c55e); }
.kpi-label {
    text-transform: uppercase;
    letter-spacing: 0.10em;
    font-size: 0.70rem;
    font-weight: 800;
    opacity: 0.82;
    color: #f8fafc;
}
.kpi-value { font-size: 1.55rem; font-weight: 850; line-height: 1.1; margin-top: 6px; color: #fff; }
.kpi-note { font-size: 0.74rem; opacity: 0.85; color: #f1f5f9; }
.duo-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
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
.caveat-box {
    color: #fde68a;
    background: rgba(245, 158, 11, 0.10);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 12px;
    padding: 12px 16px;
    margin: 14px 0;
    font-size: 0.88rem;
    line-height: 1.55;
}
.future-box {
    color: #cbd5e1;
    background: rgba(56, 189, 248, 0.08);
    border: 1px dashed rgba(56, 189, 248, 0.42);
    border-radius: 12px;
    padding: 12px 16px;
    margin: 14px 0;
    font-size: 0.88rem;
    line-height: 1.55;
}
.future-box b { color: #7dd3fc; }
.method-block { color: #cbd5e1; font-size: 0.9rem; line-height: 1.6; }
.method-block h4 { color: #f1f5f9; margin: 16px 0 6px 0; font-size: 1.02rem; }
.method-block ul { padding-left: 20px; }
.method-block code { color: var(--accent); background: #0a1828; padding: 1px 6px; border-radius: 6px; }
.ml-summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}
.ml-summary-card {
    background: #0b1a2a;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
}
.ml-summary-label {
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 800;
}
.ml-summary-value {
    color: #f8fafc;
    font-size: 1.05rem;
    font-weight: 800;
    margin-top: 6px;
}
.ml-summary-note {
    color: var(--muted);
    font-size: 0.8rem;
    line-height: 1.5;
    margin-top: 6px;
}
.shiny-input-container { margin-bottom: 12px; color: #cbd5e1; }
.form-select, .form-control {
    background-color: #132437 !important;
    border: 1px solid #36506d !important;
    color: #f8fafc !important;
    border-radius: 10px !important;
}
.method-card summary::before { content: "> "; color: var(--accent); }
.method-card details[open] summary::before { content: "v "; }
.irs--shiny .irs-line {
    background: #40536b !important;
    border: 1px solid #57718f !important;
    box-shadow: inset 0 1px 2px rgba(7, 17, 31, 0.45);
}
.irs--shiny .irs-bar, .irs--shiny .irs-single { background: #14b8a6 !important; border-color: #14b8a6 !important; }
.irs--shiny .irs-bar-edge {
    background: #14b8a6 !important;
    border-color: #14b8a6 !important;
}
.irs--shiny .irs-handle {
    border-color: #14b8a6 !important;
    background: #d9fbf6 !important;
    box-shadow: 0 0 0 1px rgba(20, 184, 166, 0.28);
}
.irs--shiny .irs-min, .irs--shiny .irs-max, .irs--shiny .irs-grid-text { color: #9fb0c7 !important; }
@media (max-width: 1100px) {
    .kpi-grid, .duo-grid, .forecast-control-grid, .ml-summary-grid { grid-template-columns: 1fr; }
}
"""


# ==========================================================
# Small UI builders
# ==========================================================

def chart_card(title, subtitle, widget_id, height):
    return ui.div(
        ui.div(title, class_="card-title"),
        ui.div(subtitle, class_="card-subtitle"),
        output_widget(widget_id, height=f"{height}px"),
        class_="chart-card",
    )


# ==========================================================
# UI
# ==========================================================

default_year = str(max([y for y in years if y <= 2020] or years))

sidebar = ui.sidebar(
    ui.div("Filters", class_="sidebar-section-title"),
    ui.div("All tabs respond to these controls.", class_="sidebar-hint"),
    ui.input_select("year", "Year", choices=[str(y) for y in years], selected=default_year),
    ui.input_slider("month", "Month", 1, 12, 9),
    ui.input_select(
        "province", "Province",
        choices=["All Provinces"] + provinces, selected="All Provinces",
    ),
    ui.div(
        "Tip: click province bars or the rainfall-vs-water scatter to update this filter.",
        class_="sidebar-hint",
    ),
    ui.div(
        ui.input_action_button("reset_province_filter", "Reset to All Provinces"),
        class_="filter-action-row",
    ),
    ui.input_select(
        "topk", "Top-N provinces",
        choices={"5": "Top 5", "10": "Top 10", "13": "All 13"}, selected="10",
    ),
    ui.div("Focus metric", class_="sidebar-section-title"),
    ui.div("Drives the map, rankings and comparisons.", class_="sidebar-hint"),
    ui.input_select("metric", "Metric", choices=metric_options, selected="rainfall_mm"),
    width=300,
    open="open",
)


app_ui = ui.page_sidebar(
    sidebar,
    ui.head_content(
        ui.tags.style(custom_css),
        ui.tags.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap",
            rel="stylesheet",
        ),
    ),
    # ---- Header --------------------------------------------------
    ui.div(
        ui.h1("Mekong FloodLens"),
        ui.div(
            "A data-storytelling view of the Vietnamese Mekong Delta: monthly "
            "rainfall, dry/wet anomalies, and observed surface-water extent across "
            "13 provinces. This is an exploratory, observational dashboard - not an "
            "official flood-prediction system.",
            class_="subtitle",
        ),
        class_="app-header",

    ),
    # ---- Tabs ----------------------------------------------------
    ui.navset_card_tab(
        # ============================================================
        # TAB 1 - MEKONG SUMMARY
        # ============================================================
        ui.nav_panel(
            "Mekong Summary",
            ui.div(
                ui.HTML(
                    "<b>What is happening across the Mekong provinces?</b> "
                    "This dashboard tracks three observed signals from public satellite "
                    "and gauge-derived data - <b>how much it rained</b>, "
                    "<b>how dry or wet that is versus normal</b>, and "
                    "<b>how much surface water</b> was mapped. Use the sidebar to pick a "
                    "period and province. The KPIs and map below show the selected month, "
                    "the annual charts summarize the full year-by-year history, and the rainfall pattern charts show the long-run monsoon cycle and province gradient. Then walk the tabs left to right: "
                    "Rainfall &amp; Dryness -> Surface Water -> Province Comparison."
                ),
                class_="lead-note",
            ),
            ui.div(
                ui.div(ui.div("Avg rainfall", class_="kpi-label"), ui.output_ui("kpi_rain"),
                       ui.div("Selected period", class_="kpi-note"), class_="kpi"),
                ui.div(ui.div("Surface water", class_="kpi-label"), ui.output_ui("kpi_water"),
                       ui.div("Satellite proxy", class_="kpi-note"), class_="kpi cyan"),
                ui.div(ui.div("Wettest province", class_="kpi-label"), ui.output_ui("kpi_wettest"),
                       ui.div("Most rainfall this month", class_="kpi-note"), class_="kpi green"),
                ui.div(ui.div("Driest (proxy)", class_="kpi-label"), ui.output_ui("kpi_driest"),
                       ui.div("Highest dryness index", class_="kpi-note"), class_="kpi amber"),
                class_="kpi-grid",
            ),
            ui.div(
                ui.div(
                    ui.div("Delta map - focus metric", class_="card-title"),
                    ui.div("Color shows the sidebar focus metric for each province in the selected month.",
                           class_="card-subtitle"),
                    output_widget("map_plot", height="520px", width="100%"),
                    class_="chart-card",
                ),
                ui.div(
                    ui.div("Key observations", class_="card-title"),
                    ui.div("Plain-English read of the current selection.", class_="card-subtitle"),
                    ui.output_ui("summary_observations"),
                    class_="story-card",
                ),
                class_="duo-grid",
            ),
            ui.div(
                chart_card(
                    "Annual Rainfall Pattern",
                    "Full calendar years across the dataset for the selected province or delta mean. Selected year highlighted; Month filter does not apply.",
                    "annual_rainfall_plot", 340,
                ),
                chart_card(
                    "Annual Dryness Context",
                    "Annual mean rainfall-deficit proxy and dry-day share across full calendar years. Selected year highlighted; Month filter does not apply.",
                    "annual_dryness_plot", 340,
                ),
                class_="duo-grid",
            ),
            ui.div(
                chart_card(
                    "Delta Seasonal Rainfall Cycle",
                    "Full-history delta climatology across all years and provinces. This chart shows the monsoon cycle; Year and Month filters do not apply.",
                    "delta_seasonality_overview_plot", 340,
                ),
                class_="duo-grid",
            ),
            ui.div(
                ui.div(
                    ui.div("Long-Run Province Rainfall Pattern", class_="card-title"),
                    ui.div(
                        "True 3D rainfall columns show the long-run mean monthly rainfall gradient across provinces. Province filter highlights only; Year and Month filters do not apply.",
                        class_="card-subtitle",
                    ),
                    ui.output_ui("province_rainfall_climatology_plot"),
                    class_="chart-card",
                ),
            ),
            ui.div(
                ui.HTML(
                    "<b>Scope &amp; data.</b> Monthly panel of 13 Mekong Delta provinces, "
                    f"{min(years)}-{max(years)}. Rainfall is CHIRPS-derived (monthly totals plus "
                    "daily-derived indicators such as dry-day share and dry spells). Surface water "
                    "is JRC/satellite water-extent, available "
                    f"{min(WATER_YEARS)}-{max(WATER_YEARS)}. See the "
                    "<b>Methodology / Caveats</b> tab for sources and limitations."
                ),
                class_="lead-note",
            ),
        ),
        # ============================================================
        # TAB 2 - RAINFALL & DRYNESS
        # ============================================================
        ui.nav_panel(
            "Rainfall & Dryness",
            ui.div(
                ui.HTML(
                    "<b>Which provinces show unusual rainfall or dry conditions?</b> "
                    "A positive rainfall anomaly means <b>wetter than the long-run normal</b>; "
                    "a negative one means <b>drier</b>. The <b>dryness index</b> is a normalized "
                    "rainfall-deficit proxy derived only from the dry-side rainfall anomaly signal - "
                    "higher means stronger relative deficit. It is a proxy, not an official drought class."
                ),
                class_="lead-note",
            ),
            ui.div(
                chart_card(
                    "Rainfall anomaly by province",
                    "Top-N provinces by deviation from the long-run monthly normal. Cool tones = wetter, warm tones = drier. Click a bar to focus a province.",
                    "anomaly_rank_plot", 360,
                ),
                chart_card(
                    "Dryness index (proxy) by province",
                    "Top-N provinces by the dryness proxy for the selected month. Higher = drier.",
                    "dry_rank_plot", 360,
                ),
                class_="duo-grid",
            ),
            ui.div(
                chart_card(
                    "Seasonal rainfall pattern (observed climatology)",
                    "Average rainfall by calendar month across all years - the selected month is highlighted. "
                    "This is the historical cyclic pattern, NOT a forecast.",
                    "seasonality_plot", 340,
                ),
                chart_card(
                    "Rainfall this year vs long-run normal",
                    "Selected-year rainfall (solid) against the historical monthly mean (dashed). "
                    "Gaps below the dashed line are dry months.",
                    "rain_trend_plot", 340,
                ),
                class_="duo-grid",
            ),
            chart_card(
                "Rainfall anomaly heatmap",
                "Month x province rainfall z-scores for the selected year. Cool tones = wetter than normal, warm tones = drier.",
                "anomaly_heatmap", 360,
            ),
        ),
        # ============================================================
        # TAB 3 - SURFACE WATER
        # ============================================================
        ui.nav_panel(
            "Surface Water",
            ui.div(
                ui.HTML(
                    "<b>How does rainfall relate to observed surface water?</b> "
                    "Surface-water extent is a satellite observation of how much land is "
                    "covered by water - a useful wet/flood proxy, but not a measure of flood "
                    "impact. Wet rainfall anomalies often (not always) line up with larger "
                    "water extent."
                ),
                class_="lead-note",
            ),
            ui.div(
                chart_card(
                    "Surface-water extent over time",
                    "Monthly surface water for the selected province (or delta total). "
                    "The selected month is marked.",
                    "water_trend_plot", 340,
                ),
                chart_card(
                    "Rainfall anomaly vs surface water",
                    "Each dot is a province this month. Right = wetter than normal; up = more water. "
                    "Upper-right is the strongest wet signal. Click a point to follow that province across tabs.",
                    "scatter_plot", 340,
                ),
                class_="duo-grid",
            ),
            chart_card(
                "Surface-water distribution across provinces (box & whisker)",
                "Spread of monthly surface-water values per province in the selected year. The box is the "
                "middle 50%, the line is the median, points are individual months. Selected province highlighted.",
                "water_box_plot", 400,
            ),
        ),
        # ============================================================
        # TAB 4 - PROVINCE COMPARISON
        # ============================================================
        ui.nav_panel(
            "Province Comparison",
            ui.div(
                ui.HTML(
                    "<b>Which provinces are consistently high or low?</b> "
                    "These views rank and compare provinces on the sidebar <b>focus metric</b> "
                    "for the selected period, and trace one province over time."
                ),
                class_="lead-note",
            ),
            ui.div(
                chart_card(
                    "Top-N province ranking - focus metric",
                    "Provinces ranked by the selected focus metric this month. Selected province highlighted.",
                    "ranking_plot", 380,
                ),
                chart_card(
                    "This month vs each province's own history",
                    "Selected-month value (filled) against that province's historical average for the month (open).",
                    "comparison_plot", 380,
                ),
                class_="duo-grid",
            ),
            chart_card(
                "Selected province timeline - rainfall & surface water",
                "Full monthly history for the selected province. Pick a single province in the sidebar to populate this.",
                "province_timeline_plot", 360,
            ),
        ),
        # ============================================================
        # TAB 5 - ML PREDICTION
        # ============================================================
        ui.nav_panel(
            "ML Prediction",
            ui.div(
                ui.HTML(
                    "<b>Rainfall forecast preview.</b> This tab links observed daily rainfall "
                    "history with recursive XGBoost forecast outputs. Use it as an exploratory "
                    "model preview only; it is not an official flood warning, impact forecast, "
                    "or rainfall advisory."
                ),
                class_="lead-note",
            ),
            ui.div(
                ui.output_ui("forecast_model_summary"),
                ui.div(
                    ui.div("How to read this ML view", class_="card-title"),
                    ui.div(
                        "The forecast model uses recent daily rainfall history only. It helps compare the observed record with the next predicted daily pattern, not to issue warnings.",
                        class_="card-subtitle",
                    ),
                    ui.output_ui("forecast_model_note"),
                    class_="story-card",
                ),
                class_="duo-grid",
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
            ui.div(
                ui.div("Daily rainfall history and XGBoost forecast", class_="card-title"),
                ui.div(
                    "Solid line shows observed daily rainfall; dashed line shows recursive forecast values.",
                    class_="card-subtitle",
                ),
                output_widget("rainfall_forecast_plot", height="420px"),
                ui.output_ui("forecast_window_note"),
                class_="chart-card",
            ),
        ),
        # ============================================================
        # TAB 6 - METHODOLOGY / CAVEATS
        # ============================================================
        ui.nav_panel(
            "Methodology / Caveats",
            ui.div(
                ui.HTML(
                    """
                    <div class="method-block">
                      <h4>What this dashboard is</h4>
                      <p>An <b>observational, exploratory</b> view of rainfall, dry/wet anomalies,
                      and surface-water extent across 13 Mekong Delta provinces. It helps you spot
                      where conditions are unusual and how provinces differ - nothing more.</p>

                      <h4>Data sources</h4>
                      <ul>
                        <li><b>Rainfall</b> - CHIRPS precipitation aggregated to province-month, with
                        daily-derived features (max 1-day rainfall, rainy/dry day counts, heavy-rain
                        days, longest dry/wet spells, dry-day share).</li>
                        <li><b>Rainfall anomaly &amp; z-score</b> - deviation of monthly rainfall from
                        each province's long-run mean for that calendar month.</li>
                        <li><b>Surface water</b> - satellite-mapped water extent (km^2 and % of province
                        area), available 1984-2021.</li>
                        <li><b>Boundaries</b> - province polygons from the admin-1 GeoJSON.</li>
                      </ul>

                      <h4>Processed / derived features</h4>
                      <ul>
                        <li><code>rainfall_anomaly</code> = monthly rainfall - long-run monthly mean.</li>
                        <li><code>rainfall_zscore</code> = standardized anomaly per province &amp; month.</li>
                        <li><code>dry_index</code> (proxy) = <code>minmax(max(-rainfall_zscore, 0))</code>,
                        where <code>max(-rainfall_zscore, 0)</code> keeps only the dry-side anomaly signal and
                        <code>minmax()</code> rescales that deficit term to 0-1 <i>relative to the whole panel</i>.
                        Higher = drier.</li>
                      </ul>
                    </div>
                    """
                ),
                ui.div(
                    ui.HTML(
                        "<b>Caveats.</b> Surface water is a satellite <b>proxy</b> for wet conditions - "
                        "it is <b>not</b> official flood-impact or flood-probability data. The dryness "
                        "index is a <b>relative proxy</b> across the panel, not an official drought "
                        "classification. Do not read any value here as an official flood or drought "
                        "warning."
                    ),
                    class_="caveat-box",
                ),
                ui.div(
                    ui.HTML(
                        "<b>Modeling preview.</b> The <b>ML Prediction</b> tab shows recursive "
                        "XGBoost rainfall forecast outputs alongside observed daily rainfall history. "
                        "Treat this as exploratory model output, not an official flood warning, "
                        "impact forecast, or rainfall advisory. The seasonal chart remains "
                        "<b>observed historical climatology only</b> - it is not a forecast."
                    ),
                    class_="future-box",
                ),
                class_="story-card",
            ),
        ),
        id="main_tabs",
    ),
    title="Mekong FloodLens",
    fillable=False,
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


def annual_rainfall_frame(selected_province):
    annual = (
        df.groupby(["province_name", "year"], as_index=False)
        .agg(annual_rainfall_mm=("rainfall_mm", "sum"))
    )
    if selected_province == "All Provinces":
        annual = (
            annual.groupby("year", as_index=False)
            .agg(annual_rainfall_mm=("annual_rainfall_mm", "mean"))
        )
    else:
        annual = annual[annual["province_name"] == selected_province][["year", "annual_rainfall_mm"]].copy()
    return annual.sort_values("year").reset_index(drop=True)


def annual_dryness_frame(selected_province):
    annual = (
        df.groupby(["province_name", "year"], as_index=False)
        .agg(
            annual_dry_index=("dry_index", "mean"),
            annual_dry_day_ratio=("dry_day_ratio", "mean"),
        )
    )
    if selected_province == "All Provinces":
        annual = (
            annual.groupby("year", as_index=False)
            .agg(
                annual_dry_index=("annual_dry_index", "mean"),
                annual_dry_day_ratio=("annual_dry_day_ratio", "mean"),
            )
        )
    else:
        annual = annual[annual["province_name"] == selected_province][
            ["year", "annual_dry_index", "annual_dry_day_ratio"]
        ].copy()
    return annual.sort_values("year").reset_index(drop=True)


def delta_monthly_climatology_frame():
    clim = (
        df.groupby("month", as_index=False)
        .agg(mean_rainfall_mm=("rainfall_mm", "mean"))
        .sort_values("month")
        .reset_index(drop=True)
    )
    clim["month_label"] = [MONTH_NAMES[int(m) - 1][:3] for m in clim["month"]]
    return clim


def province_rainfall_climatology_frame():
    return (
        df.groupby("province_name", as_index=False)
        .agg(mean_rainfall_mm=("rainfall_mm", "mean"))
        .sort_values("mean_rainfall_mm", ascending=False)
        .reset_index(drop=True)
    )


def province_rainfall_3d_frame(selected_province):
    frame = province_rainfall_climatology_frame().merge(map_label_df, on="province_name", how="left")
    frame["rank"] = frame["mean_rainfall_mm"].rank(method="first", ascending=False).astype(int)
    frame = frame.dropna(subset=["lon", "lat"]).reset_index(drop=True)
    frame["elevation_m"] = scaled_sizes(frame["mean_rainfall_mm"], lo=6000, hi=26000).round(0)
    frame["radius_m"] = np.where(
        (selected_province != "All Provinces") & (frame["province_name"] == selected_province),
        13000,
        11000,
    )
    frame["fill_color"] = [
        [245, 158, 11, 235] if (selected_province != "All Provinces" and n == selected_province)
        else [20, 184, 166, 230]
        for n in frame["province_name"]
    ]
    frame["line_color"] = [
        [255, 247, 237, 255] if (selected_province != "All Provinces" and n == selected_province)
        else [56, 189, 248, 210]
        for n in frame["province_name"]
    ]
    frame["label_altitude_m"] = frame["elevation_m"] + 1800
    return frame


def top_k(input):
    try:
        return int(input.topk())
    except (TypeError, ValueError):
        return 10


def latest_available_year(column, availability_column, selected_year):
    valid_years = sorted(
        df.loc[df[availability_column] & (df[column] > 0), "year"].dropna().unique().tolist()
    )
    valid_years = [int(y) for y in valid_years if int(y) <= selected_year]
    return max(valid_years) if valid_years else None


def ranking_frame(input, metric, *, ascending_for_top=False):
    """Return the top-N provinces for `metric` in the selected month, ready to plot."""
    d = current_all_provinces_df(input)[["province_name", metric, "has_water"]].copy()
    if metric in WATER_METRICS:
        d = d[d["has_water"]]
    d = d.dropna(subset=[metric])
    if d.empty:
        return d
    k = top_k(input)
    # Top-N by magnitude of interest, then sort ascending for a clean horizontal bar.
    d = d.sort_values(metric, ascending=ascending_for_top).head(k)
    return d.sort_values(metric, ascending=True)


def highlight_colors(names, selected_p, base, hi=None):
    hi = hi or PALETTE["amber"]
    return [
        hi if (selected_p != "All Provinces" and n == selected_p) else base
        for n in names
    ]


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
    chart_selected_province = reactive.value(None)

    def queue_chart_selected_province(selected_name):
        if selected_name and selected_name in provinces:
            chart_selected_province.set(str(selected_name))

    @reactive.calc
    def current_month_all():
        return current_all_provinces_df(input)

    @reactive.calc
    def current_month_filtered():
        return current_filter_df(input)

    @reactive.calc
    def current_daily_history():
        return selected_daily_history_df(input)

    @reactive.calc
    def current_daily_forecast():
        return selected_daily_forecast_df(input)

    @reactive.effect
    def _log_filters():
        logger.info(
            f"Filters -> Province={input.province()}, Year={input.year()}, "
            f"Month={input.month()}, Metric={input.metric()}, TopK={input.topk()}"
        )

    @reactive.effect
    def _sync_chart_selected_province():
        selected = chart_selected_province()
        if not selected:
            return
        if selected in provinces and selected != input.province():
            ui.update_select("province", selected=selected, session=session)
        chart_selected_province.set(None)

    @reactive.effect
    @reactive.event(input.reset_province_filter)
    def _reset_province_filter():
        chart_selected_province.set(None)
        ui.update_select("province", selected="All Provinces", session=session)

    # ---------------- TAB 1: KPIs ----------------
    @output(suspend_when_hidden=False)
    @render.ui
    def kpi_rain():
        d = current_month_filtered()
        if d.empty:
            return ui.div("N/A", class_="kpi-value")
        return ui.div(f"{d['rainfall_mm'].mean():,.0f} mm", class_="kpi-value")

    @output(suspend_when_hidden=False)
    @render.ui
    def kpi_water():
        d = current_month_filtered()
        d = d[d["has_water"]]
        if d.empty:
            return ui.div("No coverage", class_="kpi-value")
        return ui.div(f"{d['water_area_km2'].sum():,.0f} km^2", class_="kpi-value")

    @output(suspend_when_hidden=False)
    @render.ui
    def kpi_wettest():
        d = current_month_all()
        if d.empty:
            return ui.div("N/A", class_="kpi-value")
        row = d.sort_values("rainfall_mm", ascending=False).iloc[0]
        return ui.div(str(row["province_name"]), class_="kpi-value")

    @output(suspend_when_hidden=False)
    @render.ui
    def kpi_driest():
        d = current_month_all()
        if d.empty:
            return ui.div("N/A", class_="kpi-value")
        row = d.sort_values("dry_index", ascending=False).iloc[0]
        return ui.div(str(row["province_name"]), class_="kpi-value")

    # ---------------- TAB 1: observations ----------------
    @output(suspend_when_hidden=False)
    @render.ui
    def summary_observations():
        bullets = summary_bullets(input.province(), int(input.year()), int(input.month()))
        return ui.HTML(
            "<ul class='obs-list'>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>"
        )

    # ---------------- TAB 1: map ----------------
    @output(suspend_when_hidden=False)
    @render_widget
    def map_plot():
        d = current_month_all()
        metric = input.metric()
        label = metric_labels.get(metric, metric)
        color_scale = metric_color_scales.get(metric, "Viridis")

        if metric in WATER_METRICS:
            d = d[d["has_water"]]
        if d.empty:
            return empty_fig(520, "No data for this metric / month")

        hover_data = {
            "rainfall_mm": ":,.1f",
            "rainfall_anomaly": ":+,.1f",
            "dry_index": ":.2f",
            "water_area_km2": ":,.1f",
            "province_name": False,
        }
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
            zoom=6.6,
            opacity=0.78,
        )
        fig.update_traces(
            marker_line_width=1.1,
            marker_line_color="rgba(248,250,252,0.55)",
            selector=dict(type="choroplethmapbox"),
        )
        if metric in {"rainfall_anomaly", "rainfall_zscore"}:
            fig.update_coloraxes(cmid=0)

        labels = map_label_df[map_label_df["province_name"].isin(d["province_name"])].copy()
        if not labels.empty:
            fig.add_trace(go.Scattermapbox(
                lon=labels["lon"], lat=labels["lat"], text=labels["province_name"],
                mode="text", textfont=dict(size=11, color="#e2e8f0"),
                hoverinfo="skip", showlegend=False,
            ))
        fig.update_layout(
            height=520, autosize=True,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"]),
            coloraxis_colorbar=dict(
                title=label, thickness=14, len=0.65, y=0.5, x=0.98,
                bgcolor="rgba(15,32,50,0.78)",
            ),
        )
        return fig

    @output(suspend_when_hidden=False)
    @render_widget
    def annual_rainfall_plot():
        selected_p = input.province()
        selected_year = int(input.year())
        annual = annual_rainfall_frame(selected_p)
        if annual.empty:
            return empty_fig(340, "No annual rainfall history for this selection")

        long_run_mean = annual["annual_rainfall_mm"].mean()
        selected_row = annual[annual["year"] == selected_year]
        series_name = "Delta mean annual rainfall" if selected_p == "All Provinces" else selected_p

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=annual["year"], y=annual["annual_rainfall_mm"],
            mode="lines+markers",
            name=series_name,
            line=dict(color=PALETTE["accent"], width=2.6),
            marker=dict(size=6, color=PALETTE["accent"]),
            hovertemplate="Year: %{x}<br>Annual rainfall: %{y:,.0f} mm<extra></extra>",
        ))
        fig.add_hline(
            y=long_run_mean,
            line_dash="dash",
            line_color=PALETTE["cyan"],
            annotation_text="Long-run mean",
            annotation_position="top left",
        )
        if not selected_row.empty:
            fig.add_trace(go.Scatter(
                x=selected_row["year"], y=selected_row["annual_rainfall_mm"],
                mode="markers",
                name="Selected year",
                marker=dict(size=11, color=PALETTE["amber"], line=dict(color="#f8fafc", width=1)),
                hovertemplate="Selected year %{x}<br>Annual rainfall: %{y:,.0f} mm<extra></extra>",
                showlegend=False,
            ))
        fig.add_vline(x=selected_year, line_dash="dot", line_color=PALETTE["amber"])
        apply_dark_layout(fig, 340, legend=True)
        fig.update_xaxes(title="Year", dtick=max(1, len(annual) // 10))
        fig.update_yaxes(title="Annual rainfall (mm)")
        return fig

    @output(suspend_when_hidden=False)
    @render_widget
    def annual_dryness_plot():
        selected_p = input.province()
        selected_year = int(input.year())
        annual = annual_dryness_frame(selected_p)
        if annual.empty:
            return empty_fig(340, "No annual dryness history for this selection")

        selected_row = annual[annual["year"] == selected_year]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=annual["year"], y=annual["annual_dry_index"],
            mode="lines+markers",
            name="Dryness index",
            line=dict(color=PALETTE["accent"], width=2.4),
            marker=dict(size=6, color=PALETTE["accent"]),
            hovertemplate="Year: %{x}<br>Dryness index: %{y:.2f}<extra></extra>",
            yaxis="y1",
        ))
        fig.add_trace(go.Scatter(
            x=annual["year"], y=annual["annual_dry_day_ratio"],
            mode="lines+markers",
            name="Dry-day share",
            line=dict(color=PALETTE["cyan"], width=2.2),
            marker=dict(size=6, color=PALETTE["cyan"]),
            hovertemplate="Year: %{x}<br>Dry-day share: %{y:.0%}<extra></extra>",
            yaxis="y2",
        ))
        if not selected_row.empty:
            fig.add_trace(go.Scatter(
                x=selected_row["year"], y=selected_row["annual_dry_index"],
                mode="markers",
                name="Selected year (index)",
                marker=dict(size=11, color=PALETTE["amber"], line=dict(color="#f8fafc", width=1)),
                hovertemplate="Selected year %{x}<br>Dryness index: %{y:.2f}<extra></extra>",
                yaxis="y1",
                showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=selected_row["year"], y=selected_row["annual_dry_day_ratio"],
                mode="markers",
                name="Selected year (share)",
                marker=dict(size=9, color="#f8fafc", line=dict(color=PALETTE["cyan"], width=2)),
                hovertemplate="Selected year %{x}<br>Dry-day share: %{y:.0%}<extra></extra>",
                yaxis="y2",
                showlegend=False,
            ))
        fig.add_vline(x=selected_year, line_dash="dot", line_color=PALETTE["amber"])
        apply_dark_layout(fig, 340, legend=True)
        fig.update_layout(
            yaxis=dict(
                title="Dryness index",
                showgrid=True,
                gridcolor=PALETTE["grid"],
                zeroline=False,
                range=[0, 1.05],
            ),
            yaxis2=dict(
                title="Dry-day share",
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=False,
                tickformat=".0%",
                range=[0, 1.05],
            ),
        )
        fig.update_xaxes(title="Year", dtick=max(1, len(annual) // 10))
        return fig

    @output(suspend_when_hidden=False)
    @render_widget
    def delta_seasonality_overview_plot():
        clim = delta_monthly_climatology_frame()
        if clim.empty:
            return empty_fig(340, "No long-run rainfall climatology available")

        wettest_months = set(clim.nlargest(2, "mean_rainfall_mm")["month"].tolist())
        driest_months = set(clim.nsmallest(2, "mean_rainfall_mm")["month"].tolist())
        bar_colors = []
        for month in clim["month"]:
            if month in wettest_months:
                bar_colors.append(PALETTE["cyan"])
            elif month in driest_months:
                bar_colors.append(PALETTE["rust"])
            else:
                bar_colors.append(PALETTE["accent"])

        fig = go.Figure(go.Bar(
            x=clim["month_label"],
            y=clim["mean_rainfall_mm"],
            marker_color=bar_colors,
            text=[f"{v:,.0f}" for v in clim["mean_rainfall_mm"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="Month: %{x}<br>Mean rainfall: %{y:,.1f} mm<extra></extra>",
        ))
        apply_dark_layout(fig, 340)
        fig.update_yaxes(title="Long-run mean rainfall (mm)")
        fig.update_xaxes(title="", showgrid=False)
        max_row = clim.loc[clim["mean_rainfall_mm"].idxmax()]
        min_row = clim.loc[clim["mean_rainfall_mm"].idxmin()]
        fig.add_annotation(
            x=max_row["month_label"],
            y=max_row["mean_rainfall_mm"],
            text="Wettest",
            yshift=28,
            showarrow=False,
            font=dict(color=PALETTE["cyan"], size=11),
        )
        fig.add_annotation(
            x=min_row["month_label"],
            y=min_row["mean_rainfall_mm"],
            text="Driest",
            yshift=24,
            showarrow=False,
            font=dict(color=PALETTE["rust"], size=11),
        )
        return fig

    @output(suspend_when_hidden=False)
    @render.ui
    def province_rainfall_climatology_plot():
        selected_p = input.province()
        clim = province_rainfall_3d_frame(selected_p)
        if clim.empty:
            return ui.div(
                "No long-run province rainfall averages available.",
                class_="card-subtitle",
            )

        label_df = clim.head(3).copy()
        if selected_p != "All Provinces":
            selected_label = clim[clim["province_name"] == selected_p]
            if not selected_label.empty and selected_label["province_name"].iloc[0] not in label_df["province_name"].tolist():
                label_df = pd.concat([label_df, selected_label], ignore_index=True)
                label_df = label_df.drop_duplicates(subset=["province_name"])

        geo_layer = pdk.Layer(
            "GeoJsonLayer",
            data=geojson_data,
            stroked=True,
            filled=True,
            extruded=False,
            get_fill_color=[15, 32, 50, 58],
            get_line_color=[41, 64, 92, 190],
            line_width_min_pixels=1,
            pickable=False,
            auto_highlight=False,
        )
        column_layer = pdk.Layer(
            "ColumnLayer",
            data=clim.to_dict("records"),
            get_position=["lon", "lat"],
            get_elevation="elevation_m",
            elevation_scale=1,
            radius="radius_m",
            get_fill_color="fill_color",
            get_line_color="line_color",
            line_width_min_pixels=1,
            extruded=True,
            stroked=True,
            pickable=True,
            auto_highlight=False,
            disk_resolution=4,
            coverage=0.9,
        )
        text_layer = pdk.Layer(
            "TextLayer",
            data=label_df.to_dict("records"),
            get_position=["lon", "lat"],
            get_text="province_name",
            get_color=[226, 232, 240, 235],
            get_size=14,
            size_units="meters",
            size_scale=120,
            get_alignment_baseline="bottom",
            get_pixel_offset=[0, -14],
            pickable=False,
        )
        glow_layer = None
        if selected_p != "All Provinces":
            selected_marker = clim[clim["province_name"] == selected_p]
            if not selected_marker.empty:
                glow_layer = pdk.Layer(
                    "ColumnLayer",
                    data=selected_marker.to_dict("records"),
                    get_position=["lon", "lat"],
                    get_elevation="elevation_m",
                    elevation_scale=1.05,
                    get_fill_color=[[253, 230, 138, 68]],
                    radius=15500,
                    extruded=True,
                    stroked=False,
                    pickable=False,
                    disk_resolution=20,
                    coverage=1.0,
                )

        layers = [geo_layer]
        if glow_layer is not None:
            layers.append(glow_layer)
        layers.extend([column_layer, text_layer])

        original_has_jupyter_extra = pdk.bindings.deck.has_jupyter_extra
        pdk.bindings.deck.has_jupyter_extra = lambda: False
        try:
            deck = pdk.Deck(
                layers=layers,
                initial_view_state=pdk.ViewState(
                    latitude=9.95,
                    longitude=105.65,
                    zoom=6.55,
                    pitch=54,
                    bearing=-15,
                ),
                tooltip={
                    "html": (
                        "<b>{province_name}</b><br/>"
                        "Long-run mean monthly rainfall: {mean_rainfall_mm} mm<br/>"
                        "Rank: {rank}"
                    ),
                    "style": {
                        "backgroundColor": "rgba(8, 19, 31, 0.94)",
                        "color": "#e2e8f0",
                        "border": "1px solid rgba(41, 64, 92, 0.95)",
                        "borderRadius": "8px",
                        "fontSize": "12px",
                    },
                },
                map_provider="carto",
                map_style=pdk.map_styles.CARTO_DARK_NO_LABELS,
                width="100%",
                height=520,
                parameters={
                    "clearColor": [8, 19, 31, 0],
                },
                description="True 3D rainfall columns by province.",
            )
        finally:
            pdk.bindings.deck.has_jupyter_extra = original_has_jupyter_extra
        deck_html = deck.to_html(
            as_string=True,
            iframe_width="100%",
            iframe_height=520,
            notebook_display=False,
            offline=True,
        )
        return ui.tags.iframe(
            srcdoc=deck_html,
            style="width: 100%; height: 520px; border: 0; border-radius: 12px; background: transparent;",
            loading="lazy",
        )

    # ---------------- TAB 2: anomaly ranking ----------------
    @output
    @render_widget
    def anomaly_rank_plot():
        d = current_month_all()[["province_name", "rainfall_anomaly"]].dropna()
        if d.empty:
            return empty_fig(360)
        k = top_k(input)
        # Show the most extreme anomalies (either direction).
        d = d.reindex(d["rainfall_anomaly"].abs().sort_values(ascending=False).index).head(k)
        d = d.sort_values("rainfall_anomaly", ascending=True)

        selected_p = input.province()
        colors = []
        for n, v in zip(d["province_name"], d["rainfall_anomaly"]):
            if selected_p != "All Provinces" and n == selected_p:
                colors.append(PALETTE["amber"])
            else:
                colors.append(PALETTE["cyan"] if v >= 0 else PALETTE["rust"])

        fig = go.FigureWidget(go.Bar(
            x=d["rainfall_anomaly"], y=d["province_name"], orientation="h",
            marker_color=colors,
            text=[f"{v:+,.0f}" for v in d["rainfall_anomaly"]],
            textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Anomaly: %{x:+,.1f} mm<extra></extra>",
        ))
        def _handle_anomaly_click(trace, points, state):
            if points.point_inds:
                queue_chart_selected_province(trace.y[points.point_inds[0]])

        fig.data[0].on_click(_handle_anomaly_click)
        fig.add_vline(x=0, line_dash="dot", line_color=PALETTE["muted"])
        apply_dark_layout(fig, 360)
        fig.update_layout(margin=dict(l=5, r=45, t=5, b=38))
        fig.update_xaxes(title="Rainfall anomaly (mm) - cool wetter, warm drier")
        fig.update_yaxes(showgrid=False)
        return fig

    @output
    @render_widget
    def dry_rank_plot():
        d = ranking_frame(input, "dry_index", ascending_for_top=False)
        if d.empty:
            return empty_fig(360)
        colors = highlight_colors(d["province_name"], input.province(), PALETTE["rust"], PALETTE["amber"])
        fig = go.FigureWidget(go.Bar(
            x=d["dry_index"], y=d["province_name"], orientation="h",
            marker_color=colors,
            text=[f"{v:.2f}" for v in d["dry_index"]],
            textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Dryness index: %{x:.2f}<extra></extra>",
        ))
        def _handle_dryness_click(trace, points, state):
            if points.point_inds:
                queue_chart_selected_province(trace.y[points.point_inds[0]])

        fig.data[0].on_click(_handle_dryness_click)
        apply_dark_layout(fig, 360)
        fig.update_layout(margin=dict(l=5, r=45, t=5, b=38))
        fig.update_xaxes(title="Dryness index (proxy, 0-1) - higher = drier", range=[0, 1.05])
        fig.update_yaxes(showgrid=False)
        return fig

    # ---------------- TAB 2: seasonality ----------------
    @output
    @render_widget
    def seasonality_plot():
        p = input.province()
        base = df if p == "All Provinces" else df[df["province_name"] == p]
        clim = base.groupby("month", as_index=False)["rainfall_mm"].mean()
        clim = clim.set_index("month").reindex(range(1, 13)).fillna(0).reset_index()
        if clim["rainfall_mm"].sum() == 0:
            return empty_fig(340)

        selected_m = int(input.month())
        colors = [PALETTE["amber"] if m == selected_m else PALETTE["cyan"] for m in clim["month"]]
        fig = go.Figure(go.Bar(
            x=[MONTH_NAMES[m - 1][:3] for m in clim["month"]],
            y=clim["rainfall_mm"], marker_color=colors,
            hovertemplate="%{x}: %{y:,.0f} mm<extra></extra>",
        ))
        apply_dark_layout(fig, 340)
        fig.update_yaxes(title="Avg rainfall (mm)")
        fig.update_xaxes(title="", showgrid=False)
        return fig

    @output
    @render_widget
    def rain_trend_plot():
        y = int(input.year())
        p = input.province()
        selected_m = int(input.month())
        if p == "All Provinces":
            d = (
                df[df["year"] == y].groupby("month", as_index=False)
                .agg(rainfall_mm=("rainfall_mm", "mean"), monthly_mean=("monthly_mean", "mean"))
            )
        else:
            d = df[(df["year"] == y) & (df["province_name"] == p)].copy()
        d = d.set_index("month").reindex(range(1, 13)).reset_index()
        if d["rainfall_mm"].dropna().empty:
            return empty_fig(340)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=d["month"], y=d["rainfall_mm"], mode="lines+markers",
            name="Selected year", line=dict(color=PALETTE["accent"], width=3),
        ))
        fig.add_trace(go.Scatter(
            x=d["month"], y=d["monthly_mean"], mode="lines+markers",
            name="Long-run mean", line=dict(color=PALETTE["cyan"], width=2, dash="dash"),
        ))
        fig.add_vline(x=selected_m, line_dash="dot", line_color="#e2e8f0")
        apply_dark_layout(fig, 340, legend=True)
        fig.update_xaxes(title="Month", dtick=1)
        fig.update_yaxes(title="Rainfall (mm)")
        return fig

    @output
    @render_widget
    def anomaly_heatmap():
        y = int(input.year())
        d = df[df["year"] == y].copy()
        if d.empty:
            return empty_fig(360)
        pivot = d.pivot_table(
            index="province_name", columns="month",
            values="rainfall_zscore", aggfunc="mean",
        ).reindex(provinces)
        if pivot.dropna(how="all").empty:
            return empty_fig(360)

        fig = px.imshow(
            pivot, labels=dict(x="Month", y="", color="Z-score"),
            color_continuous_scale=ANOMALY_COLORSCALE, zmin=-2, zmax=2, aspect="auto",
        )
        fig.update_layout(
            margin=dict(l=85, r=5, t=10, b=35), height=360,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"], size=10),
            coloraxis_colorbar=dict(title="Z-score", thickness=10, len=0.75),
            xaxis=dict(dtick=1),
        )
        return fig

    # ---------------- TAB 5: ML prediction ----------------
    @output
    @render.ui
    def forecast_model_summary():
        history = current_daily_history()
        forecast = current_daily_forecast()
        horizon_months = int(input.forecast_horizon_months())
        forecast_days = len(forecast.index) if not forecast.empty else 0
        history_span = "No selected history slice"
        if not history.empty:
            history_span = (
                f"{history['date'].min():%Y} to {history['date'].max():%Y}"
            )

        return ui.div(
            ui.div(
                ui.div("Model family", class_="ml-summary-label"),
                ui.div("Two-stage recursive XGBoost", class_="ml-summary-value"),
                ui.div(
                    "Classifier for rain occurrence plus regressor for rainfall amount.",
                    class_="ml-summary-note",
                ),
                class_="ml-summary-card",
            ),
            ui.div(
                ui.div("Features used", class_="ml-summary-label"),
                ui.div("Daily lags, rolling rain stats, wet/dry streaks, seasonality", class_="ml-summary-value"),
                ui.div(
                    "Long lags up to one year are available through the full daily history files.",
                    class_="ml-summary-note",
                ),
                class_="ml-summary-card",
            ),
            ui.div(
                ui.div("Selected display window", class_="ml-summary-label"),
                ui.div(history_span, class_="ml-summary-value"),
                ui.div(
                    "The control below changes the observed history shown in the chart, not the underlying model export.",
                    class_="ml-summary-note",
                ),
                class_="ml-summary-card",
            ),
            ui.div(
                ui.div("Forecast shown", class_="ml-summary-label"),
                ui.div(f"{horizon_months} month(s) / {forecast_days} daily rows", class_="ml-summary-value"),
                ui.div(
                    "Useful for regime and seasonality context. Do not read it as day-level event certainty.",
                    class_="ml-summary-note",
                ),
                class_="ml-summary-card",
            ),
            class_="ml-summary-grid",
        )

    @output
    @render.ui
    def forecast_model_note():
        return ui.HTML(
            "This preview is generated outside the dashboard from <b>raw daily CHIRPS rainfall</b> "
            "and loaded from <code>modeling/result/</code>. The notebook keeps the most recent "
            "<b>15 years</b> of valid feature rows for fitting, upweights rainy and heavy-rain days, "
            "and predicts forward recursively. It is useful for seeing likely wet/dry regime behavior, "
            "but the app does <b>not</b> currently expose held-out accuracy metrics or calibrated warning thresholds."
        )

    @output
    @render_widget
    def rainfall_forecast_plot():
        history = current_daily_history()
        forecast = current_daily_forecast()
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
        history = current_daily_history()
        forecast = current_daily_forecast()
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
                "Observed data comes from the raw daily rainfall file; future values come from the recursive XGBoost outputs in modeling/result. This preview is not an official warning or advisory."
            ),
            class_="forecast-note",
        )

    # ---------------- TAB 3: surface water ----------------
    @output
    @render_widget
    def water_trend_plot():
        p = input.province()
        wdf = df[df["has_water"]]
        if p == "All Provinces":
            t = wdf.groupby("date", as_index=False)["water_area_km2"].sum().sort_values("date")
            name = "Delta total"
        else:
            t = wdf[wdf["province_name"] == p].sort_values("date")
            name = p
        if t.empty or t["water_area_km2"].sum() == 0:
            return empty_fig(340, "No surface-water coverage for this selection")

        sel_date = pd.Timestamp(year=int(input.year()), month=int(input.month()), day=1)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=t["date"], y=t["water_area_km2"], mode="lines", name=name,
            line=dict(color=PALETTE["cyan"], width=2),
            fill="tozeroy", fillcolor="rgba(14,165,233,0.12)",
        ))
        sel = t[t["date"] == sel_date]
        if not sel.empty:
            fig.add_trace(go.Scatter(
                x=sel["date"], y=sel["water_area_km2"], mode="markers",
                name="Selected", marker=dict(color=PALETTE["amber"], size=12),
            ))
        apply_dark_layout(fig, 340)
        fig.update_yaxes(title="Surface water (km^2)")
        fig.update_xaxes(title="")
        return fig

    @output
    @render_widget
    def scatter_plot():
        d = current_month_all()
        d = d[d["has_water"]].copy()
        d = d[(d["water_area_km2"] > 0) | (d["rainfall_anomaly"] != 0)]
        if d.empty:
            return empty_fig(340, "No rainfall/water pairs for this month")

        selected_p = input.province()
        line_colors = [
            "#f8fafc" if (selected_p != "All Provinces" and n == selected_p) else "rgba(0,0,0,0)"
            for n in d["province_name"]
        ]
        fig = go.FigureWidget(go.Scatter(
            x=d["rainfall_anomaly"], y=d["water_area_km2"],
            mode="markers+text", text=d["province_name"],
            textposition="top center", textfont=dict(size=9, color=PALETTE["muted"]),
            marker=dict(
                size=14, color=d["rainfall_anomaly"], colorscale=ANOMALY_COLORSCALE,
                cmid=0, showscale=True, line=dict(width=2, color=line_colors),
                colorbar=dict(title="Anomaly", thickness=12, len=0.7),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>Rain anomaly: %{x:+,.0f} mm"
                "<br>Water: %{y:,.0f} km^2<extra></extra>"
            ),
        ))
        def _handle_scatter_click(trace, points, state):
            if points.point_inds:
                queue_chart_selected_province(trace.text[points.point_inds[0]])

        fig.data[0].on_click(_handle_scatter_click)
        fig.add_vline(x=0, line_dash="dot", line_color=PALETTE["muted"])
        apply_dark_layout(fig, 340)
        fig.update_xaxes(title="Rainfall anomaly (mm)")
        fig.update_yaxes(title="Surface water (km^2)")
        return fig

    @output
    @render_widget
    def water_box_plot():
        y = int(input.year())
        d = df[(df["year"] == y) & df["has_water"]].copy()
        d = d[d["water_area_km2"] > 0]
        if d.empty:
            return empty_fig(400, "No surface-water coverage for this year")

        # Order provinces by median so the chart reads top-to-bottom.
        order = (
            d.groupby("province_name")["water_area_km2"].median()
            .sort_values(ascending=True).index.tolist()
        )
        selected_p = input.province()

        fig = go.Figure()
        for prov in order:
            vals = d[d["province_name"] == prov]["water_area_km2"]
            is_sel = (selected_p != "All Provinces" and prov == selected_p)
            fig.add_trace(go.Box(
                x=vals, name=prov, orientation="h",
                boxpoints="all", jitter=0.4, pointpos=0,
                marker=dict(size=4, color=PALETTE["amber"] if is_sel else PALETTE["muted"]),
                line=dict(color=PALETTE["amber"] if is_sel else PALETTE["cyan"]),
                fillcolor="rgba(245,158,11,0.18)" if is_sel else "rgba(14,165,233,0.12)",
                hovertemplate=f"<b>{prov}</b><br>%{{x:,.0f}} km^2<extra></extra>",
            ))
        apply_dark_layout(fig, 400)
        fig.update_layout(margin=dict(l=90, r=20, t=10, b=38))
        fig.update_xaxes(title=f"Monthly surface water (km^2) - distribution across {y}")
        fig.update_yaxes(showgrid=False)
        return fig

    # ---------------- TAB 4: comparison ----------------
    @output
    @render_widget
    def ranking_plot():
        metric = input.metric()
        label = metric_labels.get(metric, metric)
        d = ranking_frame(input, metric, ascending_for_top=False)
        if d.empty:
            return empty_fig(380, "No data for this metric / month")

        colors = highlight_colors(d["province_name"], input.province(), PALETTE["accent"])
        fig = go.FigureWidget(go.Bar(
            x=d[metric],
            y=d["province_name"],
            orientation="h",
            text=d[metric],
            marker_color=colors,
            hovertemplate="<b>%{y}</b><br>" + label + f": %{{x{metric_plot_formats.get(metric, ':.2f')}}}<extra></extra>",
        ))
        fig.update_traces(
            texttemplate=metric_text_template(metric),
            textposition="outside", cliponaxis=False,
        )
        def _handle_ranking_click(trace, points, state):
            if points.point_inds:
                queue_chart_selected_province(trace.y[points.point_inds[0]])

        fig.data[0].on_click(_handle_ranking_click)
        apply_dark_layout(fig, 380)
        fig.update_layout(margin=dict(l=5, r=50, t=5, b=38))
        fig.update_xaxes(title=label)
        fig.update_yaxes(showgrid=False)
        return fig

    @output
    @render_widget
    def comparison_plot():
        y = int(input.year())
        m = int(input.month())
        metric = input.metric()
        label = metric_labels.get(metric, metric)

        selected = df[(df["year"] == y) & (df["month"] == m)][["province_name", metric, "has_water"]].copy()
        if metric in WATER_METRICS:
            selected = selected[selected["has_water"]]
        hist_base = df[df["month"] == m]
        if metric in WATER_METRICS:
            hist_base = hist_base[hist_base["has_water"]]
        avg = (
            hist_base.groupby("province_name", as_index=False)[metric]
            .mean().rename(columns={metric: "historical_average"})
        )
        merged = selected.merge(avg, on="province_name", how="left").dropna(subset=[metric])
        if merged.empty:
            return empty_fig(380)

        k = top_k(input)
        merged = merged.sort_values(metric, ascending=False).head(k).sort_values(metric, ascending=True)

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
            name="Selected month", marker=dict(color=PALETTE["accent"], size=11),
        ))
        apply_dark_layout(fig, 380, legend=True)
        fig.update_xaxes(title=label)
        fig.update_yaxes(title="", showgrid=False)
        return fig

    @output
    @render_widget
    def province_timeline_plot():
        p = input.province()
        if p == "All Provinces":
            return empty_fig(360, "Select a single province in the sidebar to see its timeline")
        t = df[df["province_name"] == p].sort_values("date")
        if t.empty:
            return empty_fig(360)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=t["date"], y=t["rainfall_mm"], mode="lines",
            name="Rainfall (mm)", line=dict(color=PALETTE["accent"], width=1.6),
            yaxis="y1",
        ))
        wt = t[t["has_water"]]
        if not wt.empty:
            fig.add_trace(go.Scatter(
                x=wt["date"], y=wt["water_area_km2"], mode="lines",
                name="Surface water (km^2)", line=dict(color=PALETTE["cyan"], width=1.6),
                yaxis="y2",
            ))
        sel_date = pd.Timestamp(year=int(input.year()), month=int(input.month()), day=1)
        fig.add_vline(x=sel_date, line_dash="dot", line_color="#e2e8f0")
        fig.update_layout(
            height=360, margin=dict(l=50, r=55, t=10, b=38),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"], size=11),
            legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
            xaxis=dict(showgrid=True, gridcolor=PALETTE["grid"], zeroline=False, title=""),
            yaxis=dict(title="Rainfall (mm)", showgrid=True, gridcolor=PALETTE["grid"], zeroline=False),
            yaxis2=dict(title="Surface water (km^2)", overlaying="y", side="right", showgrid=False, zeroline=False),
        )
        return fig


app = App(app_ui, server)
