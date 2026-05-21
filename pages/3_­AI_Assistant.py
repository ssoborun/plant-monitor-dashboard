import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings, get_latest_reading
from utils.ai_helpers import analyze_data_with_ai, text_to_speech, generate_sensor_summary
from utils.weather import get_current_weather

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

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
    .chat-user {
        border-radius: 12px 12px 0 12px; padding: 12px 16px; margin: 8px 0;
        border: 1px solid rgba(59,130,246,0.3); background: rgba(59,130,246,0.05);
    }
    .chat-ai {
        border-radius: 12px 12px 12px 0; padding: 12px 16px; margin: 8px 0;
        border: 1px solid rgba(34,197,94,0.3); background: rgba(34,197,94,0.05);
    }
    .chat-label-user { color: #3b82f6; font-size: 0.72rem; font-weight: 700; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.08em; }
    .chat-label-ai   { color: #22c55e; font-size: 0.72rem; font-weight: 700; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.08em; }
</style>
""", unsafe_allow_html=True)

st.markdown("## AI Assistant")
st.caption("Ask questions about your sensor data — get AI-powered answers")
st.markdown("---")

st.markdown('<div class="section-title">Select Data Period for Analysis</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From", value=pd.Timestamp.now() - pd.Timedelta(days=7))
with col2:
    end_date = st.date_input("To", value=pd.Timestamp.now())

if st.button("Load Data for Analysis", type="primary"):
    with st.spinner("Loading data from BigQuery..."):
        start_dt = pd.Timestamp(start_date).tz_localize("UTC")
        end_dt = pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).tz_localize("UTC")
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=2000)
        st.session_state["ai_df"] = df
        if not df.empty:
            st.success(f"Loaded {len(df):,} readings from {start_date} to {end_date}")
        else:
            st.warning("No data found for this period.")

if "ai_df" not in st.session_state:
    st.info("Load data first, then ask your question.")
    st.stop()

df = st.session_state["ai_df"]
st.caption(f"Working with **{len(df):,} readings** — {start_date} → {end_date}")

st.markdown("---")
st.markdown('<div class="section-title">Ask a Question</div>', unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "current_question" not in st.session_state:
    st.session_state["current_question"] = ""

st.markdown("**Quick questions:**")
quick_qs = [
    "What was the average temperature for this period?",
    "Did humidity drop below 40% at any point?",
    "What trend do you see in the soil moisture data?",
    "Were there any anomalies in the sensor data?",
    "Compare temperature and humidity patterns",
]
cols = st.columns(len(quick_qs))
for i, q in enumerate(quick_qs):
    with cols[i]:
        if st.button(q[:30] + "...", key=f"quick_{i}", help=q):
            st.session_state["current_question"] = q
            with st.spinner("Analyzing data..."):
                answer = analyze_data_with_ai(df, q)
            st.session_state["chat_history"].append({"question": q, "answer": answer})
            st.rerun()

user_input = st.text_area("Or type your question:", value=st.session_state["current_question"],
    placeholder="e.g. What was the humidity trend this week?", height=80)

col_ask, col_clear = st.columns([3, 1])
with col_ask:
    send = st.button("Ask AI", type="primary", disabled=not user_input.strip())
with col_clear:
    if st.button("Clear chat"):
        st.session_state["chat_history"] = []
        st.rerun()

if send and user_input.strip():
    with st.spinner("Analyzing data..."):
        answer = analyze_data_with_ai(df, user_input.strip())
    st.session_state["chat_history"].append({"question": user_input.strip(), "answer": answer})

if st.session_state["chat_history"]:
    st.markdown("---")
    st.markdown('<div class="section-title">Conversation</div>', unsafe_allow_html=True)
    for i, exchange in enumerate(reversed(st.session_state["chat_history"])):
        st.markdown(f'<div class="chat-user"><div class="chat-label-user">You</div>{exchange["question"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-ai"><div class="chat-label-ai">AI Assistant</div>{exchange["answer"]}</div>', unsafe_allow_html=True)
        tts_col, _ = st.columns([1, 4])
        with tts_col:
            if st.button("Read aloud", key=f"tts_{i}"):
                with st.spinner("Generating audio..."):
                    audio_bytes = text_to_speech(exchange["answer"])
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                    else:
                        st.error("TTS failed.")
        st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div class="section-title">Auto Summary</div>', unsafe_allow_html=True)

if st.button("Generate & Read Summary"):
    latest = get_latest_reading()
    weather = get_current_weather()
    summary_text = generate_sensor_summary(latest, weather)
    st.info(f"**Summary:** {summary_text}")
    with st.spinner("Generating audio..."):
        audio_bytes = text_to_speech(summary_text)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
        else:
            st.error("TTS not available.")