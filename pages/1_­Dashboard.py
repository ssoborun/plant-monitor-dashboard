import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_latest_reading, get_hourly_averages, get_stats, get_readings
from utils.weather import get_current_weather, get_forecast, get_weather_alerts

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

SWISS_OFFSET = pd.Timedelta(hours=2)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e3a5f, #0f2d4a);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #2a5a8f;
    }
    .weather-card {
        background: linear-gradient(135deg, #0f3460, #16213e);
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid #2a5a8f;
        margin: 4px;
        text-align: center;
    }
    .forecast-day { font-weight: 600; color: #90caf9; font-size: 0.9rem; }
    .forecast-icon { font-size: 1.8rem; margin: 4px 0; }
    .forecast-temp { color: #fff; font-size: 0.9rem; }
    .forecast-rain { color: #64b5f6; font-size: 0.8rem; }
    .section-title { color: #4fc3f7; font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📊 Live Dashboard")

# ── Refresh button ──────────────────────────────────────────────────────────
col_refresh, col_time = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ── Fetch data ───────────────────────────────────────────────────────────────
latest = get_latest_reading()
weather = get_current_weather()
hourly_df = get_hourly_averages(days=7)
stats_24h = get_stats(
    start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24)
)

with col_time:
    if latest and latest.get("timestamp"):
        ts = pd.Timestamp(latest["timestamp"]) + SWISS_OFFSET
        st.caption(f"Last reading: **{ts.strftime('%Y-%m-%d %H:%M:%S')} (Swiss time)**")

st.markdown("---")

# ── SECTION 1: Indoor Sensors ────────────────────────────────────────────────
st.markdown('<div class="section-title">🏠 Indoor Sensor Readings</div>', unsafe_allow_html=True)

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
        st.metric(
            "🌡️ Temperature",
            f"{temp:.1f} °C" if temp else "—",
            delta=f"{delta_temp:+.1f}°C vs 24h avg" if delta_temp else None,
            help="Current indoor temperature"
        )
    with col2:
        hum_status = "✅ Optimal" if hum and 40 <= hum <= 60 else ("⬇️ Too dry" if hum and hum < 40 else "⬆️ Too humid")
        st.metric(
            "💧 Humidity",
            f"{hum:.1f} %" if hum else "—",
            delta=hum_status,
            help="Optimal range: 40–60%"
        )
    with col3:
        pres_status = None
        if pres:
            if pres > 1013:
                pres_status = "☀️ High pressure"
            elif pres < 1000:
                pres_status = "🌧️ Low pressure"
            else:
                pres_status = "🌤️ Normal"
        st.metric(
            "🔵 Pressure",
            f"{pres:.1f} hPa" if pres else "—",
            delta=pres_status,
            help="Atmospheric pressure"
        )
    with col4:
        soil_comment = None
        if soil_raw:
            if soil_raw < 1500:
                soil_comment = "💧 Wet soil"
            elif soil_raw < 2000:
                soil_comment = "✅ Moist"
            else:
                soil_comment = "🏜️ Dry soil"
        st.metric(
            "🌱 Soil Raw",
            f"{soil_raw}" if soil_raw else "—",
            delta=soil_comment,
            help="Raw ADC value from soil sensor"
        )
    with col5:
        st.metric(
            "💦 Soil Moisture",
            f"{soil_moist} %" if soil_moist else "—",
            help="Calibrated soil moisture percentage"
        )
else:
    st.warning("No sensor data available. Check your BigQuery connection.")

st.markdown("---")

# ── SECTION 2: Last Sensor Readings ─────────────────────────────────────────
st.markdown('<div class="section-title">📋 Last Sensor Readings</div>', unsafe_allow_html=True)

recent_df = get_readings(
    start_date=pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=6),
    limit=10
)

if not recent_df.empty:
    display_recent = recent_df.copy()
    if "timestamp" in display_recent.columns:
        display_recent["timestamp"] = (display_recent["timestamp"] + SWISS_OFFSET).dt.strftime("%Y-%m-%d %H:%M:%S")
    cols_order = ["timestamp", "temperature", "humidity", "pressure", "soil_raw", "soil_moisture"]
    cols_order = [c for c in cols_order if c in display_recent.columns]
    st.dataframe(
        display_recent[cols_order].sort_values("timestamp", ascending=False).reset_index(drop=True),
        use_container_width=True,
        height=200,
        hide_index=True
    )
    st.caption("Last 10 readings — times in Swiss time (UTC+2)")
else:
    st.info("No recent readings available.")

st.markdown("---")

# ── SECTION 3: Outdoor Weather ───────────────────────────────────────────────
st.markdown('<div class="section-title">🌍 Outdoor Weather</div>', unsafe_allow_html=True)

if weather:
    wcol1, wcol2, wcol3, wcol4, wcol5 = st.columns(5)
    with wcol1:
        st.metric(f"{weather['icon']} {weather['city']}", f"{weather['temp']} °C",
                  delta=f"Feels {weather['feels_like']}°C")
    with wcol2:
        st.metric("🌤️ Condition", weather["description"])
    with wcol3:
        st.metric("💧 Ext. Humidity", f"{weather['humidity']} %")
    with wcol4:
        st.metric("💨 Wind", f"{weather['wind_speed']} m/s")
    with wcol5:
        st.metric("🌅 Sunrise / Sunset", f"{weather['sunrise']} / {weather['sunset']}")

    alerts = get_weather_alerts(weather)
    for alert in alerts:
        css_class = f"alert-{alert['type']}"
        st.markdown(f'<div class="alert-box {css_class}">{alert["msg"]}</div>', unsafe_allow_html=True)

    st.markdown("**5-Day Forecast:**")
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
                    <div class="forecast-rain">🌧 {day['rain_prob']}%</div>
                    <div style="color:#b0bec5;font-size:0.75rem">{day['description']}</div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("Weather data unavailable. Add your OpenWeatherMap API key to .env")

st.markdown("---")

# ── SECTION 4: Smart Alerts ──────────────────────────────────────────────────
st.markdown('<div class="section-title">⚡ Smart Alerts</div>', unsafe_allow_html=True)

has_alert = False
if latest:
    hum = latest.get("humidity")
    temp = latest.get("temperature")
    soil_raw = latest.get("soil_raw")

    if hum and hum < 40:
        st.markdown('<div class="alert-box alert-warning">⚠️ Indoor humidity below 40% — consider using a humidifier</div>', unsafe_allow_html=True)
        has_alert = True
    if hum and hum > 70:
        st.markdown('<div class="alert-box alert-warning">⚠️ Indoor humidity above 70% — check for condensation or mold risk</div>', unsafe_allow_html=True)
        has_alert = True
    if temp and temp > 28:
        st.markdown('<div class="alert-box alert-danger">🔴 High indoor temperature: {:.1f}°C</div>'.format(temp), unsafe_allow_html=True)
        has_alert = True
    if temp and temp < 15:
        st.markdown('<div class="alert-box alert-warning">🥶 Low indoor temperature: {:.1f}°C</div>'.format(temp), unsafe_allow_html=True)
        has_alert = True

if not has_alert:
    st.markdown('<div class="alert-box alert-success">✅ All conditions normal</div>', unsafe_allow_html=True)

st.markdown("---")

# ── SECTION 5: Charts ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📈 Historical Charts (Last 7 Days)</div>', unsafe_allow_html=True)

if not hourly_df.empty:
    # Convert to Swiss time
    hourly_df["hour"] = hourly_df["hour"] + SWISS_OFFSET

    tab1, tab2, tab3, tab4 = st.tabs(["🌡️ Temperature", "💧 Humidity", "🌱 Soil Raw", "🔵 Pressure"])

    CHART_THEME = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=30, b=40),
        height=300,
    )

    with tab1:
        fig = go.Figure()
        df_valid = hourly_df.dropna(subset=["avg_temperature"])
        fig.add_trace(go.Scatter(
            x=df_valid["hour"], y=df_valid["avg_temperature"],
            mode="lines+markers", name="Temp °C",
            line=dict(color="#ff7043", width=2),
            fill="tozeroy", fillcolor="rgba(255,112,67,0.1)",
            connectgaps=False
        ))
        fig.update_layout(title="Temperature (°C)", xaxis_title="Time (Swiss)", yaxis_title="°C", **CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = go.Figure()
        df_valid = hourly_df.dropna(subset=["avg_humidity"])
        fig.add_trace(go.Scatter(
            x=df_valid["hour"], y=df_valid["avg_humidity"],
            mode="lines+markers", name="Humidity %",
            line=dict(color="#29b6f6", width=2),
            fill="tozeroy", fillcolor="rgba(41,182,246,0.1)",
            connectgaps=False
        ))
        fig.add_hrect(y0=40, y1=60, fillcolor="rgba(76,175,80,0.1)",
                      annotation_text="Optimal zone", annotation_position="top left",
                      line_width=0)
        fig.update_layout(title="Humidity (%)", xaxis_title="Time (Swiss)", yaxis_title="%", **CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = go.Figure()
        df_valid = hourly_df.dropna(subset=["avg_soil_raw"])
        fig.add_trace(go.Scatter(
            x=df_valid["hour"], y=df_valid["avg_soil_raw"],
            mode="lines+markers", name="Soil Raw ADC",
            line=dict(color="#66bb6a", width=2),
            fill="tozeroy", fillcolor="rgba(102,187,106,0.1)",
            connectgaps=False
        ))
        fig.update_layout(title="Soil Moisture Raw ADC Value", xaxis_title="Time (Swiss)", yaxis_title="ADC", **CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        fig = go.Figure()
        df_valid = hourly_df.dropna(subset=["avg_pressure"])
        fig.add_trace(go.Scatter(
            x=df_valid["hour"], y=df_valid["avg_pressure"],
            mode="lines+markers", name="Pressure hPa",
            line=dict(color="#ab47bc", width=2),
            fill="tozeroy", fillcolor="rgba(171,71,188,0.1)",
            connectgaps=False
        ))
        fig.update_layout(title="Atmospheric Pressure (hPa)", xaxis_title="Time (Swiss)", yaxis_title="hPa", **CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No historical data available yet.")