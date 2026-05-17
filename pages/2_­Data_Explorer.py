import streamlit as st
import pandas as pd
import plotly.express as px
import io
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_stats, delete_readings

st.set_page_config(page_title="Data Explorer", page_icon="🔍", layout="wide")

st.markdown("## 🔍 Data Explorer")
st.caption("Filter, explore, and export your raw sensor data")
st.markdown("---")

# ── Date filters ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    start_date = st.date_input(
        "📅 Start date",
        value=pd.Timestamp.now() - pd.Timedelta(days=7)
    )
with col2:
    end_date = st.date_input(
        "📅 End date",
        value=pd.Timestamp.now()
    )
with col3:
    limit = st.number_input("Max rows", min_value=100, max_value=10000, value=1000, step=100)

start_dt = pd.Timestamp(start_date).tz_localize("UTC")
end_dt = pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).tz_localize("UTC")

# ── Load button ───────────────────────────────────────────────────────────────
if st.button("🔍 Load Data", type="primary"):
    with st.spinner("Fetching data from BigQuery..."):
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=limit)
        st.session_state["explorer_df"] = df
        st.session_state["explorer_loaded"] = True

if "explorer_df" not in st.session_state:
    st.info("👆 Select a date range and click **Load Data**")
    st.stop()

df = st.session_state["explorer_df"]

if df.empty:
    st.warning("No data found for the selected period.")
    st.stop()

# ── Stats summary ─────────────────────────────────────────────────────────────
st.markdown("### 📊 Period Summary")
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

# ── Column selector & sort ────────────────────────────────────────────────────
st.markdown("### 🗂️ Raw Data Table")

all_cols = list(df.columns)
selected_cols = st.multiselect(
    "Select columns to display",
    options=all_cols,
    default=all_cols
)

sort_col = st.selectbox("Sort by", options=all_cols, index=0)
sort_order = st.radio("Order", ["Descending ↓", "Ascending ↑"], horizontal=True)
ascending = sort_order == "Ascending ↑"

display_df = df[selected_cols].sort_values(
    by=sort_col, ascending=ascending
).reset_index(drop=True)

st.dataframe(display_df, use_container_width=True, height=400)
st.caption(f"Showing {len(display_df):,} rows")

st.markdown("---")

# ── Quick charts ──────────────────────────────────────────────────────────────
st.markdown("### 📈 Quick Visualization")

numeric_cols = df.select_dtypes(include="number").columns.tolist()
if numeric_cols and "timestamp" in df.columns:
    chart_col = st.selectbox("Select metric to plot", options=numeric_cols)
    df_sorted = df.sort_values("timestamp")

    CHART_THEME = dict(
        template="plotly_dark",
        height=300,
    )

    fig = px.line(
        df_sorted, x="timestamp", y=chart_col,
        title=f"{chart_col} over time",
        labels={"timestamp": "Time", chart_col: chart_col},
        **CHART_THEME
    )
    fig.update_traces(line_color="#4fc3f7")
    st.plotly_chart(fig, use_container_width=True)

    # Distribution histogram
    fig2 = px.histogram(
        df, x=chart_col, nbins=30,
        title=f"Distribution of {chart_col}",
        **CHART_THEME
    )
    fig2.update_traces(marker_color="#66bb6a")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("### 💾 Export Data")

ecol1, ecol2 = st.columns(2)

with ecol1:
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Export as CSV",
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
            df_export["timestamp"] = df_export["timestamp"].dt.tz_localize(None)
        df_export.to_excel(writer, index=False, sheet_name="Sensor Data")
        # Add stats sheet
        stats_df = df.describe()
        stats_df.to_excel(writer, sheet_name="Statistics")
    excel_buffer.seek(0)
    st.download_button(
        label="📊 Export as Excel",
        data=excel_buffer.getvalue(),
        file_name=f"sensor_data_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")

# ── Delete data (protected) ───────────────────────────────────────────────────
with st.expander("🗑️ Delete Data (use with caution)"):
    st.warning("⚠️ This will permanently delete data from BigQuery.")
    confirm_text = st.text_input("Type DELETE to confirm:")
    if st.button("Delete selected period", type="secondary"):
        if confirm_text == "DELETE":
            with st.spinner("Deleting..."):
                n = delete_readings(start_dt, end_dt)
                st.success(f"Deleted {n} rows from {start_date} to {end_date}")
                st.session_state.pop("explorer_df", None)
        else:
            st.error("Type DELETE to confirm deletion")
