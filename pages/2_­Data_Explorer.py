import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_stats, delete_readings

st.set_page_config(page_title="Data Explorer", page_icon="🔍", layout="wide")

SWISS_OFFSET = pd.Timedelta(hours=2)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    [data-testid="stSidebar"] { background: #0a0f1e !important; border-right: 1px solid #1a2744; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    div[data-testid="stMetric"] {
        border-radius: 14px; padding: 20px 18px;
        border: 1px solid rgba(128,128,128,0.2);
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
        font-size: 0.72rem !important; font-weight: 700 !important;
        text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.55;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.6rem !important; font-weight: 600 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    .section-title {
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.18em; margin-bottom: 16px; padding-bottom: 8px;
        border-bottom: 1px solid rgba(128,128,128,0.15); color: #1a56db;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## Data Explorer")
st.caption("Filter, explore, and export your raw sensor data")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date", value=pd.Timestamp.now() - pd.Timedelta(days=7))
    start_hour = st.slider("Start hour", 0, 23, 0)
with col2:
    end_date = st.date_input("End date", value=pd.Timestamp.now())
    end_hour = st.slider("End hour", 0, 23, 23)

col3, _ = st.columns([2, 1])
with col3:
    limit = st.number_input("Max rows", min_value=100, max_value=10000, value=1000, step=100)

start_dt = (pd.Timestamp(start_date).replace(hour=start_hour) - SWISS_OFFSET).tz_localize("UTC")
end_dt = (pd.Timestamp(end_date).replace(hour=end_hour, minute=59, second=59) - SWISS_OFFSET).tz_localize("UTC")

bcol1, bcol2 = st.columns([2, 1])
with bcol1:
    load = st.button("Load Data", type="primary")
with bcol2:
    refresh = st.button("Refresh")

if load or refresh:
    with st.spinner("Fetching data from BigQuery..."):
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=limit)
        if not df.empty and "timestamp" in df.columns:
            df["timestamp"] = (df["timestamp"] + SWISS_OFFSET).dt.tz_localize(None)
        st.session_state["explorer_df"] = df

if "explorer_df" not in st.session_state:
    st.info("Select a date range and click Load Data.")
    st.stop()

df = st.session_state["explorer_df"]

if df.empty:
    st.warning("No data found for the selected period.")
    st.stop()

st.markdown("---")
st.markdown('<div class="section-title">Period Summary</div>', unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Readings", f"{len(df):,}")
with col2:
    if "temperature" in df.columns:
        st.metric("Avg Temp", f"{df['temperature'].mean():.1f} °C")
with col3:
    if "humidity" in df.columns:
        st.metric("Avg Humidity", f"{df['humidity'].mean():.1f} %")
with col4:
    if "soil_raw" in df.columns:
        st.metric("Avg Soil Raw", f"{df['soil_raw'].mean():.0f}")
with col5:
    if "pressure" in df.columns:
        st.metric("Avg Pressure", f"{df['pressure'].mean():.1f} hPa")

st.markdown("---")
st.markdown('<div class="section-title">Raw Data Table</div>', unsafe_allow_html=True)

all_cols = list(df.columns)
selected_cols = st.multiselect("Select columns to display", options=all_cols, default=all_cols)
sort_col = st.selectbox("Sort by", options=all_cols, index=0)
sort_order = st.radio("Order", ["Descending ↓", "Ascending ↑"], horizontal=True)

display_df = df[selected_cols].sort_values(by=sort_col, ascending=(sort_order == "Ascending ↑")).reset_index(drop=True)
st.dataframe(display_df, use_container_width=True, height=400)
st.caption(f"{len(display_df):,} rows")

st.markdown("---")
st.markdown('<div class="section-title">Visualization</div>', unsafe_allow_html=True)

def insert_gaps(df_in, metrics):
    df_s = df_in.sort_values("timestamp").copy()
    if len(df_s) < 2:
        return df_s
    diffs = df_s["timestamp"].diff().dropna()
    median_interval = diffs.median()
    threshold = median_interval * 3
    rows = []
    for i in range(len(df_s)):
        rows.append(df_s.iloc[i])
        if i < len(df_s) - 1:
            gap = df_s["timestamp"].iloc[i+1] - df_s["timestamp"].iloc[i]
            if gap > threshold:
                nan_row = {col: np.nan for col in df_s.columns}
                nan_row["timestamp"] = df_s["timestamp"].iloc[i] + median_interval
                rows.append(pd.Series(nan_row))
    return pd.DataFrame(rows).reset_index(drop=True)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
if numeric_cols and "timestamp" in df.columns:
    selected_metrics = st.multiselect("Select metrics to plot", options=numeric_cols, default=[numeric_cols[0]])

    if selected_metrics:
        df_gapped = insert_gaps(df, selected_metrics)
        colors = ["#f97316", "#3b82f6", "#22c55e", "#a855f7", "#f59e0b"]

        CHART_THEME = dict(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=400,
            font=dict(family="Inter, sans-serif", size=11),
            xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)", showline=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.1)", showline=False, zeroline=False),
        )

        if len(selected_metrics) == 2:
            m1, m2 = selected_metrics[0], selected_metrics[1]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_gapped["timestamp"], y=df_gapped[m1],
                name=m1, line=dict(color=colors[0], width=2), connectgaps=False, yaxis="y1"))
            fig.add_trace(go.Scatter(x=df_gapped["timestamp"], y=df_gapped[m2],
                name=m2, line=dict(color=colors[1], width=2), connectgaps=False, yaxis="y2"))
            fig.update_layout(
                title=f"{m1} vs {m2}",
                xaxis=dict(title="Time", showgrid=True, gridcolor="rgba(128,128,128,0.1)"),
                yaxis=dict(title=m1, color=colors[0], showgrid=True, gridcolor="rgba(128,128,128,0.1)"),
                yaxis2=dict(title=m2, color=colors[1], overlaying="y", side="right"),
                template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=400, legend=dict(x=0.01, y=0.99)
            )
            st.caption("Dual Y-axis — each metric uses its own scale on left/right")
        else:
            fig = go.Figure()
            for i, metric in enumerate(selected_metrics):
                fig.add_trace(go.Scatter(x=df_gapped["timestamp"], y=df_gapped[metric],
                    name=metric, line=dict(color=colors[i % len(colors)], width=2), connectgaps=False))
            fig.update_layout(title="Sensor metrics over time", xaxis_title="Time", **CHART_THEME)

        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown('<div class="section-title">Export Data</div>', unsafe_allow_html=True)

ecol1, ecol2 = st.columns(2)
with ecol1:
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button("Export as CSV", data=csv_buffer.getvalue(),
        file_name=f"sensor_data_{start_date}_{end_date}.csv", mime="text/csv", type="primary")
with ecol2:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_export = df.copy()
        if "timestamp" in df_export.columns:
            try:
                df_export["timestamp"] = df_export["timestamp"].dt.tz_localize(None)
            except Exception:
                pass
        df_export.to_excel(writer, index=False, sheet_name="Sensor Data")
        df.describe().to_excel(writer, sheet_name="Statistics")
    excel_buffer.seek(0)
    st.download_button("Export as Excel", data=excel_buffer.getvalue(),
        file_name=f"sensor_data_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")
with st.expander("Delete Data (use with caution)"):
    st.warning("This will permanently delete data from BigQuery.")
    confirm_text = st.text_input("Type DELETE to confirm:")
    if st.button("Delete selected period", type="secondary"):
        if confirm_text == "DELETE":
            with st.spinner("Deleting..."):
                n = delete_readings(start_dt, end_dt)
                st.success(f"Deleted {n} rows from {start_date} to {end_date}")
                st.session_state.pop("explorer_df", None)
        else:
            st.error("Type DELETE to confirm deletion")