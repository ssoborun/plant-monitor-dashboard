import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_latest_reading
from utils.weather import get_current_weather, get_weather_alerts

st.set_page_config(page_title="Plant Monitor — Alerts", page_icon="⚡", layout="wide")

SWISS_OFFSET = pd.Timedelta(hours=2)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
div[data-testid="stMetric"] {
    border-radius: 12px; padding: 18px 16px;
    border: 1px solid rgba(128,128,128,0.15);
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
}
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
    font-size: 0.68rem !important; font-weight: 700 !important;
    text-transform: uppercase; letter-spacing: 0.12em; opacity: 0.5;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.5rem !important; font-weight: 600 !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.section-title {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.2em; margin-bottom: 14px; padding-bottom: 8px;
    border-bottom: 1px solid rgba(128,128,128,0.12); color: #2563eb;
}
.alert-box { padding: 10px 14px; border-radius: 8px; margin: 5px 0; font-size: 0.85rem; font-weight: 500; }
.alert-warning { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: #92400e; }
.alert-danger  { background: rgba(239,68,68,0.08);  border: 1px solid rgba(239,68,68,0.25);  color: #991b1b; }
.alert-success { background: rgba(34,197,94,0.08);  border: 1px solid rgba(34,197,94,0.2);   color: #166534; }
.alert-info    { background: rgba(37,99,235,0.08);  border: 1px solid rgba(37,99,235,0.2);   color: #1e40af; }
.threshold-card {
    border-radius: 12px; padding: 16px;
    border: 1px solid rgba(128,128,128,0.15);
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
    margin-bottom: 12px;
}
hr { border-color: rgba(128,128,128,0.1) !important; margin: 20px 0 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Alerts & Thresholds")
st.caption("Monitor your environment and configure alert thresholds")
st.markdown("---")

# ── Sensor selection ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Sensors to Monitor</div>', unsafe_allow_html=True)
sensors = st.multiselect("Active sensors",
    options=["Temperature", "Humidity", "Soil Raw", "Pressure"],
    default=["Temperature", "Humidity"])

st.markdown("---")

# ── Thresholds ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Threshold Configuration</div>', unsafe_allow_html=True)

temp_min = temp_max = hum_min = hum_max = soil_min = soil_max = pres_min = pres_max = None

if sensors:
    cols = st.columns(min(len(sensors), 2))
    idx  = 0

    if "Temperature" in sensors:
        with cols[idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Temperature**")
            temp_min = st.slider("Min (°C)", -10, 25, 15)
            temp_max = st.slider("Max (°C)", 20, 50, 30)
            st.markdown('</div>', unsafe_allow_html=True)
        idx += 1

    if "Humidity" in sensors:
        with cols[idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Humidity**")
            hum_min = st.slider("Min (%)", 10, 60, 35)
            hum_max = st.slider("Max (%)", 50, 100, 70)
            st.markdown('</div>', unsafe_allow_html=True)
        idx += 1

    if "Soil Raw" in sensors:
        with cols[idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Soil Raw**")
            soil_min = st.slider("Min — wet soil", 500, 2000, 1000)
            soil_max = st.slider("Max — dry soil", 1500, 4000, 2500)
            st.markdown('</div>', unsafe_allow_html=True)
        idx += 1

    if "Pressure" in sensors:
        with cols[idx % 2]:
            st.markdown('<div class="threshold-card">', unsafe_allow_html=True)
            st.markdown("**Pressure**")
            pres_min = st.slider("Min (hPa)", 950, 1010, 980)
            pres_max = st.slider("Max (hPa)", 1010, 1050, 1030)
            st.markdown('</div>', unsafe_allow_html=True)
        idx += 1
else:
    st.info("Select at least one sensor above.")

st.markdown("---")

# ── Current Alerts ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Current Alerts</div>', unsafe_allow_html=True)

latest  = get_latest_reading()
weather = get_current_weather()
alerts  = []

if latest and sensors:
    t = latest.get("temperature")
    h = latest.get("humidity")
    s = latest.get("soil_raw")
    p = latest.get("pressure")

    if "Temperature" in sensors and t is not None and temp_min and temp_max:
        if t < temp_min: alerts.append(("danger",  f"Temperature too low: {t:.1f}°C (min {temp_min}°C)"))
        elif t > temp_max: alerts.append(("danger", f"Temperature too high: {t:.1f}°C (max {temp_max}°C)"))

    if "Humidity" in sensors and h is not None and hum_min and hum_max:
        if h < hum_min: alerts.append(("warning",  f"Humidity too low: {h:.1f}% (min {hum_min}%)"))
        elif h > hum_max: alerts.append(("warning", f"Humidity too high: {h:.1f}% (max {hum_max}%)"))

    if "Soil Raw" in sensors and s is not None and soil_min and soil_max:
        if s < soil_min: alerts.append(("warning",  f"Soil too wet: raw {s} below {soil_min}"))
        elif s > soil_max: alerts.append(("warning", f"Soil too dry: raw {s} above {soil_max}"))

    if "Pressure" in sensors and p is not None and pres_min and pres_max:
        if p < pres_min: alerts.append(("info",  f"Low pressure: {p:.1f} hPa — weather change possible"))
        elif p > pres_max: alerts.append(("info", f"High pressure: {p:.1f} hPa"))

if weather:
    for wa in get_weather_alerts(weather):
        alerts.append((wa["type"], wa["msg"]))

if alerts:
    for level, msg in alerts:
        st.markdown(f'<div class="alert-box alert-{level}">{msg}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-box alert-success">✓ All conditions within normal thresholds</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Historical Analysis ───────────────────────────────────────────────────────
st.markdown('<div class="section-title">Historical Violations</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("From", value=pd.Timestamp.now() - pd.Timedelta(days=7))
    start_hour = st.slider("Start hour", 0, 23, 0)
with c2:
    end_date = st.date_input("To", value=pd.Timestamp.now())
    end_hour = st.slider("End hour", 0, 23, 23)

start_dt = (pd.Timestamp(start_date).replace(hour=start_hour) - SWISS_OFFSET).tz_localize("UTC")
end_dt   = (pd.Timestamp(end_date).replace(hour=end_hour, minute=59, second=59) - SWISS_OFFSET).tz_localize("UTC")

if st.button("Analyze violations", type="primary"):
    with st.spinner("Loading data…"):
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=5000)

    if not df.empty:
        ts_min = pd.Timestamp(df["timestamp"].min())
        ts_max = pd.Timestamp(df["timestamp"].max())
        st.caption(f"Data: {ts_min.strftime('%Y-%m-%d %H:%M')} → {ts_max.strftime('%Y-%m-%d %H:%M')} — {len(df):,} readings")

        violations = []
        if "Temperature" in sensors and "temperature" in df.columns and temp_min and temp_max:
            violations.append(("Temperature", len(df[(df["temperature"] < temp_min) | (df["temperature"] > temp_max)])))
        if "Humidity" in sensors and "humidity" in df.columns and hum_min and hum_max:
            violations.append(("Humidity", len(df[(df["humidity"] < hum_min) | (df["humidity"] > hum_max)])))
        if "Soil Raw" in sensors and "soil_raw" in df.columns and soil_min and soil_max:
            violations.append(("Soil Raw", len(df[(df["soil_raw"] < soil_min) | (df["soil_raw"] > soil_max)])))
        if "Pressure" in sensors and "pressure" in df.columns and pres_min and pres_max:
            violations.append(("Pressure", len(df[(df["pressure"] < pres_min) | (df["pressure"] > pres_max)])))

        if violations:
            vcols = st.columns(len(violations))
            for i, (name, count) in enumerate(violations):
                with vcols[i]:
                    icon = "🔴" if count > 10 else ("🟡" if count > 0 else "🟢")
                    st.metric(f"{icon} {name}", f"{count:,} violations")

        CHART = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", height=320,
                     margin=dict(l=40, r=60, t=36, b=36),
                     font=dict(family="Inter, sans-serif", size=11),
                     xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                     yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"))

        df_s = df.sort_values("timestamp")
        sel  = []
        if "Temperature" in sensors and "temperature" in df.columns: sel.append(("temperature","Temperature (°C)","#f97316"))
        if "Humidity"    in sensors and "humidity"    in df.columns: sel.append(("humidity",   "Humidity (%)",    "#3b82f6"))
        if "Soil Raw"    in sensors and "soil_raw"    in df.columns: sel.append(("soil_raw",   "Soil Raw",        "#22c55e"))
        if "Pressure"    in sensors and "pressure"    in df.columns: sel.append(("pressure",   "Pressure (hPa)",  "#a855f7"))

        # Combined overview chart
        if len(sel) >= 2:
            fig = go.Figure()
            col_n, col_l, col_c = sel[0]
            fig.add_trace(go.Scatter(x=df_s["timestamp"], y=df_s[col_n], name=col_l,
                line=dict(color=col_c, width=1.5), connectgaps=False, yaxis="y1"))
            for col_n, col_l, col_c in sel[1:]:
                fig.add_trace(go.Scatter(x=df_s["timestamp"], y=df_s[col_n], name=col_l,
                    line=dict(color=col_c, width=1.5, dash="dot"), connectgaps=False, yaxis="y2"))
            fig.update_layout(
                title="All sensors overview",
                yaxis=dict(title=sel[0][1], color=sel[0][2], showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                yaxis2=dict(title=" / ".join([c[1] for c in sel[1:]]), overlaying="y", side="right", showgrid=False),
                legend=dict(x=0.01, y=0.99),
                template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=320,
                margin=dict(l=40, r=60, t=36, b=36),
                font=dict(family="Inter, sans-serif", size=11))
            st.plotly_chart(fig, use_container_width=True)

        # Individual threshold charts
        def threshold_chart(col, label, color, lo, hi):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_s["timestamp"], y=df_s[col], mode="lines",
                name=label, line=dict(color=color, width=1.5), connectgaps=False))
            fig.add_hrect(y0=lo, y1=hi, fillcolor="rgba(34,197,94,0.07)", annotation_text="Safe zone", line_width=0)
            fig.add_hline(y=hi, line_dash="dash", line_color="#ef4444", annotation_text="Max")
            fig.add_hline(y=lo, line_dash="dash", line_color="#3b82f6", annotation_text="Min")
            fig.update_layout(title=f"{label} vs Thresholds", **CHART)
            st.plotly_chart(fig, use_container_width=True)

        if "Temperature" in sensors and "temperature" in df.columns and temp_min and temp_max:
            threshold_chart("temperature", "Temperature (°C)", "#f97316", temp_min, temp_max)
        if "Humidity" in sensors and "humidity" in df.columns and hum_min and hum_max:
            threshold_chart("humidity", "Humidity (%)", "#3b82f6", hum_min, hum_max)
        if "Soil Raw" in sensors and "soil_raw" in df.columns and soil_min and soil_max:
            threshold_chart("soil_raw", "Soil Raw ADC", "#22c55e", soil_min, soil_max)
        if "Pressure" in sensors and "pressure" in df.columns and pres_min and pres_max:
            threshold_chart("pressure", "Pressure (hPa)", "#a855f7", pres_min, pres_max)
    else:
        st.warning("No data found for the selected period.")