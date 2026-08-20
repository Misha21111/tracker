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

# --- ПРОФІЛЬ ---
user_profile = st.sidebar.selectbox("👤 Оберіть профіль:", ["Я", "Дружина"])
profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"
IMAGE_URL = "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"

st.markdown(f"""<style>.stApp {{ background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), url("{IMAGE_URL}"); background-size: cover; background-position: center; background-attachment: fixed; }}</style>""", unsafe_allow_html=True)

# --- ФУНКЦІЇ ---
def load_settings():
    default = {
        "calories": 2000, "protein": 160, "fat": 70, "carbs": 180, "bmr_daily": 1850,
        "activity_level": "Сидячий", "include_exercise_in_deficit": False, "start_weight": 90.0
    }
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

def calculate_current_weight(df, user_settings):
    if df.empty: return user_settings.get("start_weight", 90.0)
    
    # Розрахунок загального дефіциту за всі дні
    bmr_daily = user_settings.get("bmr_daily", 1850)
    total_deficit = 0
    
    unique_dates = df["Дата"].unique()
    for d in unique_dates:
        day_df = df[df["Дата"] == d]
        consumed = day_df["Спожито"].sum()
        explicit_burned = day_df["Спалено"].sum()
        
        # Визначаємо, як рахувати спалені для кожного дня (як у налаштуваннях)
        if user_settings.get("include_exercise_in_deficit", False):
            day_burned = explicit_burned + bmr_daily
        else:
            day_burned = bmr_daily
            
        total_deficit += (day_burned - consumed)
        
    # Формула: 7700 ккал = 1 кг
    weight_loss = total_deficit / 7700
    return round(user_settings.get("start_weight", 90.0) - weight_loss, 1)

# --- ІНІЦІАЛІЗАЦІЯ ---
user_settings = load_settings()
df_data = load_data()
current_calc_weight = calculate_current_weight(df_data, user_settings)

st.title(f"🏋️ Фітнес: {user_profile}")
# ... (Код для інтерфейсу) ...
