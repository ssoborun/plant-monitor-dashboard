# 🌱 Plant & Environment Monitor

> IoT Experimentation Platform — M5Stack Core2 + Google BigQuery + Streamlit

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)](https://streamlit.io)
[![BigQuery](https://img.shields.io/badge/Google-BigQuery-blue)](https://cloud.google.com/bigquery)

---

## 📌 Project Overview

This project is an IoT experimentation platform for plant and environmental monitoring. Instead of providing a fixed prediction algorithm, it gives users the tools to **collect, explore, visualize, and analyze** their own sensor data.

The system collects data from an **M5Stack Core2** device equipped with sensors, stores it in **Google BigQuery**, and displays it in a **Streamlit dashboard** accessible from anywhere.

---

## 🏗️ Architecture

```
M5Stack Core2 (sensors)
        │
        ▼
Google BigQuery (cloud storage)
        │
        ▼
Streamlit Dashboard (web interface)
        │
        ├── Live sensor readings
        ├── Outdoor weather (OpenWeatherMap)
        ├── Data Explorer (filter, export)
        ├── AI Assistant (Gemini)
        └── Alerts & Thresholds
```

---

## 🔧 Hardware

- **M5Stack Core2** — main IoT device
- **ENV III Sensor** — temperature, humidity, pressure
- **Soil Moisture Sensor** — raw ADC soil readings

---

## 📊 Dashboard Pages

| Page | Description |
|------|-------------|
| 🏠 Home | Platform overview |
| 📊 Dashboard | Live sensor data + outdoor weather + 7-day charts |
| 🔍 Data Explorer | Filter by date, sort, export CSV/Excel |
| 🤖 AI Assistant | Ask questions about your data using Gemini AI |
| ⚡ Alerts | Configurable thresholds and violation history |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/ssoborun/plant-monitor-dashboard.git
cd plant-monitor-dashboard
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Fill in your API keys in .env
```

### 4. Add your Google Cloud service account
- Download your service account JSON from Google Cloud Console
- Rename it to `service_account.json`
- Place it in the project root

### 5. Run the dashboard
```bash
streamlit run app.py
```

---

## 🔑 Required API Keys

| Service | Purpose | Link |
|---------|---------|------|
| Google Cloud Service Account | Read BigQuery data | [console.cloud.google.com](https://console.cloud.google.com) |
| OpenWeatherMap | Outdoor weather data | [openweathermap.org](https://openweathermap.org) |
| Google Gemini | AI data analysis | [aistudio.google.com](https://aistudio.google.com) |

---

## 🗄️ BigQuery Schema

**Dataset:** `plant_monitoring`  
**Table:** `sensor_readings`

| Column | Type | Description |
|--------|------|-------------|
| timestamp | TIMESTAMP | Reading time (UTC) |
| device_id | STRING | M5Stack device ID |
| temperature | FLOAT | °C (ENV III sensor) |
| humidity | FLOAT | % (ENV III sensor) |
| pressure | FLOAT | hPa (ENV III sensor) |
| soil_raw | INTEGER | Raw ADC value |
| soil_moisture | STRING | Categorical label |

---

## 📁 Project Structure

```
dashboard/
├── app.py                      # Main entry point
├── pages/
│   ├── 1_Dashboard.py          # Live data + weather + charts
│   ├── 2_Data_Explorer.py      # Filter, sort, export
│   ├── 3_AI_Assistant.py       # Gemini AI chat
│   └── 4_Alerts.py             # Threshold monitoring
├── utils/
│   ├── bigquery_client.py      # BigQuery queries
│   ├── weather.py              # OpenWeatherMap API
│   └── ai_helpers.py           # Gemini AI integration
├── .env.example                # Environment template
├── .gitignore                  # Excludes secrets
└── requirements.txt            # Python dependencies
```

---

## 👥 Team

| Name | Role |
|------|------|
| Satchyn Soborun | Streamlit Dashboard, AI integration, Cloud setup |
| [Colleague Name] | M5Stack firmware, BigQuery setup, Data collection |

---

## 🎥 Demo Video

[Link to YouTube demo — coming soon]

---

## 📦 Deployment

To deploy on Streamlit Cloud:
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets in Streamlit Cloud settings

---

## 📝 License

Academic project — UNIL 2026
