import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_latest_reading, get_hourly_averages, get_stats, get_readings
from utils.weather import get_current_weather, get_forecast, get_weather_alerts

st.set_page_config(page_title="Plant Monitor — Dashboard", page_icon="🌱", layout="wide")

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
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    cursor: pointer;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    border-color: rgba(37,99,235,0.3);
}
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
    font-size: 0.68rem !important; font-weight: 700 !important;
    text-transform: uppercase; letter-spacing: 0.12em; opacity: 0.5;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.65rem !important; font-weight: 600 !important;
    font-family: 'JetBrains Mono', monospace !important; letter-spacing: -0.02em;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

.section-title {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.2em; margin-bottom: 14px; padding-bottom: 8px;
    border-bottom: 1px solid rgba(128,128,128,0.12); color: #2563eb;
}
.detail-panel {
    border-radius: 14px; padding: 20px;
    border: 1px solid rgba(37,99,235,0.2);
    background: rgba(37,99,235,0.02);
    margin: 12px 0;
}
.stat-box {
    border-radius: 10px; padding: 12px 16px;
    border: 1px solid rgba(128,128,128,0.12);
    text-align: center;
}
.stat-label { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.45; margin-bottom: 4px; }
.stat-value { font-size: 1.3rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.weather-card {
    border-radius: 10px; padding: 12px 10px;
    border: 1px solid rgba(128,128,128,0.12);
    text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.forecast-day  { font-weight: 700; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: #2563eb; }
.forecast-icon { font-size: 1.5rem; margin: 6px 0; }
.forecast-temp { font-size: 0.82rem; font-family: 'JetBrains Mono', monospace; font-weight: 500; }
.forecast-rain { font-size: 0.68rem; margin-top: 3px; color: #3b82f6; }
.forecast-desc { font-size: 0.65rem; opacity: 0.4; margin-top: 2px; }
.alert-box { padding: 10px 14px; border-radius: 8px; margin: 5px 0; font-size: 0.85rem; font-weight: 500; }
.alert-warning { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: #92400e; }
.alert-danger  { background: rgba(239,68,68,0.08);  border: 1px solid rgba(239,68,68,0.25);  color: #991b1b; }
.alert-success { background: rgba(34,197,94,0.08);  border: 1px solid rgba(34,197,94,0.2);   color: #166534; }
hr { border-color: rgba(128,128,128,0.1) !important; margin: 20px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state for selected card ──────────────────────────────────────────
if "selected_sensor" not in st.session_state:
    st.session_state["selected_sensor"] = None

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_refresh, col_time = st.columns([3, 1, 2])
with col_title:
    st.markdown("## 🌱 Plant Monitor")
with col_refresh:
    if st.button("↻ Refresh"):
        st.cache_data.clear()
        st.rerun()

latest    = get_latest_reading()
weather   = get_current_weather()
hourly_df = get_hourly_averages(days=7)
stats_24h = get_stats(start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24))

with col_time:
    if latest and latest.get("timestamp"):
        ts = pd.Timestamp(latest["timestamp"]) + SWISS_OFFSET
        st.caption(f"Last update — {ts.strftime('%d %b %Y, %H:%M:%S')}")

st.markdown("---")

# ── Helper: detail panel ──────────────────────────────────────────────────────
def show_detail_panel(sensor_key: str, label: str, unit: str, color: str, df_col: str):
    """Show a detail panel with 24h chart and stats for a sensor."""
    st.markdown(f'<div class="detail-panel">', unsafe_allow_html=True)

    col_title, col_close = st.columns([5, 1])
    with col_title:
        st.markdown(f"**{label} — Detail View**")
    with col_close:
        if st.button("✕ Close", key=f"close_{sensor_key}"):
            st.session_state["selected_sensor"] = None
            st.rerun()

    # Load 24h data
    df_24h = get_readings(
        start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24),
        limit=500
    )

    if not df_24h.empty and df_col in df_24h.columns:
        df_24h["timestamp"] = df_24h["timestamp"] + SWISS_OFFSET

        # Stats
        def fmt(val): return f"{float(val):.1f}" if val is not None else "—"
        series = df_24h[df_col].dropna()
        current_val = series.iloc[0] if not series.empty else None

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Current</div><div class="stat-value" style="color:{color}">{fmt(current_val)} {unit}</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Average</div><div class="stat-value">{fmt(series.mean())} {unit}</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Min</div><div class="stat-value">{fmt(series.min())} {unit}</div></div>', unsafe_allow_html=True)
        with s4:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Max</div><div class="stat-value">{fmt(series.max())} {unit}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Chart
        df_sorted = df_24h.sort_values("timestamp")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_sorted["timestamp"], y=df_sorted[df_col],
            mode="lines", line=dict(color=color, width=2),
            fill="tozeroy", fillcolor="rgba(128,128,128,0.08)",
            connectgaps=False, showlegend=False
        ))
        fig.update_layout(
            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=200,
            margin=dict(l=40, r=20, t=10, b=36),
            font=dict(family="Inter, sans-serif", size=11),
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", title="Last 24 hours"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", title=unit, autorange=True),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the last 24 hours.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── Indoor Sensors ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Indoor Sensor Readings</div>', unsafe_allow_html=True)

SENSORS = [
    ("temperature", "Temperature", "°C",  "#f97316", "temperature"),
    ("humidity",    "Humidity",    "%",   "#3b82f6", "humidity"),
    ("pressure",    "Pressure",    "hPa", "#a855f7", "pressure"),
    ("soil_raw",    "Soil Raw",    "ADC", "#22c55e", "soil_raw"),
    ("soil_moist",  "Soil Moist.", "%",   "#06b6d4", "soil_moisture"),
]

if latest:
    temp       = latest.get("temperature")
    hum        = latest.get("humidity")
    pres       = latest.get("pressure")
    soil_raw   = latest.get("soil_raw")
    soil_moist = latest.get("soil_moisture")

    c1, c2, c3, c4, c5 = st.columns(5)
    cols = [c1, c2, c3, c4, c5]
    labels = [
        ("Temperature", f"{temp:.1f} °C" if temp else "—",
         f"{round(temp - stats_24h['avg_temp'], 1):+.1f}°C vs 24h" if stats_24h.get('avg_temp') and temp else None),
        ("Humidity", f"{hum:.1f} %" if hum else "—",
         "Optimal" if hum and 40 <= hum <= 60 else ("Too dry" if hum and hum < 40 else "Too humid")),
        ("Pressure", f"{pres:.1f} hPa" if pres else "—",
         "High" if pres and pres > 1013 else ("Low" if pres and pres < 1000 else "Normal")),
        ("Soil Raw", f"{soil_raw}" if soil_raw else "—",
         "Wet" if soil_raw and soil_raw < 1500 else ("Moist" if soil_raw and soil_raw < 2000 else "Dry")),
        ("Soil Moisture", f"{soil_moist} %" if soil_moist else "—", None),
    ]

    for i, (col, (title, value, delta)) in enumerate(zip(cols, labels)):
        sensor_key = SENSORS[i][0]
        with col:
            st.metric(title, value, delta=delta)
            if st.button(f"Details", key=f"btn_{sensor_key}", use_container_width=True):
                if st.session_state["selected_sensor"] == sensor_key:
                    st.session_state["selected_sensor"] = None
                else:
                    st.session_state["selected_sensor"] = sensor_key
                st.rerun()

    # Show detail panel if a sensor is selected
    if st.session_state["selected_sensor"]:
        key = st.session_state["selected_sensor"]
        sensor_info = {s[0]: s for s in SENSORS}
        if key in sensor_info:
            _, label, unit, color, df_col = sensor_info[key]
            show_detail_panel(key, label, unit, color, df_col)
else:
    st.warning("No sensor data available.")

st.markdown("---")

# ── Previous Readings ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Previous Readings</div>', unsafe_allow_html=True)

recent_df = get_readings(start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=6), limit=11)
if not recent_df.empty:
    disp = recent_df.copy()
    if "timestamp" in disp.columns:
        disp["timestamp"] = (disp["timestamp"] + SWISS_OFFSET).dt.strftime("%Y-%m-%d %H:%M:%S")
    disp = disp.sort_values("timestamp", ascending=False).reset_index(drop=True).iloc[1:]
    cols_order = [c for c in ["timestamp","temperature","humidity","pressure","soil_raw","soil_moisture"] if c in disp.columns]
    st.dataframe(disp[cols_order].reset_index(drop=True), use_container_width=True, height=210, hide_index=True)
    st.caption("Last 10 readings — Swiss time (UTC+2)")
else:
    st.info("No recent readings available.")

st.markdown("---")

# ── Outdoor Weather ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Outdoor Weather — Lausanne</div>', unsafe_allow_html=True)

if weather:
    w1, w2, w3, w4, w5 = st.columns(5)
    with w1: st.metric(f"{weather['icon']} {weather['city']}", f"{weather['temp']} °C", delta=f"Feels {weather['feels_like']}°C")
    with w2: st.metric("Condition", weather["description"].capitalize())
    with w3: st.metric("Humidity", f"{weather['humidity']} %")
    with w4: st.metric("Wind", f"{weather['wind_speed']} m/s")
    with w5: st.metric("Sunrise / Sunset", f"{weather['sunrise']} / {weather['sunset']}")

    for alert in get_weather_alerts(weather):
        st.markdown(f'<div class="alert-box alert-{alert["type"]}">{alert["msg"]}</div>', unsafe_allow_html=True)

    st.markdown("<br>**5-Day Forecast**", unsafe_allow_html=True)
    forecast = get_forecast()
    if forecast:
        fcols = st.columns(len(forecast))
        for i, day in enumerate(forecast):
            with fcols[i]:
                st.markdown(f"""<div class="weather-card">
                    <div class="forecast-day">{day['date']}</div>
                    <div class="forecast-icon">{day['icon']}</div>
                    <div class="forecast-temp">{day['temp_max']}° / {day['temp_min']}°</div>
                    <div class="forecast-rain">{day['rain_prob']}% rain</div>
                    <div class="forecast-desc">{day['description']}</div>
                </div>""", unsafe_allow_html=True)
else:
    st.info("Weather data unavailable.")

st.markdown("---")

# ── Alerts ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Alerts</div>', unsafe_allow_html=True)

has_alert = False
if latest:
    hum  = latest.get("humidity")
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

# ── Historical Charts ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Historical Data — Last 7 Days</div>', unsafe_allow_html=True)

if not hourly_df.empty:
    full_range = pd.date_range(start=hourly_df["hour"].min(), end=hourly_df["hour"].max(), freq="h")
    full_grid  = pd.DataFrame({"hour": full_range})
    hourly_df["hour"] = pd.to_datetime(hourly_df["hour"]).dt.tz_localize(None)
    full_grid["hour"] = full_grid["hour"].dt.tz_localize(None)
    hdf = full_grid.merge(hourly_df, on="hour", how="left")

    CHART = dict(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=20, t=36, b=36), height=260,
        font=dict(family="Inter, sans-serif", size=11),
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", showline=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", showline=False, zeroline=False, autorange=True),
        title_font=dict(size=12, family="Inter, sans-serif"),
    )

    for col, title, unit, color in [
        ("avg_temperature", "Temperature (°C)", "°C",  "#f97316"),
        ("avg_humidity",    "Humidity (%)",     "%",   "#3b82f6"),
        ("avg_soil_raw",    "Soil Raw ADC",     "ADC", "#22c55e"),
        ("avg_pressure",    "Pressure (hPa)",   "hPa", "#a855f7"),
    ]:
        if hdf[col].dropna().empty:
            continue
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hdf["hour"], y=hdf[col], mode="lines",
            line=dict(color=color, width=2), connectgaps=False, showlegend=False))
        if col == "avg_humidity":
            fig.add_hrect(y0=40, y1=60, fillcolor="rgba(34,197,94,0.07)",
                          annotation_text="Optimal", annotation_position="top left",
                          annotation_font_size=10, line_width=0)
        fig.update_layout(title=title, yaxis_title=unit, xaxis_title="", **CHART)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No historical data available yet.")