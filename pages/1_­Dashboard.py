import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_latest_reading, get_hourly_averages, get_stats, get_readings
from utils.weather import get_current_weather, get_forecast, get_weather_alerts

st.set_page_config(page_title="Plant Monitor", page_icon="📊", layout="wide")

SWISS_OFFSET = pd.Timedelta(hours=2)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    div[data-testid="stMetric"] {
        border-radius: 14px;
        padding: 20px 18px;
        border: 1px solid rgba(128,128,128,0.2);
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-2px); }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        opacity: 0.55;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 600 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

    .section-title {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(128,128,128,0.15);
        color: #1a56db;
    }
    .weather-card {
        border-radius: 12px;
        padding: 14px;
        border: 1px solid rgba(128,128,128,0.15);
        text-align: center;
        box-shadow: 0 1px 6px rgba(0,0,0,0.05);
    }
    .forecast-day  { font-weight: 700; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #1a56db; }
    .forecast-icon { font-size: 1.6rem; margin: 8px 0; }
    .forecast-temp { font-size: 0.85rem; font-family: 'JetBrains Mono', monospace; }
    .forecast-rain { font-size: 0.72rem; margin-top: 4px; color: #3b82f6; }
    .forecast-desc { font-size: 0.7rem; opacity: 0.45; margin-top: 2px; }

    .alert-box { padding: 12px 16px; border-radius: 10px; margin: 6px 0; font-size: 0.875rem; font-weight: 500; }
    .alert-warning { background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); color: #b45309; }
    .alert-danger  { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.3);  color: #b91c1c; }
    .alert-success { background: rgba(34,197,94,0.1);  border: 1px solid rgba(34,197,94,0.25); color: #15803d; }
</style>
""", unsafe_allow_html=True)

col_title, col_refresh, col_time = st.columns([3, 1, 2])
with col_title:
    st.markdown("## Plant Monitor")
with col_refresh:
    if st.button("↻ Refresh"):
        st.cache_data.clear()
        st.rerun()

latest = get_latest_reading()
weather = get_current_weather()
hourly_df = get_hourly_averages(days=7)
stats_24h = get_stats(start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24))

with col_time:
    if latest and latest.get("timestamp"):
        ts = pd.Timestamp(latest["timestamp"]) + SWISS_OFFSET
        st.caption(f"Last update — {ts.strftime('%d %b %Y, %H:%M:%S')}")

st.markdown("---")

st.markdown('<div class="section-title">Indoor Sensor Readings</div>', unsafe_allow_html=True)

if latest:
    temp = latest.get("temperature")
    hum = latest.get("humidity")
    pres = latest.get("pressure")
    soil_raw = latest.get("soil_raw")
    soil_moist = latest.get("soil_moisture")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        delta_temp = None
        if stats_24h.get("avg_temp") and temp:
            delta_temp = round(temp - stats_24h["avg_temp"], 1)
        st.metric("Temperature", f"{temp:.1f} °C" if temp else "—",
                  delta=f"{delta_temp:+.1f}°C vs 24h avg" if delta_temp else None)
    with col2:
        hum_status = "Optimal" if hum and 40 <= hum <= 60 else ("Too dry" if hum and hum < 40 else "Too humid")
        st.metric("Humidity", f"{hum:.1f} %" if hum else "—", delta=hum_status)
    with col3:
        pres_status = "High pressure" if pres and pres > 1013 else ("Low pressure" if pres and pres < 1000 else "Normal")
        st.metric("Pressure", f"{pres:.1f} hPa" if pres else "—", delta=pres_status)
    with col4:
        soil_comment = "Wet" if soil_raw and soil_raw < 1500 else ("Moist" if soil_raw and soil_raw < 2000 else "Dry")
        st.metric("Soil Raw", f"{soil_raw}" if soil_raw else "—", delta=soil_comment)
    with col5:
        st.metric("Soil Moisture", f"{soil_moist} %" if soil_moist else "—")
else:
    st.warning("No sensor data available.")

st.markdown("---")

st.markdown('<div class="section-title">Previous Readings</div>', unsafe_allow_html=True)

recent_df = get_readings(start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=6), limit=11)

if not recent_df.empty:
    display_recent = recent_df.copy()
    if "timestamp" in display_recent.columns:
        display_recent["timestamp"] = (display_recent["timestamp"] + SWISS_OFFSET).dt.strftime("%Y-%m-%d %H:%M:%S")
    display_recent = display_recent.sort_values("timestamp", ascending=False).reset_index(drop=True).iloc[1:]
    cols_order = [c for c in ["timestamp", "temperature", "humidity", "pressure", "soil_raw", "soil_moisture"] if c in display_recent.columns]
    st.dataframe(display_recent[cols_order].reset_index(drop=True), use_container_width=True, height=220, hide_index=True)
    st.caption("Last 10 readings")
else:
    st.info("No recent readings available.")

st.markdown("---")

st.markdown('<div class="section-title">Outdoor Weather — Lausanne</div>', unsafe_allow_html=True)

if weather:
    wcol1, wcol2, wcol3, wcol4, wcol5 = st.columns(5)
    with wcol1:
        st.metric(f"{weather['icon']} {weather['city']}", f"{weather['temp']} °C", delta=f"Feels {weather['feels_like']}°C")
    with wcol2:
        st.metric("Condition", weather["description"].capitalize())
    with wcol3:
        st.metric("Ext. Humidity", f"{weather['humidity']} %")
    with wcol4:
        st.metric("Wind", f"{weather['wind_speed']} m/s")
    with wcol5:
        st.metric("Sunrise / Sunset", f"{weather['sunrise']} / {weather['sunset']}")

    alerts = get_weather_alerts(weather)
    for alert in alerts:
        st.markdown(f'<div class="alert-box alert-{alert["type"]}">{alert["msg"]}</div>', unsafe_allow_html=True)

    st.markdown("<br>**5-Day Forecast**", unsafe_allow_html=True)
    forecast = get_forecast()
    if forecast:
        fcols = st.columns(len(forecast))
        for i, day in enumerate(forecast):
            with fcols[i]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="forecast-day">{day['date']}</div>
                    <div class="forecast-icon">{day['icon']}</div>
                    <div class="forecast-temp">{day['temp_max']}° / {day['temp_min']}°</div>
                    <div class="forecast-rain">{day['rain_prob']}% rain</div>
                    <div class="forecast-desc">{day['description']}</div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("Weather data unavailable.")

st.markdown("---")

st.markdown('<div class="section-title">Alerts</div>', unsafe_allow_html=True)

has_alert = False
if latest:
    hum = latest.get("humidity")
    temp = latest.get("temperature")
    if hum and hum < 40:
        st.markdown('<div class="alert-box alert-warning">⚠ Humidity below 40% — consider using a humidifier</div>', unsafe_allow_html=True)
        has_alert = True
    if hum and hum > 70:
        st.markdown('<div class="alert-box alert-warning">⚠ Humidity above 70% — check for condensation or mold risk</div>', unsafe_allow_html=True)
        has_alert = True
    if temp and temp > 28:
        st.markdown(f'<div class="alert-box alert-danger">High indoor temperature: {temp:.1f}°C</div>', unsafe_allow_html=True)
        has_alert = True
    if temp and temp < 15:
        st.markdown(f'<div class="alert-box alert-warning">Low indoor temperature: {temp:.1f}°C</div>', unsafe_allow_html=True)
        has_alert = True

if not has_alert:
    st.markdown('<div class="alert-box alert-success">✓ All conditions normal</div>', unsafe_allow_html=True)

st.markdown("---")

st.markdown('<div class="section-title">Historical Data — Last 7 Days</div>', unsafe_allow_html=True)

if not hourly_df.empty:
    full_range = pd.date_range(start=hourly_df["hour"].min(), end=hourly_df["hour"].max(), freq="h")
    full_grid = pd.DataFrame({"hour": full_range})
    hourly_df["hour"] = pd.to_datetime(hourly_df["hour"]).dt.tz_localize(None)
    full_grid["hour"] = full_grid["hour"].dt.tz_localize(None)
    hourly_filled = full_grid.merge(hourly_df, on="hour", how="left")

    CHART_THEME = dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=20, t=40, b=40),
        height=280,
        font=dict(family="Inter, sans-serif", size=11),
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)", showline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)", showline=False),
        title_font=dict(size=13, family="Inter, sans-serif"),
    )

    charts = [
        ("avg_temperature", "Temperature (°C)", "°C", "#f97316"),
        ("avg_humidity",    "Humidity (%)",      "%",  "#3b82f6"),
        ("avg_soil_raw",    "Soil Raw ADC",       "ADC","#22c55e"),
        ("avg_pressure",    "Pressure (hPa)",     "hPa","#a855f7"),
    ]

    for col, title, unit, color in charts:
        series = hourly_filled[col].dropna()
        if series.empty:
            continue
        padding = (series.max() - series.min()) * 0.15 or 1
        y_min = series.min() - padding
        y_max = series.max() + padding

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hourly_filled["hour"], y=hourly_filled[col],
            mode="lines", name=unit,
            line=dict(color=color, width=2),
            connectgaps=False
        ))
        if col == "avg_humidity":
            fig.add_hrect(y0=40, y1=60, fillcolor="rgba(34,197,94,0.08)",
                          annotation_text="Optimal zone", annotation_position="top left",
                          annotation_font_size=10, line_width=0)
        fig.update_layout(
            title=title, yaxis_title=unit, xaxis_title="",
            showlegend=False, yaxis_range=[y_min, y_max],
            **CHART_THEME
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No historical data available yet.")