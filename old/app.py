from shiny import App, render, ui, reactive
import pandas as pd
import json
import plotly.express as px
from shinywidgets import output_widget, render_widget
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MekongFloodLens")

# Load data and handle missing values to avoid JSON serialization errors with NaN
df = pd.read_csv("data/processed/province_month_panel.csv")
df = df.fillna(0)
with open("data/raw/mekong_provinces_boundary.geojson", encoding="utf-8") as f:
    geojson_data = json.load(f)

provinces = df["province_name"].unique().tolist()
provinces.sort()
years = df["year"].unique().tolist()
years.sort()

# Sleek Dark UI CSS
custom_css = """
body, html {
    margin: 0;
    padding: 0;
    background-color: #0b1120;
    color: #f8fafc;
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
}
.app-container {
    padding: 20px;
}
.header {
    margin-bottom: 30px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e293b;
}
.header h1 {
    font-weight: 700;
    font-size: 2rem;
    margin: 0;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.control-panel {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 20px;
    height: 100%;
}
.custom-card {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}
.card-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 15px;
    color: #e2e8f0;
}
.value-box-container {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
}
.v-box {
    flex: 1;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    position: relative;
    overflow: hidden;
}
.v-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0));
    pointer-events: none;
}
.v-box.blue { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
.v-box.cyan { background: linear-gradient(135deg, #0ea5e9, #0369a1); }
.v-box.purple { background: linear-gradient(135deg, #8b5cf6, #6d28d9); }

.v-box-title {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    opacity: 0.8;
    margin-bottom: 8px;
    font-weight: 600;
}
.v-box-value {
    font-size: 2.5rem;
    font-weight: 700;
}
/* Override shiny inputs */
.shiny-input-container { color: #cbd5e1; }
.form-select, .form-control {
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
    border-radius: 8px;
}
.form-select:focus, .form-control:focus {
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.5) !important;
    border-color: #38bdf8 !important;
}
"""

