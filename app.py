import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
from google import genai
from google.genai import types

# Обробка часового поясу
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))

st.set_page_config(page_title="Мій Фітнес", layout="centered")

# --- ВИБІР ПРОФІЛЮ ---
user_profile = st.sidebar.selectbox("👤 Оберіть профіль:", ["Я", "Дружина"])
profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
WEIGHT_FILE = f"weight_data_{profile_prefix}.json"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"

IMAGE_URL = "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"

# Адаптивний CSS без блокування мобільного скролу
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), url("{IMAGE_URL}");
        background-size: cover;
        background-position: center;
    }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"] {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 8px 12px;
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
    .advice-box {{ border-left: 4px solid #36A2EB; }}
    .donut-container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 15px 0; }}
    .donut-ring {{ width: 190px; height: 190px; border-radius: 50%; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 15px rgba(0,0,0,0.8); }}
    .donut-hole {{ width: 125px; height: 125px; background-color: #141414; border-radius: 50%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: white; }}
    .macros-row {{ display: flex; justify-content: space-around; width: 100%; max-width: 340px; margin-top: 12px; font-size: 11px; background-color: rgba(20, 20, 20, 0.9); padding: 8px 6px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); }}

    .log-item {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 0;
        font-size: 14px;
    }}
    .log-item:last-child {{ border-bottom: none; }}
    .log-left {{ word-break: break-word; flex-grow: 1; margin-right: 10px; }}
    .log-right {{ white-space: nowrap; font-weight: bold; color: #36A2EB; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Ініціалізація стану
for key, default_val in [
    ("show_advice", False),
    ("advice_text", ""),
    ("edit_mode", False),
    ("open_camera", False),
    ("edit_log_mode", False),
    ("confirm_clear_day", False)
]:
    if key not in st.session_state:
        st.session_state[key] = default_val

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Не знайдено API ключ GEMINI_API_KEY!")
    st.stop()

client = genai.Client(api_key=api_key)

# --- ФУНКЦІЇ ДАНИХ ---
def load_settings():
    default = {"calories": 2000, "protein": 160, "fat": 70, "carbs": 180, "bmr_daily": 1850, "initial_weight": 89.0, "include_exercise_in_deficit": True}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**default, **json.load(f)}
        except Exception:
            pass
    return default

def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def load_data():
    empty_df = pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE)
            if "Час" not in df.columns:
                df["Час"] = datetime.now(LOCAL_TZ).strftime("%H:%M")
            return df
        except Exception:
            return empty_df
    return empty_df

def calculate_current_weight(df, settings):
    initial_weight = float(settings.get("initial_weight", 89.0))
    bmr_daily = float(settings.get("bmr_daily", 1850))
    if df.empty:
        return initial_weight
    work_df = df.copy()
    work_df["Дата"] = work_df["Дата"].astype(str)
    work_df["Спожито"] = pd.to_numeric(work_df["Спожито"], errors="coerce").fillna(0)
    work_df["Спалено"] = pd.to_numeric(work_df["Спалено"], errors="coerce").fillna(0)

    total_deficit = 0.0
    today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    now = datetime.now(LOCAL_TZ)

    for date_str in work_df["Дата"].unique():
        day_df = work_df[work_df["Дата"] == date_str]
        consumed = float(day_df["Спожито"].sum())
        exercise_burned = float(day_df["Спалено"].sum())
        bmr_for_day = (bmr_daily / 24) * (now.hour + now.minute / 60) if date_str == today else bmr_daily
        burned = bmr_for_day + exercise_burned if settings.get("include_exercise_in_deficit", True) else bmr_for_day
        total_deficit += (burned - consumed)

    return max(0.0, initial_weight - (total_deficit / 7700))

user_settings = load_settings()
df_data = load_data()
calculated_weight = calculate_current_weight(df_data, user_settings)

st.title(f"🏋️ Фітнес: {user_profile}")

# --- БЛОК ВВОДУ ---
user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")

if not st.session_state["open_camera"]:
    if st.button("📸 Увімкнути камеру", use_container_width=True):
        st.session_state["open_camera"] = True
        st.rerun()
else:
    if st.button("❌ Вимкнути камеру", use_container_width=True):
        st.session_state["open_camera"] = False
        st.rerun()

captured_image = st.camera_input("Зробити фото") if st.session_state["open_camera"] else None
submit_btn = st.button("✅ Записати в лог", type="primary", use_container_width=True)

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
        new_entry = pd.DataFrame([{
            "Дата": current_date_str,
            "Час": current_time_str,
            "Опис": data.get("food_description") or user_input or "Запис",
            "Тип": "Тренування" if float(data.get("kcal_burned") or 0) > 0 else "Їжа",
            "Спожито": float(data.get("total_consumed_kcal") or 0),
            "Спалено": float(data.get("kcal_burned") or 0),
            "Білки": float(data.get("total_protein") or 0),
            "Жири": float(data.get("total_fat") or 0),
            "Вуглеводи": float(data.get("total_carbs") or 0)
        }])
        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        st.session_state["open_camera"] = False
        st.rerun()
    except Exception as e:
        st.error(f"Помилка обробки: {e}")

