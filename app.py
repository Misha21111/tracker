import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
from google import genai
from google.genai import types

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except ImportError:
    LOCAL_TZ = timezone(timedelta(hours=2))

st.set_page_config(page_title="Мій Фітнес", layout="centered")

# --- НАЛАШТУВАННЯ ФАЙЛІВ ---
user_profile = st.sidebar.selectbox("👤 Оберіть профіль:", ["Я", "Дружина"])
profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"
IMAGE_URL = "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"

st.markdown(f"""
    <style>
    .stApp {{ background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), url("{IMAGE_URL}"); background-size: cover; background-position: center; background-attachment: fixed; }}
    #MainMenu, footer, header {{visibility: hidden;}}
    .food-box {{ background-color: rgba(20, 20, 20, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 12px; color: white; }}
    </style>
""", unsafe_allow_html=True)

# --- ФУНКЦІЇ ---
def load_settings():
    default = {"calories": 2000, "protein": 160, "fat": 70, "carbs": 180, "bmr_daily": 1850, "start_weight": 90.0, "include_exercise_in_deficit": False}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f: return {**default, **json.load(f)}
        except: pass
    return default

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f: json.dump(s, f)

def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    return pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

# Розрахунок поточної ваги
def calculate_current_weight(df, settings):
    start_weight = settings.get("start_weight", 90.0)
    if df.empty: return start_weight
    
    bmr = settings.get("bmr_daily", 1850)
    total_deficit = 0
    for d in df["Дата"].unique():
        day_df = df[df["Дата"] == d]
        consumed = day_df["Спожито"].sum()
        explicit_burned = day_df["Спалено"].sum()
        day_burned = (explicit_burned + bmr) if settings.get("include_exercise_in_deficit") else bmr
        total_deficit += (day_burned - consumed)
        
    return round(start_weight - (total_deficit / 7700), 1)

# --- СТАН ---
if "open_camera" not in st.session_state: st.session_state["open_camera"] = False
if "edit_mode" not in st.session_state: st.session_state["edit_mode"] = False

user_settings = load_settings()
df_data = load_data()
current_weight = calculate_current_weight(df_data, user_settings)

# --- ІНТЕРФЕЙС ---
st.title(f"🏋️ Фітнес: {user_profile}")
st.metric("Вага (розрахункова)", f"{current_weight} кг")

with st.container(border=True):
    user_input = st.text_input("📥 Що з'їв / тренування:")
    if st.button("✅ Записати"):
        # Тут логіка запису в Excel
        st.success("Записано!")
        st.rerun()

# Налаштування
if st.button("⚙️ Налаштування"): st.session_state["edit_mode"] = not st.session_state["edit_mode"]

if st.session_state["edit_mode"]:
    s_weight = st.number_input("Початкова вага (кг)", value=float(user_settings["start_weight"]))
    if st.button("💾 Зберегти"):
        user_settings["start_weight"] = s_weight
        save_settings(user_settings)
        st.rerun()
