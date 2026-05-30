from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_widget
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MekongFloodLens")


# ==========================================================
# Data loading
# ==========================================================

PANEL_PATH = "data/processed/province_month_panel.csv"
BOUNDARY_PATH = "data/raw/mekong_provinces_boundary.geojson"

df = pd.read_csv(PANEL_PATH)
df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
df["month"] = pd.to_numeric(df["month"], errors="coerce").astype(int)

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

if df["combined_risk_score"].isna().all():
    df["rainfall_score"] = minmax(df["rainfall_zscore"].clip(lower=0))
    df["water_score"] = minmax(df["water_area_pct"].fillna(0))
    df["drought_score"] = minmax((-df["rainfall_zscore"]).clip(lower=0))
    df["exposure_score"] = 0.6 * minmax(df["population_total"].fillna(0)) + 0.4 * minmax(df["cropland_area_km2"].fillna(0))
    df["combined_risk_score"] = ( #combine risk score as a weighted average of components, with rainfall and water given slightly higher weight
        0.35 * df["water_score"]
        + 0.25 * df["rainfall_score"]
        + 0.25 * df["drought_score"]
        + 0.15 * df["exposure_score"]
    )
else:
    df["rainfall_score"] = minmax(df["rainfall_zscore"].clip(lower=0))
    df["water_score"] = minmax(df["water_area_pct"].fillna(0))
    df["drought_score"] = minmax((-df["rainfall_zscore"]).clip(lower=0))
    df["exposure_score"] = 0.6 * minmax(df["population_total"].fillna(0)) + 0.4 * minmax(df["cropland_area_km2"].fillna(0))

df = df.fillna(0)

with open(BOUNDARY_PATH, encoding="utf-8") as f:
    geojson_data = json.load(f)