app_ui = ui.page_fluid(
    ui.head_content(
        ui.tags.style(custom_css),
        ui.tags.link(href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap", rel="stylesheet")
    ),
    ui.div(
        ui.div(ui.h1("Mekong FloodLens"), class_="header"),
        ui.row(
            ui.column(3,
                ui.div(
                    ui.h4("Filters", style="margin-top:0; margin-bottom:20px; font-weight:600; color:#e2e8f0;"),
                    ui.input_select("province", "Province", choices=["All"] + provinces),
                    ui.input_select("year", "Year", choices=[str(y) for y in years], selected="2021"),
                    ui.input_slider("month", "Month", 1, 12, 9),
                    class_="control-panel"
                )
            ),
            ui.column(9,
                ui.div(
                    ui.div(
                        ui.div("Avg Rainfall (mm)", class_="v-box-title"),
                        ui.output_ui("val_rain"),
                        class_="v-box blue"
                    ),
                    ui.div(
                        ui.div("Water Extent (km²)", class_="v-box-title"),
                        ui.output_ui("val_water"),
                        class_="v-box cyan"
                    ),
                    ui.div(
                        ui.div("Population Context", class_="v-box-title"),
                        ui.output_ui("val_pop"),
                        class_="v-box purple"
                    ),
                    class_="value-box-container"
                ),
                ui.row(
                    ui.column(6,
                        ui.div(
                            ui.div("Mekong Delta Map (Rainfall Anomaly)", class_="card-title"),
                            output_widget("map_plot", height="440px"),
                            class_="custom-card",
                            style="height: 500px;"
                        )
                    ),
                    ui.column(6,
                        ui.div(
                            ui.div("Rainfall Trend", class_="card-title"),
                            output_widget("rain_trend_plot", height="180px"),
                            class_="custom-card",
                            style="margin-bottom: 20px;"
                        ),
                        ui.div(
                            ui.div("Surface Water Area Trend", class_="card-title"),
                            output_widget("water_trend_plot", height="180px"),
                            class_="custom-card",
                            style="margin-bottom: 0;"
                        )
                    )
                )
            )
        ),
        class_="app-container"
    )
)

def server(input, output, session):
    @reactive.effect
    def _log_filters():
        logger.info(f"User filter updated: Province={input.province()}, Year={input.year()}, Month={input.month()}")

    @reactive.calc
    def filtered_df():
        y = int(input.year())
        m = int(input.month())
        p = input.province()
        if p == "All":
            return df[(df["year"] == y) & (df["month"] == m)]
        else:
            return df[(df["province_name"] == p) & (df["year"] == y) & (df["month"] == m)]

    @reactive.calc
    def filtered_year_df():
        y = int(input.year())
        p = input.province()
        if p == "All":
            return df[df["year"] == y].groupby("month").agg({"rainfall_mm": "mean", "monthly_mean": "mean", "water_area_km2": "sum"}).reset_index()
        else:
            return df[(df["province_name"] == p) & (df["year"] == y)]

    @output
    @render.ui
    def val_rain():
        d = filtered_df()
        if len(d) > 0:
            val = d["rainfall_mm"].mean()
            return ui.div(f"{val:.1f}", class_="v-box-value")
        return ui.div("N/A", class_="v-box-value")

    @output
    @render.ui
    def val_water():
        d = filtered_df()
        if len(d) > 0:
            val = d["water_area_km2"].sum()
            return ui.div(f"{val:,.1f}", class_="v-box-value")
        return ui.div("N/A", class_="v-box-value")

    @output
    @render.ui
    def val_pop():
        d = filtered_df()
        if len(d) > 0:
            val = d["population_total"].sum()
            return ui.div(f"{val:,.0f}", class_="v-box-value")
        return ui.div("N/A", class_="v-box-value")

    @output
    @render_widget
    def map_plot():
        y = int(input.year())
        m = int(input.month())
        map_df = df[(df["year"] == y) & (df["month"] == m)]
        
        fig = px.choropleth_mapbox(
            map_df,
            geojson=geojson_data,
            locations="province_name",
            featureidkey="properties.ADM1_NAME",
            color="rainfall_anomaly",
            hover_name="province_name",
            hover_data={"rainfall_anomaly": ":.2f", "rainfall_mm": ":.2f", "water_area_km2": ":.2f", "province_name": False},
            color_continuous_scale="RdBu",
            mapbox_style="carto-darkmatter",
            center={"lat": 9.9, "lon": 105.7},
            zoom=7,
            opacity=0.75
        )
        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            coloraxis_colorbar=dict(
                title="Anomaly (mm)",
                thickness=15,
                len=0.7,
                yanchor="bottom",
                y=0.1,
                xanchor="right",
                x=0.95
            )
        )
        return fig

    @output
    @render_widget
    def rain_trend_plot():
        d = filtered_year_df()
        fig = px.line(
            d, 
            x="month", 
            y=["rainfall_mm", "monthly_mean"], 
            labels={"value": "Rainfall (mm)", "variable": "", "month": ""}
        )
        # Update colors to match dark theme better
        fig.data[0].line.color = '#38bdf8'
        if len(fig.data) > 1:
            fig.data[1].line.color = '#f43f5e'
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8', size=11),
            margin={"r":10,"t":10,"l":10,"b":10},
            xaxis=dict(showgrid=True, gridcolor='#1e293b', dtick=1),
            yaxis=dict(showgrid=True, gridcolor='#1e293b'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title="")
        )
        return fig

    @output
    @render_widget
    def water_trend_plot():
        d = filtered_year_df()
        fig = px.line(
            d, 
            x="month", 
            y="water_area_km2", 
            labels={"water_area_km2": "Area (km²)", "month": ""}
        )
        fig.update_traces(line_color='#0ea5e9')
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8', size=11),
            margin={"r":10,"t":10,"l":10,"b":10},
            xaxis=dict(showgrid=True, gridcolor='#1e293b', dtick=1),
            yaxis=dict(showgrid=True, gridcolor='#1e293b')
        )
        return fig

app = App(app_ui, server)
