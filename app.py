import pandas as pd
import streamlit as st
from datetime import datetime
import json
import os
from google import genai
from google.genai import types

st.set_page_config(page_title="Мій Фітнес", layout="centered")

# Картинка через Postimages
IMAGE_URL = "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), url("{IMAGE_URL}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px 14px;
        color: white;
    }}
    .food-box, .advice-box {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px 16px;
        color: #ffffff;
        margin-top: 10px;
    }}
    .advice-box {{
        border-left: 4px solid #36A2EB;
    }}
    .donut-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 15px 0;
    }}
    .donut-ring {{
        width: 190px;
        height: 190px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow: 0 0 15px rgba(0,0,0,0.8);
    }}
    .donut-hole {{
        width: 125px;
        height: 125px;
        background-color: #141414;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: white;
    }}
    .macros-row {{
        display: flex;
        justify-content: space-around;
        width: 100%;
        max-width: 340px;
        margin-top: 12px;
        font-size: 12px;
        background-color: rgba(20, 20, 20, 0.9);
        padding: 8px 6px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

EXCEL_FILE = "fitness_entries.xlsx"
WEIGHT_FILE = "weight_data.json"
TARGET_PROTEIN, TARGET_FAT, TARGET_CARBS, BASE_CALORIE_TARGET = 160, 70, 180, 1990

DAYS_UA = {
    "Monday": "Понеділок", "Tuesday": "Вівторок", "Wednesday": "Середа",
    "Thursday": "Четвер", "Friday": "П’ятниця", "Saturday": "Субота", "Sunday": "Неділя",
}

if "redo_stack" not in st.session_state: st.session_state["redo_stack"] = []

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key: st.error("⚠️ Не знайдено API ключ!"); st.stop()
client = genai.Client(api_key=api_key)

def load_weight():
    if os.path.exists(WEIGHT_FILE):
        with open(WEIGHT_FILE, "r") as f:
            return json.load(f)
    return {"start_weight": 89.0, "total_deficit": 0.0}

w_data = load_weight()

st.title("🏋️ Мій фітнес")

with st.container(border=True):
    user_input = st.text_input("📥 Введи, що зїв / тренування:", placeholder="Наприклад: з'їв 30г хліба або спалено 300 ккал")
    submit_btn = st.button("Записати", type="primary", use_container_width=True)

now = datetime.now()
date_str, time_str = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

def load_data():
    return pd.read_excel(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

df_data = load_data()

if submit_btn and user_input:
    prompt = f'Аналізуй: "{user_input}". JSON: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs.'
    try:
        response = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(response.text)
        
        c_consumed = float(data.get("total_consumed_kcal", 0))
        c_burned = float(data.get("kcal_burned", 0))
        
        new_entry = pd.DataFrame([{
            "Дата": date_str, "Час": time_str, 
            "Опис": data.get("food_description", user_input), 
            "Тип": "Тренування" if c_burned > 0 else "Їжа", 
            "Спожито": c_consumed, "Спалено": c_burned, 
            "Білки": float(data.get("total_protein", 0)), 
            "Жири": float(data.get("total_fat", 0)), 
            "Вуглеводи": float(data.get("total_carbs", 0))
        }])
        
        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        
        # Оновлення загального дефіциту та розрахунок ваги (7700 ккал = 1 кг)
        today_entries = df_data[df_data["Дата"].astype(str) == date_str]
        day_consumed = today_entries["Спожито"].sum()
        day_burned = today_entries["Спалено"].sum()
        
        w_data["total_deficit"] += (BASE_CALORIE_TARGET - day_consumed + day_burned)
        with open(WEIGHT_FILE, "w") as f:
            json.dump(w_data, f)
            
        st.rerun()
    except Exception as e: st.error(f"Помилка: {e}")

today_df = df_data[df_data["Дата"].astype(str) == date_str]
if not today_df.empty:
    consumed, burned, protein, fat, carbs = today_df["Спожито"].sum(), today_df["Спалено"].sum(), today_df["Білки"].sum(), today_df["Жири"].sum(), today_df["Вуглеводи"].sum()
    
    current_weight = w_data["start_weight"] - (w_data["total_deficit"] / 7700)
    
    st.markdown(f"**📅 {date_str} | Вага: ~{current_weight:.2f} кг**")
    
    percent_target = min(100, int((consumed / BASE_CALORIE_TARGET) * 100))
    st.markdown(f"""
        <div class="donut-container">
            <div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg 120deg, #FFCE56 120deg 240deg, #FF6384 240deg 360deg);">
                <div class="donut-hole">
                    <span style="font-size: 20px; font-weight: bold;">{int(consumed)}</span>
                    <span style="font-size: 11px; color: #aaa;">із {BASE_CALORIE_TARGET} ккал</span>
                    <span style="font-size: 12px; color: #4CAF50;"><b>{percent_target}%</b></span>
                </div>
            </div>
            <div class="macros-row">
                <span>🥩 {protein:.0f}/{TARGET_PROTEIN}г</span><span>🥑 {fat:.0f}/{TARGET_FAT}г</span><span>🍞 {carbs:.0f}/{TARGET_CARBS}г</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("🍽️ З'їв", f"{int(consumed)} ккал")
    c2.metric("💪 Спалено", f"{int(burned)} ккал")
    
    log_lines = [f"• {row['Час']} {'💪' if row['Тип'] == 'Тренування' else '🍽️'} {row['Опис']} — <b>{int(row['Спалено'] if row['Тип'] == 'Тренування' else row['Спожито'])} ккал</b>" for _, row in today_df.iterrows()]
    st.markdown(f'<div class="food-box"><b>📝 Лог:</b><br>{"<br>".join(log_lines)}</div>', unsafe_allow_html=True)
    
    # Блок поради від Gemini
    advice_prompt = f"""Проаналізуй харчування за сьогодні для чоловіка, який худне:
    - Спожито калорій: {consumed} із норми {BASE_CALORIE_TARGET} ккал
    - Спалено калорій: {burned} ккал
    - Білки: {protein}г (ціль {TARGET_PROTEIN}г)
    - Жири: {fat}г (ціль {TARGET_FAT}г)
    - Вуглеводи: {carbs}г (ціль {TARGET_CARBS}г)
    
    Дай коротку, чітку пораду українською мовою: чого замало, а чого забагато в раціоні, і що варто скоригувати до кінця дня. Пиши лаконічно."""
    
    try:
        advice_resp = client.models.generate_content(model="gemini-3.5-flash-lite", contents=advice_prompt)
        advice_text = advice_resp.text
    except:
        advice_text = "Не вдалося завантажити пораду."

    st.markdown(f'<div class="advice-box"><b>💡 Порада тренера (Gemini):</b><br>{advice_text}</div>', unsafe_allow_html=True)
    
    if st.button("⚠️ Очистити сьогодні", type="primary", use_container_width=True):
        df_data = df_data[df_data["Дата"].astype(str) != date_str]
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()
