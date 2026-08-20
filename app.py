import pandas as pd
import streamlit as st
import plotly.express as px
import json
import os
from datetime import datetime

# --- НАЛАШТУВАННЯ ---
st.set_page_config(layout="centered")
EXCEL_FILE = "fitness_data.xlsx"
SETTINGS_FILE = "settings.json"

def load_settings():
    default = {"bmr": 1850, "start_weight": 90.0}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f: return json.load(f)
    return default

def calculate_weight(df, settings):
    # Розрахунок дефіциту за всі дні
    total_deficit = 0
    for _, row in df.iterrows():
        total_deficit += (settings["bmr"] - row["Спожито"] + row["Спалено"])
    return round(settings["start_weight"] - (total_deficit / 7700), 1)

# --- ЗАВАНТАЖЕННЯ ---
df = pd.read_excel(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else pd.DataFrame(columns=["Дата", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])
settings = load_settings()
current_weight = calculate_weight(df, settings)

# --- UI ---
st.title("🏋️ Фітнес")
st.metric("Поточна вага (розрахункова)", f"{current_weight} кг")

# Відображення графіків (як було)
if not df.empty:
    col1, col2 = st.columns(2)
    # Приклад графіку дефіциту
    fig = px.bar(df, x="Дата", y="Спожито", title="Споживання калорій")
    st.plotly_chart(fig)

# Введення даних
with st.expander("➕ Додати запис"):
    cal = st.number_input("Калорії")
    if st.button("Зберегти"):
        # логіка запису...
        st.rerun()

# Налаштування
with st.expander("⚙️ Налаштування"):
    start_w = st.number_input("Початкова вага", value=float(settings["start_weight"]))
    if st.button("Зберегти налаштування"):
        settings["start_weight"] = start_w
        with open(SETTINGS_FILE, "w") as f: json.dump(settings, f)
        st.rerun()
