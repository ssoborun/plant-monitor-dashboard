import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.bigquery_client import get_readings
from utils.ai_helpers import analyze_data_with_ai, text_to_speech, generate_sensor_summary
from utils.weather import get_current_weather

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .chat-user {
        background: linear-gradient(135deg, #1e3a5f, #0f2d4a);
        border-radius: 12px 12px 0 12px;
        padding: 12px 16px;
        margin: 8px 0;
        border-left: 3px solid #4fc3f7;
    }
    .chat-ai {
        background: linear-gradient(135deg, #1a2e1a, #0f2d0f);
        border-radius: 12px 12px 12px 0;
        padding: 12px 16px;
        margin: 8px 0;
        border-left: 3px solid #66bb6a;
    }
    .chat-label-user { color: #4fc3f7; font-size: 0.75rem; font-weight: 600; margin-bottom: 4px; }
    .chat-label-ai { color: #66bb6a; font-size: 0.75rem; font-weight: 600; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🤖 AI Assistant")
st.caption("Ask questions about your sensor data — get AI-powered answers, with optional voice output")
st.markdown("---")

# ── Data period selector ──────────────────────────────────────────────────────
st.markdown("### 📅 Select Data Period for Analysis")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From", value=pd.Timestamp.now() - pd.Timedelta(days=7))
with col2:
    end_date = st.date_input("To", value=pd.Timestamp.now())

if st.button("📂 Load Data for Analysis", type="primary"):
    with st.spinner("Loading data from BigQuery..."):
        start_dt = pd.Timestamp(start_date).tz_localize("UTC")
        end_dt = pd.Timestamp(end_date).replace(hour=23, minute=59, second=59).tz_localize("UTC")
        df = get_readings(start_date=start_dt, end_date=end_dt, limit=2000)
        st.session_state["ai_df"] = df
        if not df.empty:
            st.success(f"✅ Loaded {len(df):,} readings from {start_date} to {end_date}")
        else:
            st.warning("No data found for this period.")

if "ai_df" not in st.session_state:
    st.info("👆 Load data first, then ask your question.")
    st.stop()

df = st.session_state["ai_df"]
st.caption(f"📊 Working with **{len(df):,} readings** | {start_date} → {end_date}")

st.markdown("---")

# ── Chat interface ────────────────────────────────────────────────────────────
st.markdown("### 💬 Ask a Question")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "current_question" not in st.session_state:
    st.session_state["current_question"] = ""

# Quick questions
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
            # Analyser directement
            with st.spinner("Analyzing data..."):
                answer = analyze_data_with_ai(df, q)
            st.session_state["chat_history"].append({
                "question": q,
                "answer": answer
            })
            st.rerun()

user_input = st.text_area(
    "Or type your question:",
    value=st.session_state["current_question"],
    placeholder="e.g. What was the humidity trend this week?",
    height=80
)

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ── Speech to Text ────────────────────────────────────────────────────────────
with st.expander("🎤 Or use voice input (Speech-to-Text)"):
    st.info("Record your question using your device's microphone, then upload the audio file.")
    audio_file = st.file_uploader("Upload audio file (.wav, .mp3, .m4a)", type=["wav", "mp3", "m4a", "webm"])
    if audio_file and st.button("🎤 Transcribe Audio"):
        from utils.ai_helpers import speech_to_text
        with st.spinner("Transcribing..."):
            text = speech_to_text(audio_file.read())
            if text:
                st.success(f"Transcribed: **{text}**")
                st.session_state["pending_question"] = text
                st.rerun()
            else:
                st.error("Transcription failed. Check your OpenAI API key.")

# ── Send question ─────────────────────────────────────────────────────────────
col_ask, col_clear = st.columns([3, 1])
with col_ask:
    send = st.button("🚀 Ask AI", type="primary", disabled=not user_input.strip())
with col_clear:
    if st.button("🗑️ Clear chat"):
        st.session_state["chat_history"] = []
        st.rerun()

if send and user_input.strip():
    with st.spinner("Analyzing data..."):
        answer = analyze_data_with_ai(df, user_input.strip())

    st.session_state["chat_history"].append({
        "question": user_input.strip(),
        "answer": answer
    })

# ── Display chat history ──────────────────────────────────────────────────────
if st.session_state["chat_history"]:
    st.markdown("---")
    st.markdown("### 🗨️ Conversation")

    for i, exchange in enumerate(reversed(st.session_state["chat_history"])):
        st.markdown(f"""
        <div class="chat-user">
            <div class="chat-label-user">👤 YOU</div>
            {exchange['question']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="chat-ai">
            <div class="chat-label-ai">🤖 AI ASSISTANT</div>
            {exchange['answer']}
        </div>
        """, unsafe_allow_html=True)

        # TTS button for each answer
        tts_col, _ = st.columns([1, 4])
        with tts_col:
            if st.button(f"🔊 Read aloud", key=f"tts_{i}"):
                with st.spinner("Generating audio..."):
                    audio_bytes = text_to_speech(exchange["answer"])
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                    else:
                        st.error("TTS failed. Check your OpenAI API key.")

        st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")

# ── Auto-summary with TTS ─────────────────────────────────────────────────────
st.markdown("### 📢 Auto Summary (Text-to-Speech)")
st.caption("Generate a spoken summary of current conditions")

if st.button("🔊 Generate & Read Summary"):
    from utils.bigquery_client import get_latest_reading
    latest = get_latest_reading()
    weather = get_current_weather()

    summary_text = generate_sensor_summary(latest, weather)
    st.info(f"**Summary:** {summary_text}")

    with st.spinner("Generating audio..."):
        audio_bytes = text_to_speech(summary_text)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
            st.success("✅ Audio ready — press play above")
        else:
            st.error("TTS not available. Check your OpenAI API key.")
