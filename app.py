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
    .stButton button {{ width: 100%; border-radius: 10px; }}

    .log-item {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 6px 0;
        font-size: 14px;
    }}
    .log-item:last-child {{ border-bottom: none; }}
    .log-left {{
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-right: 10px;
        flex-grow: 1;
    }}
    .log-right {{
        white-space: nowrap;
        font-weight: bold;
        color: #36A2EB;
    }}
    </style>
    """, unsafe_allow_html=True,
)

EXCEL_FILE = "fitness_entries.xlsx"
WEIGHT_FILE = "weight_data.json"
SETTINGS_FILE = "user_settings.json"
TRASH_FILE = "fitness_trash.json"

if "show_advice" not in st.session_state: st.session_state["show_advice"] = False
if "edit_mode" not in st.session_state: st.session_state["edit_mode"] = False

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key: 
    st.error("⚠️ Не знайдено API ключ!")
    st.stop()
client = genai.Client(api_key=api_key)

def load_settings():
    default = {"calories": 2000, "protein": 160, "fat": 70, "carbs": 180, "bmr_daily": 1850}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f: return {**default, **json.load(f)}
        except: pass
    return default

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f: json.dump(s, f)

def load_weight():
    if os.path.exists(WEIGHT_FILE):
        try:
            with open(WEIGHT_FILE, "r") as f: return json.load(f)
        except: pass
    return {"current_weight": 89.0}

def save_weight(w):
    with open(WEIGHT_FILE, "w") as f: json.dump(w, f)

def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        if "Час" not in df.columns:
            df["Час"] = datetime.now(LOCAL_TZ).strftime("%H:%M")
        else:
            df["Час"] = df["Час"].fillna(datetime.now(LOCAL_TZ).strftime("%H:%M"))
        return df
    return pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

user_settings = load_settings()
w_data = load_weight()
df_data = load_data()

st.title("🏋️ Мій фітнес")

with st.container(border=True):
    user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")
    
    # Використовуємо завантажувач файлів із параметром capture="environment", 
    # який на мобільних пристроях примусово відкриває саме ЗАДНЮ камеру (основну камеру).
    captured_image = st.file_uploader(
        "📸 Зробити фото задньою камерою або завантажити:", 
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        label_visibility="visible"
    )

    submit_btn = st.button("Записати в лог", type="primary", use_container_width=True)

if submit_btn and (user_input or captured_image):
    current_time_str = datetime.now(LOCAL_TZ).strftime("%H:%M")
    current_date_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    
    try:
        if captured_image:
            image_bytes = captured_image.getvalue()
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            prompt = "Проаналізуй страву на фото. Поверни суворо JSON з ключами: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs."
            response = client.models.generate_content(model="gemini-3.5-flash", contents=[image_part, prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
        else:
            prompt = f'Аналізуй: "{user_input}". Поверни суворо JSON з ключами: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs.'
            response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
            
        data = json.loads(response.text)
        
        f_desc = data.get("food_description") or user_input or "Фото їжі"
        k_burned = float(data.get("kcal_burned") or 0)
        c_consumed = float(data.get("total_consumed_kcal") or 0)
        prot = float(data.get("total_protein") or 0)
        fat_val = float(data.get("total_fat") or 0)
        carb = float(data.get("total_carbs") or 0)
        
        new_entry = pd.DataFrame([{
            "Дата": current_date_str, "Час": current_time_str, "Опис": f_desc, 
            "Тип": "Тренування" if k_burned > 0 else "Їжа", 
            "Спожито": c_consumed, 
            "Спалено": k_burned, 
            "Білки": prot, 
            "Жири": fat_val, 
            "Вуглеводи": carb
        }])
        
        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()
    except Exception as e: st.error(f"Помилка: {e}")

today_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
available_dates = [today_str]
if not df_data.empty and "Дата" in df_data.columns:
    unique_dates = sorted(df_data["Дата"].astype(str).unique(), reverse=True)
    for d in unique_dates:
        if d not in available_dates:
            available_dates.append(d)

selected_date = st.selectbox("📅 Вибрати день для перегляду:", available_dates)

if st.button("⚙️ Налаштування", use_container_width=True): 
    st.session_state["edit_mode"] = not st.session_state["edit_mode"]

btn_del = st.button("🗑️ Видалити", use_container_width=True)
has_trash = os.path.exists(TRASH_FILE)
btn_back = st.button("🔄 Повернути", disabled=not has_trash, use_container_width=True)

if btn_del:
    if not df_data.empty:
        last_row = df_data.iloc[-1:].to_dict(orient="records")
        with open(TRASH_FILE, "w") as f: json.dump(last_row, f)
        df_data = df_data.iloc[:-1]
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()

if btn_back and has_trash:
    with open(TRASH_FILE, "r") as f: restored = json.load(f)
    df_data = pd.concat([df_data, pd.DataFrame(restored)], ignore_index=True)
    df_data.to_excel(EXCEL_FILE, index=False)
    os.remove(TRASH_FILE)
    st.rerun()

if st.session_state["edit_mode"]:
    with st.container(border=True):
        st.subheader("Редагування цілей та ваги")
        e_cal = st.number_input("Ціль калорій", value=int(user_settings["calories"]), step=10)
        e_prot = st.number_input("Ціль білків (г)", value=int(user_settings["protein"]), step=5)
        e_fat = st.number_input("Ціль жирів (г)", value=int(user_settings["fat"]), step=5)
        e_carb = st.number_input("Ціль вуглеводів (г)", value=int(user_settings["carbs"]), step=5)
        e_weight = st.number_input("Актуальна вага (кг)", value=float(w_data.get("current_weight", 89.0)), step=0.1)
        
        if st.button("💾 Зберегти зміни", type="primary", use_container_width=True):
            save_settings({"calories": e_cal, "protein": e_prot, "fat": e_fat, "carbs": e_carb, "bmr_daily": user_settings.get("bmr_daily", 1850)})
            save_weight({"current_weight": e_weight})
            st.session_state["edit_mode"] = False
            st.rerun()

day_df = df_data[df_data["Дата"].astype(str) == selected_date] if not df_data.empty else pd.DataFrame()
now = datetime.now(LOCAL_TZ)

if not day_df.empty:
    consumed = day_df["Спожито"].sum()
    explicit_burned = day_df["Спалено"].sum()
    protein, fat, carbs = day_df["Білки"].sum(), day_df["Жири"].sum(), day_df["Вуглеводи"].sum()
    
    bmr_total = user_settings.get("bmr_daily", 1850)
    if selected_date == today_str:
        hours_passed = now.hour + now.minute / 60
        total_burned = explicit_burned + (bmr_total / 24) * hours_passed
    else:
        total_burned = explicit_burned + bmr_total

    st.markdown(f"**📅 {selected_date} | Вага: ~{w_data.get('current_weight', 89.0):.1f} кг**")
    
    target_cal = user_settings["calories"]`
    percent_target = min(100, int((consumed / target_cal) * 100)) if target_cal > 0 else 0
    
    total_macros = protein + fat + carbs
    if total_macros > 0:
        p_deg = (protein / total_macros) * 360
        f_deg = p_deg + (fat / total_macros) * 360
        c_deg = f_deg + (carbs / total_macros) * 360
    else:
        p_deg, f_deg, c_deg = 0, 0, 0
    
    st.markdown(f"""
        <div class="donut-container">
            <div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg);">
                <div class="donut-hole">
                    <b>{int(consumed)}</b><br>із {target_cal} ккал<br><b>{percent_target}%</b>
                </div>
            </div>
            <div class="macros-row">
                <span>🥩 {protein:.0f}/{user_settings['protein']}г</span>
                <span>🥑 {fat:.0f}/{user_settings['fat']}г</span>
                <span>🍞 {carbs:.0f}/{user_settings['carbs']}г</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("🍽️ З'їв", f"{int(consumed)} ккал")
    c2.metric("🔥 Спалено", f"{int(total_burned)} ккал")
    
    log_html_lines = []
    for _, row in day_df.iterrows():
        t_val = str(row['Час'])[:5]
        icon = '💪' if row['Тип'] == 'Тренування' else '🍽️'
        desc = row['Опис']
        kcal = int(row['Спалено'] if row['Тип'] == 'Тренування' else row['Спожито'])
        log_html_lines.append(f'<div class="log-item"><div class="log-left">{t_val} {icon} {desc}</div><div class="log-right"><b>{kcal} ккал</b></div></div>')

    st.markdown(f'<div class="food-box"><b>📝 Лог:</b><br>{"".join(log_html_lines)}</div>', unsafe_allow_html=True)
    
    if st.button("💡 Порада Gemini", use_container_width=True):
        st.session_state["show_advice"] = True

    if st.session_state["show_advice"]:
        advice_resp = client.models.generate_content(model="gemini-3.5-flash", contents=f"Аналіз за {selected_date}: {consumed} ккал, {protein}г білків. Коротка порада.")
        st.markdown(f'<div class="advice-box"><b>💡 Порада:</b><br>{advice_resp.text}</div>', unsafe_allow_html=True)
    
    if st.button("⚠️ Очистити цей день", use_container_width=True):
        df_data = df_data[df_data["Дата"].astype(str) != selected_date]
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()
else:
    st.info(f"За цей день ({selected_date}) ще немає записів.")
