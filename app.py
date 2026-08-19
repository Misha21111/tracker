import pandas as pd
import streamlit as st
from datetime import datetime
import json
import os
from google import genai
from google.genai import types

st.set_page_config(page_title="Мій Фітнес", layout="centered")

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
SETTINGS_FILE = "user_settings.json"

if "show_advice" not in st.session_state: st.session_state["show_advice"] = False
if "edit_mode" not in st.session_state: st.session_state["edit_mode"] = False

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key: st.error("⚠️ Не знайдено API ключ!"); st.stop()
client = genai.Client(api_key=api_key)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"calories": 1990, "protein": 160, "fat": 70, "carbs": 180}

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f)

user_settings = load_settings()

def load_weight():
    if os.path.exists(WEIGHT_FILE):
        with open(WEIGHT_FILE, "r") as f:
            return json.load(f)
    return {"start_weight": 89.0, "total_deficit": 0.0}

w_data = load_weight()

TARGET_PROTEIN = user_settings["protein"]
TARGET_FAT = user_settings["fat"]
TARGET_CARBS = user_settings["carbs"]
BASE_CALORIE_TARGET = user_settings["calories"]

st.title("🏋️ Мій фітнес")

col_top1, col_top2 = st.columns([3, 1])
with col_top2:
    if st.button("⚙️ Змінити цілі"):
        st.session_state["edit_mode"] = not st.session_state["edit_mode"]

if st.session_state["edit_mode"]:
    with st.container(border=True):
        st.subheader("Редагування цілей і ваги вручну")
        e_cal = st.number_input("Ціль калорій (ккал)", value=int(BASE_CALORIE_TARGET), step=10)
        e_prot = st.number_input("Ціль білків (г)", value=int(TARGET_PROTEIN), step=5)
        e_fat = st.number_input("Ціль жирів (г)", value=int(TARGET_FAT), step=5)
        e_carb = st.number_input("Ціль вуглеводів (г)", value=int(TARGET_CARBS), step=5)
        e_weight = st.number_input("Початкова вага (кг)", value=float(w_data["start_weight"]), step=0.1)
        
        if st.button("💾 Зберегти зміни", type="primary", use_container_width=True):
            user_settings = {"calories": e_cal, "protein": e_prot, "fat": e_fat, "carbs": e_carb}
            save_settings(user_settings)
            w_data["start_weight"] = e_weight
            with open(WEIGHT_FILE, "w") as f:
                json.dump(w_data, f)
            st.session_state["edit_mode"] = False
            st.rerun()

with st.container(border=True):
    user_input = st.text_input("📥 Введи, що зїв / тренування:", placeholder="Наприклад: з'їв 30г хліба або спалено 300 ккал")
    submit_btn = st.button("Записати", type="primary", use_container_width=True)

now = datetime.now()
date_str, time_str = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

def load_data():
    return pd.read_excel(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

df_data = load_data()

if "history" not in st.session_state:
    st.session_state["history"] = []
if "redo_stack" not in st.session_state:
    st.session_state["redo_stack"] = []

if submit_btn and user_input:
    st.session_state["history"].append(df_data.copy())
    st.session_state["redo_stack"].clear()
    
    prompt = f'Аналізуй: "{user_input}". Поверни суворо JSON з полями: food_description (рядок), kcal_burned (число або 0), total_consumed_kcal (число або 0), total_protein (число або 0), total_fat (число або 0), total_carbs (число або 0).'
    try:
        response = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(response.text)
        
        c_consumed = float(data.get("total_consumed_kcal") or 0)
        c_burned = float(data.get("kcal_burned") or 0)
        p_val = float(data.get("total_protein") or 0)
        f_val = float(data.get("total_fat") or 0)
        cb_val = float(data.get("total_carbs") or 0)
        desc = data.get("food_description") or user_input
        
        new_entry = pd.DataFrame([{
            "Дата": date_str, "Час": time_str, 
            "Опис": desc, 
            "Тип": "Тренування" if c_burned > 0 else "Їжа", 
            "Спожито": c_consumed, "Спалено": c_burned, 
            "Білки": p_val, "Жири": f_val, "Вуглеводи": cb_val
        }])
        
        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        
        today_entries = df_data[df_data["Дата"].astype(str) == date_str]
        day_consumed = today_entries["Спожито"].sum()
        day_burned = today_entries["Спалено"].sum()
        
        w_data["total_deficit"] += (BASE_CALORIE_TARGET - day_consumed + day_burned)
        with open(WEIGHT_FILE, "w") as f:
            json.dump(w_data, f)
            
        st.session_state["show_advice"] = False
        st.rerun()
    except Exception as e: st.error(f"Помилка: {e}")

col_u1, col_u2 = st.columns(2)
with col_u1:
    if st.button("↩️ Скасувати (Undo)", use_container_width=True, disabled=len(st.session_state["history"]) == 0):
        if st.session_state["history"]:
            st.session_state["redo_stack"].append(df_data.copy())
            df_data = st.session_state["history"].pop()
            df_data.to_excel(EXCEL_FILE, index=False)
            st.rerun()
with col_u2:
    if st.button("🔁 Повернути (Redo)", use_container_width=True, disabled=len(st.session_state["redo_stack"]) == 0):
        if st.session_state["redo_stack"]:
            st.session_state["history"].append(df_data.copy())
            df_data = st.session_state["redo_stack"].pop()
            df_data.to_excel(EXCEL_FILE, index=False)
            st.rerun()

today_df = df_data[df_data["Дата"].astype(str) == date_str]
if not today_df.empty:
    consumed, burned, protein, fat, carbs = today_df["Спожито"].sum(), today_df["Спалено"].sum(), today_df["Білки"].sum(), today_df["Жири"].sum(), today_df["Вуглеводи"].sum()
    
    current_weight = w_data["start_weight"] - (w_data["total_deficit"] / 7700)
    
    st.markdown(f"**📅 {date_str} | Вага: ~{current_weight:.2f} кг**")
    
    percent_target = min(100, int((consumed / BASE_CALORIE_TARGET) * 100)) if BASE_CALORIE_TARGET > 0 else 0
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
    
    if st.button("💡 Запитати пораду у Gemini", use_container_width=True):
        st.session_state["show_advice"] = True

    if st.session_state["show_advice"]:
        advice_prompt = f"""Проаналізуй харчування за сьогодні для чоловіка, який худне:
        - Спожито калорій: {consumed} із норми {BASE_CALORIE_TARGET} ккал
        - Спалено калорій: {burned} ккал
        - Білки: {protein}г (ціль {TARGET_PROTEIN}г)
        - Жири: {fat}г (ціль {TARGET_FAT}г)
        - Вуглеводи: {carbs}г (ціль {TARGET_CARBS}г)
        
        Дай коротку, чітку пораду українською мовою: чого замало, а чого забагато в раціоні, і що варто скоригувати до кінця дня. Пиши лаконічно."""
        
        try:
            with st.spinner("Аналізую..."):
                advice_resp = client.models.generate_content(model="gemini-3.5-flash-lite", contents=advice_prompt)
                advice_text = advice_resp.text
        except:
            advice_text = "Не вдалося завантажити пораду."

        st.markdown(f'<div class="advice-box"><b>💡 Порада тренера:</b><br>{advice_text}</div>', unsafe_allow_html=True)
    
    if st.button("⚠️ Очистити сьогодні", type="primary", use_container_width=True):
        df_data = df_data[df_data["Дата"].astype(str) != date_str]
        df_data.to_excel(EXCEL_FILE, index=False)
        st.session_state["show_advice"] = False
        st.rerun()
