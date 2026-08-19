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
    .stApp {{ background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), url("{IMAGE_URL}"); background-size: cover; background-position: center; background-attachment: fixed; }}
    #MainMenu, footer, header {{visibility: hidden;}}
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {{ background-color: rgba(20, 20, 20, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 10px 14px; color: white; }}
    .food-box, .advice-box {{ background-color: rgba(20, 20, 20, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 12px 16px; color: #ffffff; margin-top: 10px; }}
    .advice-box {{ border-left: 4px solid #36A2EB; }}
    .donut-container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 15px 0; }}
    .donut-ring {{ width: 190px; height: 190px; border-radius: 50%; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 15px rgba(0,0,0,0.8); }}
    .donut-hole {{ width: 125px; height: 125px; background-color: #141414; border-radius: 50%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: white; }}
    .macros-row {{ display: flex; justify-content: space-around; width: 100%; max-width: 340px; margin-top: 12px; font-size: 12px; background-color: rgba(20, 20, 20, 0.9); padding: 8px 6px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); }}
    </style>
    """, unsafe_allow_html=True,
)

EXCEL_FILE = "fitness_entries.xlsx"
WEIGHT_FILE = "weight_data.json"
SETTINGS_FILE = "user_settings.json"

if "show_advice" not in st.session_state: st.session_state["show_advice"] = False
if "edit_mode" not in st.session_state: st.session_state["edit_mode"] = False

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key: 
    st.error("⚠️ Не знайдено API ключ!")
    st.stop()
client = genai.Client(api_key=api_key)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f: return json.load(f)
    return {"calories": 1990, "protein": 160, "fat": 70, "carbs": 180, "bmr_daily": 1850}

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f: json.dump(s, f)

def load_weight():
    # Завантажуємо вагу з JSON, яка зберігає прогрес постійно
    if os.path.exists(WEIGHT_FILE):
        try:
            with open(WEIGHT_FILE, "r") as f: return json.load(f)
        except: pass
    return {"current_weight": 91.8} # Стартове значення

def save_weight(w):
    with open(WEIGHT_FILE, "w") as f: json.dump(w, f)

def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    return pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

user_settings = load_settings()
w_data = load_weight()
df_data = load_data()

st.title("🏋️ Мій фітнес")

col_top1, col_top2 = st.columns([3, 1])
with col_top2:
    if st.button("⚙️ Налаштування"): st.session_state["edit_mode"] = not st.session_state["edit_mode"]

if st.session_state["edit_mode"]:
    with st.container(border=True):
        st.subheader("Редагування цілей та ваги")
        e_cal = st.number_input("Ціль калорій", value=int(user_settings["calories"]), step=10)
        e_prot = st.number_input("Ціль білків (г)", value=int(user_settings["protein"]), step=5)
        e_fat = st.number_input("Ціль жирів (г)", value=int(user_settings["fat"]), step=5)
        e_carb = st.number_input("Ціль вуглеводів (г)", value=int(user_settings["carbs"]), step=5)
        e_weight = st.number_input("Актуальна вага (кг)", value=float(w_data["current_weight"]), step=0.1)
        
        if st.button("💾 Зберегти зміни", type="primary", use_container_width=True):
            save_settings({"calories": e_cal, "protein": e_prot, "fat": e_fat, "carbs": e_carb, "bmr_daily": user_settings.get("bmr_daily", 1850)})
            w_data["current_weight"] = e_weight
            save_weight(w_data)
            st.session_state["edit_mode"] = False
            st.rerun()

with st.container(border=True):
    user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")
    submit_btn = st.button("Записати", type="primary", use_container_width=True)

now = datetime.now()
date_str, time_str = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

if submit_btn and user_input:
    prompt = f'Аналізуй: "{user_input}". Поверни суворо JSON: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs.'
    try:
        response = client.models.generate_content(model="gemini-3.5-flash-lite", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(response.text)
        
        new_entry = pd.DataFrame([{
            "Дата": date_str, "Час": time_str, "Опис": data.get("food_description", user_input), 
            "Тип": "Тренування" if float(data.get("kcal_burned", 0)) > 0 else "Їжа", 
            "Спожито": float(data.get("total_consumed_kcal", 0)), 
            "Спалено": float(data.get("kcal_burned", 0)), 
            "Білки": float(data.get("total_protein", 0)), 
            "Жири": float(data.get("total_fat", 0)), 
            "Вуглеводи": float(data.get("total_carbs", 0))
        }])
        
        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()
    except Exception as e: st.error(f"Помилка: {e}")

if st.button("↩️ Видалити останній запис"):
    if not df_data.empty:
        df_data = df_data.iloc[:-1]
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()

today_df = df_data[df_data["Дата"].astype(str) == date_str] if not df_data.empty else pd.DataFrame()

if not today_df.empty:
    consumed = today_df["Спожито"].sum()
    explicit_burned = today_df["Спалено"].sum()
    protein, fat, carbs = today_df["Білки"].sum(), today_df["Жири"].sum(), today_df["Вуглеводи"].sum()
    
    total_burned = explicit_burned + (user_settings.get("bmr_daily", 1850) / 24) * (now.hour + now.minute / 60)
    
    st.markdown(f"**📅 {date_str} | Вага: ~{w_data['current_weight']:.1f} кг**")
    
    # Розрахунок прогресу (візуалізація)
    target_cal = user_settings["calories"]
    percent_target = min(100, int((consumed / target_cal) * 100)) if target_cal > 0 else 0
    
    st.markdown(f"""
        <div class="donut-container">
            <div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg {(protein/max(1,protein+fat+carbs))*360}deg, #FFCE56 0deg 360deg);">
                <div class="donut-hole">
                    <b>{int(consumed)}</b><br>із {target_cal} ккал<br><b>{percent_target}%</b>
                </div>
            </div>
            <div class="macros-row">
                <span>🥩 {protein:.0f}/{user_settings['protein']}г</span><span>🥑 {fat:.0f}/{user_settings['fat']}г</span><span>🍞 {carbs:.0f}/{user_settings['carbs']}г</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("🍽️ З'їв", f"{int(consumed)} ккал")
    c2.metric("🔥 Спалено", f"{int(total_burned)} ккал")
    
    log_lines = [f"• {row['Час']} {'💪' if row['Тип'] == 'Тренування' else '🍽️'} {row['Опис']} — <b>{int(row['Спалено'] if row['Тип'] == 'Тренування' else row['Спожито'])} ккал</b>" for _, row in today_df.iterrows()]
    st.markdown(f'<div class="food-box"><b>📝 Лог:</b><br>{"<br>".join(log_lines)}</div>', unsafe_allow_html=True)
    
    if st.button("💡 Порада Gemini"):
        st.session_state["show_advice"] = True

    if st.session_state["show_advice"]:
        advice_resp = client.models.generate_content(model="gemini-3.5-flash-lite", contents=f"Аналіз: {consumed} ккал, {protein}г білків. Коротка порада.")
        st.markdown(f'<div class="advice-box"><b>💡 Порада:</b><br>{advice_resp.text}</div>', unsafe_allow_html=True)
    
    if st.button("⚠️ Очистити день"):
        df_data = df_data[df_data["Дата"].astype(str) != date_str]
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()
