import streamlit as st
import pandas as pd
import plotly.express as px
import io
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_stats, delete_readings

st.set_page_config(page_title="Data Explorer", page_icon="🔍", layout="wide")

SWISS_OFFSET = pd.Timedelta(hours=2)

st.markdown("## Data Explorer")
st.caption("Filter, explore, and export your raw sensor data")
st.markdown("---")

# ── Filters ───────────────────────────────────────────────────────────────────
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

# ── Buttons ───────────────────────────────────────────────────────────────────
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

# ── Period Summary ────────────────────────────────────────────────────────────
st.markdown("### Period Summary")
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

# ── Data Table ────────────────────────────────────────────────────────────────
st.markdown("### Raw Data Table")

all_cols = list(df.columns)
selected_cols = st.multiselect("Select columns to display", options=all_cols, default=all_cols)
sort_col = st.selectbox("Sort by", options=all_cols, index=0)
sort_order = st.radio("Order", ["Descending ↓", "Ascending ↑"], horizontal=True)

display_df = df[selected_cols].sort_values(by=sort_col, ascending=(sort_order == "Ascending ↑")).reset_index(drop=True)
st.dataframe(display_df, use_container_width=True, height=400)
st.caption(f"{len(display_df):,} rows")

st.markdown("---")

# ── Visualization ─────────────────────────────────────────────────────────────
st.markdown("### Visualization")

numeric_cols = df.select_dtypes(include="number").columns.tolist()
if numeric_cols and "timestamp" in df.columns:
    selected_metrics = st.multiselect(
        "Select metrics to plot",
        options=numeric_cols,
        default=[numeric_cols[0]]
    )
    if selected_metrics:
        df_sorted = df.sort_values("timestamp").dropna(subset=selected_metrics, how="all")
        df_melted = df_sorted.melt(id_vars="timestamp", value_vars=selected_metrics,
                                   var_name="Metric", value_name="Value")
        fig = px.line(df_melted, x="timestamp", y="Value", color="Metric",
                      title="Sensor metrics over time",
                      labels={"timestamp": "Time", "Value": ""},
                      template="plotly_dark", height=350)
        fig.update_traces(connectgaps=False)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("### Export Data")

ecol1, ecol2 = st.columns(2)

with ecol1:
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Export as CSV",
        data=csv_buffer.getvalue(),
        file_name=f"sensor_data_{start_date}_{end_date}.csv",
        mime="text/csv",
        type="primary"
    )

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
    st.download_button(
        label="Export as Excel",
        data=excel_buffer.getvalue(),
        file_name=f"sensor_data_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")

# ── Delete ────────────────────────────────────────────────────────────────────
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