st.divider()

# --- ПЕРЕГЛЯД ДНІВ ТА КЕРУВАННЯ ---
today_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
available_dates = [today_str]
if not df_data.empty and "Дата" in df_data.columns:
    for d in sorted(df_data["Дата"].astype(str).unique(), reverse=True):
        if d not in available_dates:
            available_dates.append(d)

selected_date = st.selectbox("📅 Вибрати день:", available_dates)

col_b1, col_b2 = st.columns(2)
with col_b1:
    btn_settings = st.button("⚙️ Налаштування", use_container_width=True)
with col_b2:
    btn_del = st.button("🗑️ Видалити останній", use_container_width=True)

if btn_settings:
    st.session_state["edit_mode"] = not st.session_state["edit_mode"]
    st.rerun()

if btn_del and not df_data.empty:
    last_row = df_data.iloc[-1:].to_dict(orient="records")
    with open(TRASH_FILE, "w", encoding="utf-8") as f:
        json.dump(last_row, f, ensure_ascii=False)
    df_data = df_data.iloc[:-1]
    df_data.to_excel(EXCEL_FILE, index=False)
    st.rerun()

# --- БЛОК НАЛАШТУВАНЬ ---
if st.session_state["edit_mode"]:
    st.subheader("⚙️ Налаштування цілей")
    e_cal = st.number_input("Ціль калорій", value=int(user_settings["calories"]), step=10)
    e_prot = st.number_input("Ціль білків (г)", value=int(user_settings["protein"]), step=5)
    e_fat = st.number_input("Ціль жирів (г)", value=int(user_settings["fat"]), step=5)
    e_carb = st.number_input("Ціль вуглеводів (г)", value=int(user_settings["carbs"]), step=5)
    e_initial_weight = st.number_input("Початкова вага (кг)", value=float(user_settings.get("initial_weight", 89.0)), min_value=0.0, step=0.1)
    if st.button("💾 Зберегти цілі", type="primary", use_container_width=True):
        save_settings({"calories": e_cal, "protein": e_prot, "fat": e_fat, "carbs": e_carb, "bmr_daily": user_settings.get("bmr_daily", 1850), "initial_weight": e_initial_weight, "include_exercise_in_deficit": True})
        st.session_state["edit_mode"] = False
        st.rerun()

# --- СТАТИСТИКА ДНЯ ---
day_df = df_data[df_data["Дата"].astype(str) == selected_date] if not df_data.empty else pd.DataFrame()

if not day_df.empty:
    consumed = day_df["Спожито"].sum()
    explicit_burned = day_df["Спалено"].sum()
    protein = day_df["Білки"].sum()
    fat = day_df["Жири"].sum()
    carbs = day_df["Вуглеводи"].sum()

    bmr_total = user_settings.get("bmr_daily", 1850)
    now = datetime.now(LOCAL_TZ)
    total_burned = explicit_burned + ((bmr_total / 24) * (now.hour + now.minute / 60) if selected_date == today_str else bmr_total)
    deficit = total_burned - consumed

    st.markdown(f"**📅 {selected_date} | Поточна вага: ~{calculated_weight:.1f} кг**")

    total_macros = protein + fat + carbs
    p_deg = (protein / total_macros * 360) if total_macros > 0 else 0
    f_deg = p_deg + (fat / total_macros * 360) if total_macros > 0 else 0
    c_deg = f_deg + (carbs / total_macros * 360) if total_macros > 0 else 0

    st.markdown(
        f"""
        <div class="donut-container">
            <div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg);">
                <div class="donut-hole">
                    <span style="font-size: 10px; color: #aaa;">Дефіцит: {int(deficit)}</span>
                    <b style="font-size: 14px;">{int(consumed)} / {user_settings['calories']}</b>
                    <span style="font-size: 9px; color: #888;">ккал</span>
                </div>
            </div>
            <div class="macros-row">
                <span style="color: #36A2EB;">🥩 {protein:.0f}/{user_settings['protein']}г</span>
                <span style="color: #FFCE56;">🥑 {fat:.0f}/{user_settings['fat']}г</span>
                <span style="color: #FF6384;">🍞 {carbs:.0f}/{user_settings['carbs']}г</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    log_lines = []
    for _, row in day_df.iterrows():
        t_val = str(row["Час"])[:5]
        icon = "💪" if row["Тип"] == "Тренування" else "🍽️"
        kcal = int(row["Спалено"] if row["Тип"] == "Тренування" else row["Спожито"])
        log_lines.append(f'<div class="log-item"><div class="log-left">{t_val} {icon} {row["Опис"]}</div><div class="log-right"><b>{kcal} ккал</b></div></div>')

    st.markdown(f'<div class="food-box"><b>📝 Лог:</b><br>{"".join(log_lines)}</div>', unsafe_allow_html=True)
else:
    st.info(f"За {selected_date} ще немає записів. Додайте перший продукт вище!")
