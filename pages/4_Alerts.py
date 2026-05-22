import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_latest_reading
from utils.weather import get_current_weather, get_weather_alerts

st.set_page_config(page_title="Alerts", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    [data-testid="stSidebar"] { background: #0a0f1e !important; border-right: 1px solid #1a2744; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    .section-title {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.18em; margin-bottom: 16px; padding-bottom: 8px;
        border-bottom: 1px solid rgba(128,128,128,0.15); color: #1a56db;
    }
    .alert-box { padding: 12px 16px; border-radius: 10px; margin: 6px 0; font-size: 0.875rem; font-weight: 500; }
    .alert-warning { background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3); color: #b45309; }
    .alert-danger  { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.3);  color: #b91c1c; }
    .alert-success { background: rgba(34,197,94,0.1);  border: 1px solid rgba(34,197,94,0.25); color: #15803d; }
    .alert-info    { background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.3); color: #1d4ed8; }
    .threshold-card {
        border-radius: 12px; padding: 16px;
        border: 1px solid rgba(128,128,128,0.2);
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## Alerts & Thresholds")
st.caption("Monitor your environment and get notified when conditions are out of range")
st.markdown("---")

st.markdown('<div class="section-title">Select Sensors to Monitor</div>', unsafe_allow_html=True)
sensors = st.multiselect("Active sensors",
    options=["Temperature", "Humidity", "Soil Raw", "Pressure"],
    default=["Temperature", "Humidity"])

st.markdown("---")
st.markdown('<div class="section-title">Threshold Configuration</div>', unsafe_allow_html=True)

temp_min = temp_max = hum_min = hum_max = soil_threshold = pressure_min = None

if sensors:
    cols = st.columns(min(len(sensors), 2))
    col_idx = 0

    if "Temperature" in sensors:
        with cols[col_idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Temperature**")
            temp_min = st.slider("Min (°C)", -10, 25, 15)
            temp_max = st.slider("Max (°C)", 20, 50, 30)
            st.markdown('</div>', unsafe_allow_html=True)
        col_idx += 1

    if "Humidity" in sensors:
        with cols[col_idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Humidity**")
            hum_min = st.slider("Min (%)", 10, 60, 35)
            hum_max = st.slider("Max (%)", 50, 100, 70)
            st.markdown('</div>', unsafe_allow_html=True)
        col_idx += 1

    if "Soil Raw" in sensors:
        with cols[col_idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Soil Raw**")
            soil_threshold = st.slider("Dry alert above", 1000, 4000, 2500)
            st.markdown('</div>', unsafe_allow_html=True)
        col_idx += 1

    if "Pressure" in sensors:
        with cols[col_idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Pressure**")
            pressure_min = st.slider("Min (hPa)", 950, 1010, 980)
            st.markdown('</div>', unsafe_allow_html=True)
        col_idx += 1
else:
    st.info("Select at least one sensor above to configure thresholds.")

st.markdown("---")
st.markdown('<div class="section-title">Current Alerts</div>', unsafe_allow_html=True)

latest = get_latest_reading()
weather = get_current_weather()
active_alerts = []

if latest and sensors:
    temp = latest.get("temperature")
    hum = latest.get("humidity")
    soil = latest.get("soil_raw")
    pres = latest.get("pressure")

    if "Temperature" in sensors and temp is not None and temp_min and temp_max:
        if temp < temp_min:
            active_alerts.append(("danger", f"Temperature too low: {temp:.1f}°C (min: {temp_min}°C)"))
        elif temp > temp_max:
            active_alerts.append(("danger", f"Temperature too high: {temp:.1f}°C (max: {temp_max}°C)"))

    if "Humidity" in sensors and hum is not None and hum_min and hum_max:
        if hum < hum_min:
            active_alerts.append(("warning", f"Humidity too low: {hum:.1f}% (min: {hum_min}%)"))
        elif hum > hum_max:
            active_alerts.append(("warning", f"Humidity too high: {hum:.1f}% (max: {hum_max}%)"))

    if "Soil Raw" in sensors and soil is not None and soil_threshold:
        if soil > soil_threshold:
            active_alerts.append(("warning", f"Soil appears dry — raw value {soil} exceeds threshold {soil_threshold}"))

    if "Pressure" in sensors and pres is not None and pressure_min:
        if pres < pressure_min:
            active_alerts.append(("info", f"Low pressure: {pres:.1f} hPa — possible weather change incoming"))

if weather:
    for wa in get_weather_alerts(weather):
        active_alerts.append((wa["type"], wa["msg"]))

if active_alerts:
    for level, msg in active_alerts:
        st.markdown(f'<div class="alert-box alert-{level}">{msg}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-box alert-success">✓ All conditions are within normal thresholds</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div class="section-title">Threshold Violations — Historical Analysis</div>', unsafe_allow_html=True)

# Date selection
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From", value=pd.Timestamp.now() - pd.Timedelta(days=7))
    start_hour = st.slider("Start hour", 0, 23, 0)
with col2:
    end_date = st.date_input("To", value=pd.Timestamp.now())
    end_hour = st.slider("End hour", 0, 23, 23)

SWISS_OFFSET = pd.Timedelta(hours=2)
start_dt = (pd.Timestamp(start_date).replace(hour=start_hour) - SWISS_OFFSET).tz_localize("UTC")
end_dt = (pd.Timestamp(end_date).replace(hour=end_hour, minute=59, second=59) - SWISS_OFFSET).tz_localize("UTC")

if st.button("Analyze violations", type="primary"):
    with st.spinner("Loading data..."):
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=5000)

    if not df.empty:
        if "timestamp" in df.columns:
            ts_min = pd.Timestamp(df["timestamp"].min())
            ts_max = pd.Timestamp(df["timestamp"].max())
            st.caption(f"Data from {ts_min.strftime('%Y-%m-%d %H:%M')} to {ts_max.strftime('%Y-%m-%d %H:%M')} — {len(df):,} readings")

        violations = []
        if "Temperature" in sensors and "temperature" in df.columns and temp_min and temp_max:
            count = len(df[(df["temperature"] < temp_min) | (df["temperature"] > temp_max)])
            violations.append(("Temperature", count))
        if "Humidity" in sensors and "humidity" in df.columns and hum_min and hum_max:
            count = len(df[(df["humidity"] < hum_min) | (df["humidity"] > hum_max)])
            violations.append(("Humidity", count))
        if "Soil Raw" in sensors and "soil_raw" in df.columns and soil_threshold:
            count = len(df[df["soil_raw"] > soil_threshold])
            violations.append(("Soil (dry)", count))

        if violations:
            vcols = st.columns(len(violations))
            for i, (name, count) in enumerate(violations):
                with vcols[i]:
                    color = "🔴" if count > 10 else ("🟡" if count > 0 else "🟢")
                    st.metric(f"{color} {name}", f"{count:,} violations")

        CHART_THEME = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)", height=300,
                           margin=dict(l=40, r=20, t=40, b=40),
                           font=dict(family="Inter, sans-serif", size=11),
                           xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)"),
                           yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)"))

        if "Temperature" in sensors and "temperature" in df.columns and temp_min and temp_max:
            df_sorted = df.sort_values("timestamp")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_sorted["timestamp"], y=df_sorted["temperature"],
                mode="lines", name="Temperature", line=dict(color="#f97316", width=1.5), connectgaps=False))
            fig.add_hrect(y0=temp_min, y1=temp_max, fillcolor="rgba(34,197,94,0.08)",
                          annotation_text="Safe zone", line_width=0)
            fig.add_hline(y=temp_max, line_dash="dash", line_color="#ef4444", annotation_text="Max")
            fig.add_hline(y=temp_min, line_dash="dash", line_color="#3b82f6", annotation_text="Min")
            fig.update_layout(title="Temperature vs Thresholds", **CHART_THEME)
            st.plotly_chart(fig, use_container_width=True)

        if "Humidity" in sensors and "humidity" in df.columns and hum_min and hum_max:
            df_sorted = df.sort_values("timestamp")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_sorted["timestamp"], y=df_sorted["humidity"],
                mode="lines", name="Humidity", line=dict(color="#3b82f6", width=1.5), connectgaps=False))
            fig.add_hrect(y0=hum_min, y1=hum_max, fillcolor="rgba(34,197,94,0.08)",
                          annotation_text="Safe zone", line_width=0)
            fig.add_hline(y=hum_max, line_dash="dash", line_color="#ef4444", annotation_text="Max")
            fig.add_hline(y=hum_min, line_dash="dash", line_color="#3b82f6", annotation_text="Min")
            fig.update_layout(title="Humidity vs Thresholds", **CHART_THEME)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data found for the selected period.")