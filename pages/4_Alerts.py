import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_latest_reading
from utils.weather import get_current_weather, get_weather_alerts

st.set_page_config(page_title="Alerts", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .alert-box { padding: 14px 18px; border-radius: 10px; margin: 8px 0; font-weight: 500; }
    .alert-danger  { background: rgba(244,67,54,0.15); border-left: 4px solid #f44336; color: #ef9a9a; }
    .alert-warning { background: rgba(255,193,7,0.15); border-left: 4px solid #ffc107; color: #ffd54f; }
    .alert-success { background: rgba(76,175,80,0.15); border-left: 4px solid #4caf50; color: #a5d6a7; }
    .alert-info    { background: rgba(79,195,247,0.15); border-left: 4px solid #4fc3f7; color: #81d4fa; }
    .threshold-card {
        background: linear-gradient(135deg, #1e3a5f, #0f2d4a);
        border-radius: 12px; padding: 16px; border: 1px solid #2a5a8f;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Alerts & Thresholds")
st.caption("Monitor your environment and get notified when conditions are out of range")
st.markdown("---")

# ── Threshold settings ────────────────────────────────────────────────────────
st.markdown("### ⚙️ Threshold Configuration")

col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
    st.markdown("**🌡️ Temperature Thresholds**")
    temp_min = st.slider("Min temperature (°C)", -10, 25, 15)
    temp_max = st.slider("Max temperature (°C)", 20, 50, 30)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
    st.markdown("**💧 Humidity Thresholds**")
    hum_min = st.slider("Min humidity (%)", 10, 60, 35)
    hum_max = st.slider("Max humidity (%)", 50, 100, 70)
    st.markdown('</div>', unsafe_allow_html=True)

col3, col4 = st.columns(2)
with col3:
    soil_threshold = st.slider("⚠️ Soil Raw Alert (below = very wet, above = dry)", 1000, 4000, 2500)
with col4:
    pressure_min = st.slider("🔵 Min Pressure Alert (hPa)", 950, 1010, 980)

st.markdown("---")

# ── Current status ────────────────────────────────────────────────────────────
st.markdown("### 🔴 Current Alerts")

latest = get_latest_reading()
weather = get_current_weather()
active_alerts = []

if latest:
    temp = latest.get("temperature")
    hum = latest.get("humidity")
    soil = latest.get("soil_raw")
    pres = latest.get("pressure")

    if temp is not None:
        if temp < temp_min:
            active_alerts.append(("danger", f"🥶 Temperature too low: {temp:.1f}°C (min: {temp_min}°C)"))
        elif temp > temp_max:
            active_alerts.append(("danger", f"🔴 Temperature too high: {temp:.1f}°C (max: {temp_max}°C)"))

    if hum is not None:
        if hum < hum_min:
            active_alerts.append(("warning", f"⬇️ Humidity too low: {hum:.1f}% (min: {hum_min}%)"))
        elif hum > hum_max:
            active_alerts.append(("warning", f"⬆️ Humidity too high: {hum:.1f}% (max: {hum_max}%)"))

    if soil is not None and soil > soil_threshold:
        active_alerts.append(("warning", f"🌱 Soil appears dry — raw value {soil} exceeds threshold {soil_threshold}"))

    if pres is not None and pres < pressure_min:
        active_alerts.append(("info", f"🔵 Low pressure: {pres:.1f} hPa — possible weather change incoming"))

# Add weather alerts
if weather:
    for wa in get_weather_alerts(weather):
        active_alerts.append((wa["type"], wa["msg"]))

if active_alerts:
    for level, msg in active_alerts:
        st.markdown(f'<div class="alert-box alert-{level}">{msg}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-box alert-success">✅ All conditions are within normal thresholds</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Historical threshold violations ──────────────────────────────────────────
st.markdown("### 📊 Threshold Violations — Last 7 Days")

if st.button("🔍 Analyze violations"):
    with st.spinner("Loading data..."):
        start_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
        df = get_readings(start_date=start_dt, limit=5000)

    if not df.empty:
        violations = []

        if "temperature" in df.columns:
            temp_violations = df[(df["temperature"] < temp_min) | (df["temperature"] > temp_max)]
            violations.append(("Temperature", len(temp_violations)))

        if "humidity" in df.columns:
            hum_violations = df[(df["humidity"] < hum_min) | (df["humidity"] > hum_max)]
            violations.append(("Humidity", len(hum_violations)))

        if "soil_raw" in df.columns:
            soil_violations = df[df["soil_raw"] > soil_threshold]
            violations.append(("Soil (dry)", len(soil_violations)))

        vcol1, vcol2, vcol3 = st.columns(3)
        metrics = [vcol1, vcol2, vcol3]
        for i, (name, count) in enumerate(violations):
            with metrics[i]:
                color = "🔴" if count > 10 else ("🟡" if count > 0 else "🟢")
                st.metric(f"{color} {name} violations", f"{count:,}")

        # Show temperature violations on chart
        if "temperature" in df.columns and "timestamp" in df.columns:
            df_sorted = df.sort_values("timestamp")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_sorted["timestamp"], y=df_sorted["temperature"],
                mode="lines", name="Temperature",
                line=dict(color="#4fc3f7", width=1.5)
            ))
            fig.add_hrect(y0=temp_min, y1=temp_max,
                          fillcolor="rgba(76,175,80,0.1)",
                          annotation_text="Safe zone", line_width=0)
            fig.add_hline(y=temp_max, line_dash="dash", line_color="#f44336", annotation_text="Max")
            fig.add_hline(y=temp_min, line_dash="dash", line_color="#2196f3", annotation_text="Min")
            fig.update_layout(
                title="Temperature vs Thresholds (7 days)",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300, margin=dict(l=40, r=20, t=40, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data found for the last 7 days.")