provinces = sorted(df["province_name"].dropna().unique().tolist())
years = sorted(df["year"].dropna().unique().tolist())

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
    padding-bottom: 12px;
}
.header h1 {
    margin: 0;
    font-size: 2.25rem;
    font-weight: 800;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.subtitle {
    margin-top: 4px;
    color: var(--muted);
}
.story-strip, .flow-note {
    color: #cbd5e1;
    background: rgba(56, 189, 248, 0.08);
    border: 1px solid rgba(56, 189, 248, 0.20);
    border-radius: 14px;
    padding: 10px 14px;
    margin-bottom: 18px;
    font-size: 0.92rem;
}
.filter-bar {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px 16px 6px 16px;
    margin-bottom: 18px;
}
.filter-title {
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 8px;
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
.bottom-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
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
@media (max-width: 1200px) {
    .overview-grid, .bottom-grid, .kpi-grid {
        grid-template-columns: 1fr;
    }
}
"""


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
        ui.div(
            ui.h1("Mekong FloodLens"),
            ui.div(
                "Interactive water-risk dashboard for the Vietnamese Mekong Delta",
                class_="subtitle",
            ),
            class_="header",
        ),
        ui.div(
            "Analytical flow: filter context → locate spatial patterns → summarize key signals → compare provinces → inspect trends and anomalies.",
            class_="story-strip",
        ),
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
            ui.div(ui.div("Average rainfall", class_="kpi-label"), ui.output_ui("kpi_rain"), ui.div("Selected context", class_="kpi-note"), class_="kpi"),
            ui.div(ui.div("Surface water extent", class_="kpi-label"), ui.output_ui("kpi_water"), ui.div("Flood proxy where available", class_="kpi-note"), class_="kpi cyan"),
            ui.div(ui.div("Population context", class_="kpi-label"), ui.output_ui("kpi_pop"), ui.div("Annual exposure layer", class_="kpi-note"), class_="kpi purple"),
            ui.div(ui.div("Highest selected metric", class_="kpi-label"), ui.output_ui("kpi_top"), ui.div("Strongest province signal", class_="kpi-note"), class_="kpi orange"),
            class_="kpi-grid",
        ),
        ui.div(
            ui.div(
                ui.div(
                    ui.div("Interactive Mekong Delta map", class_="card-title"),
                    ui.div("Start here: locate spatial water-risk patterns by province.", class_="card-subtitle"),
                    ui.div(output_widget("map_plot", height="580px", width="100%"), class_="map-widget-shell"),
                    class_="card map-card",
                ),
            ),
            ui.div(
                ui.div(
                    ui.div("Province ranking", class_="card-title"),
                    ui.div("Compare provinces and identify priority areas for the selected month.", class_="card-subtitle"),
                    output_widget("ranking_plot", height="255px"),
                    class_="card compact",
                ),
                ui.div(
                    ui.div("Risk component breakdown", class_="card-title"),
                    ui.div("See whether the signal comes from rainfall, surface water, or exposure.", class_="card-subtitle"),
                    output_widget("breakdown_plot", height="255px"),
                    class_="card compact",
                ),
                class_="side-grid",
            ),
            class_="overview-grid",
        ),
        ui.div(
            ui.div(
                ui.div("Rainfall trend", class_="card-title"),
                ui.div("Track how rainfall compares with the long-run monthly average.", class_="card-subtitle"),
                output_widget("rain_trend_plot", height="320px"),
                class_="card",
            ),
            ui.div(
                ui.div("Anomaly heatmap", class_="card-title"),
                ui.div("Spot unusual months and cross-province rainfall anomalies.", class_="card-subtitle"),
                output_widget("heatmap_plot", height="320px"),
                class_="card",
            ),
            ui.div(
                ui.div("Province comparison", class_="card-title"),
                ui.div("Benchmark selected-month values against historical averages.", class_="card-subtitle"),
                output_widget("comparison_plot", height="320px"),
                class_="card",
            ),
            class_="bottom-grid",
        ),
        ui.div(
            "All views are linked by the global filters. Rainfall has the longest coverage; water and population layers are shown only where available.",
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


# ==========================================================
# Server
# ==========================================================

def server(input, output, session):

    @reactive.effect
    def _log_filters():
        logger.info(f"User filter updated: Province={input.province()}, Year={input.year()}, Month={input.month()}, Metric={input.metric()}")

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

    @output
    @render_widget
    def map_plot():
        d = current_all_provinces_df(input)
        metric = input.metric()
        label = metric_labels.get(metric, metric)
        color_scale = metric_color_scales.get(metric, "Viridis")

        fig = px.choropleth_mapbox(
            d,
            geojson=geojson_data,
            locations="province_name",
            featureidkey="properties.ADM1_NAME",
            color=metric,
            hover_name="province_name",
            hover_data={
                "rainfall_mm": ":,.1f",
                "rainfall_anomaly": ":,.1f",
                "water_area_km2": ":,.1f",
                "water_area_pct": ":,.2f",
                "population_total": ":,.0f",
                "cropland_area_km2": ":,.1f",
                metric: ":,.2f",
                "province_name": False,
            },
            color_continuous_scale=color_scale,
            mapbox_style="carto-darkmatter",
            center={"lat": 9.95, "lon": 105.65},
            zoom=6.7,
            opacity=0.78,
        )
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

        d = (
            d[["province_name", metric]]
            .dropna()
            .sort_values(metric, ascending=True)
            .tail(13)
        )

        fig = px.bar(
            d,
            x=metric,
            y="province_name",
            orientation="h",
            text=metric,
            labels={metric: label, "province_name": ""},
        )
        fig.update_traces(
            marker_color="#38bdf8",
            texttemplate="%{text:.2f}",
            textposition="outside",
            cliponaxis=False,
        )
        fig.update_layout(
            margin=dict(l=5, r=45, t=5, b=25),
            height=255,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=11),
            xaxis=dict(showgrid=True, gridcolor="#1e293b", zeroline=False),
            yaxis=dict(showgrid=False, automargin=True),
        )
        return fig

    @output
    @render_widget
    def breakdown_plot():
        d = current_filter_df(input)
        if d.empty:
            vals = [0, 0, 0]
        else:
            vals = [
                float(d["rainfall_score"].mean()),
                float(d["water_score"].mean()),
                float(d["exposure_score"].mean()),
            ]

        fig = go.Figure(
            go.Bar(
                x=["Rainfall", "Water", "Exposure"],
                y=vals,
                marker_color=["#38bdf8", "#0ea5e9", "#8b5cf6"],
            )
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=5, b=25),
            height=255,
            yaxis=dict(range=[0, 1], showgrid=True, gridcolor="#1e293b", title="Normalized score"),
            xaxis=dict(showgrid=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=11),
        )
        return fig

    @output
    @render_widget
    def rain_trend_plot():
        d = selected_province_or_mean_year_df(input)
        selected_m = int(input.month())

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=d["month"],
                y=d["rainfall_mm"],
                mode="lines+markers",
                name="Selected year",
                line=dict(color="#38bdf8", width=3),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=d["month"],
                y=d["monthly_mean"],
                mode="lines+markers",
                name="Historical monthly mean",
                line=dict(color="#f43f5e", width=2, dash="dash"),
            )
        )
        fig.add_vline(x=selected_m, line_dash="dot", line_color="#e2e8f0")
        fig.update_layout(
            margin=dict(l=45, r=20, t=10, b=38),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=11),
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
            xaxis=dict(title="Month", dtick=1, showgrid=True, gridcolor="#1e293b"),
            yaxis=dict(title="Rainfall (mm)", showgrid=True, gridcolor="#1e293b", automargin=True),
        )
        return fig

    @output
    @render_widget
    def heatmap_plot():
        y = int(input.year())
        d = df[df["year"] == y].copy()
        pivot = d.pivot_table(
            index="province_name",
            columns="month",
            values="rainfall_zscore",
            aggfunc="mean",
        ).reindex(provinces)

        fig = px.imshow(
            pivot,
            labels=dict(x="Month", y="", color="Z-score"),
            color_continuous_scale="RdBu",
            zmin=-2,
            zmax=2,
            aspect="auto",
        )
        fig.update_layout(
            margin=dict(l=80, r=5, t=10, b=35),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=10),
            coloraxis_colorbar=dict(title="Anomaly", thickness=10, len=0.75),
            xaxis=dict(dtick=1),
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
        merged = merged.sort_values(metric, ascending=False).head(10)
        merged = merged.sort_values(metric, ascending=True)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=merged["historical_average"],
                y=merged["province_name"],
                mode="markers",
                name="Historical avg",
                marker=dict(color="#94a3b8", size=9, symbol="circle-open"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=merged[metric],
                y=merged["province_name"],
                mode="markers",
                name="Selected month",
                marker=dict(color="#38bdf8", size=10),
            )
        )

        for _, row in merged.iterrows():
            fig.add_shape(
                type="line",
                x0=row["historical_average"],
                x1=row[metric],
                y0=row["province_name"],
                y1=row["province_name"],
                line=dict(color="#334155", width=2),
            )

        fig.update_layout(
            margin=dict(l=80, r=20, t=10, b=38),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=10),
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
            xaxis=dict(title=label, showgrid=True, gridcolor="#1e293b"),
            yaxis=dict(title="", showgrid=False, automargin=True),
        )
        return fig


app = App(app_ui, server)
