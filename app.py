import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import gspread
from google.oauth2.service_account import Credentials

from google import genai
from google.genai import types


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="⚖️",
    layout="centered"
)


# ============================================================
# ЧАСОВИЙ ПОЯС
# ============================================================

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


# ============================================================
# ПРОФІЛЬ
# ============================================================

profile = st.sidebar.selectbox(
    "👤 Профіль",
    [
        "Я",
        "Дружина"
    ]
)

if profile == "Я":
    profile_id = "user1"
    sheet_name_prefix = "Я"
else:
    profile_id = "user2"
    sheet_name_prefix = "Дружина"


# ============================================================
# ФАЙЛИ НАЛАШТУВАНЬ
# ============================================================

SETTINGS_FILE = f"user_settings_{profile_id}.json"


# ============================================================
# GOOGLE SHEETS ПІДКЛЮЧЕННЯ
# ============================================================

@st.cache_resource
def init_gsheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    return gspread.authorize(creds)

try:
    gs_client = init_gsheet()
    spreadsheet = gs_client.open_by_key("1Blo5R_ZDOeAgVkRwXDfY1Wpw12QVrZMVUEfmY_Jlk_U")
    
    try:
        sheet = spreadsheet.worksheet(sheet_name_prefix)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name_prefix, rows=1000, cols=10)

    COLUMNS = [
        "Дата",
        "Час",
        "Опис",
        "Тип",
        "Спожито",
        "Спалено",
        "Білки",
        "Жири",
        "Вуглеводи"
    ]

    existing_data = sheet.get_all_values()
    if not existing_data:
        sheet.append_row(COLUMNS)

except Exception as e:
    st.error(f"❌ Помилка підключення до Google Таблиці: {e}")
    st.stop()


# ============================================================
# ФОН
# ============================================================

BACKGROUND_IMAGE = (
    "https://i.postimg.cc/"
    "kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    f"""
<style>
.stApp {{
    background-image:
        linear-gradient(
            rgba(0,0,0,.72),
            rgba(0,0,0,.90)
        ),
        url("{BACKGROUND_IMAGE}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

#MainMenu, footer, header {{
    visibility: hidden;
}}

div.stButton > button {{
    min-height: 46px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,.14) !important;
    background: linear-gradient(135deg, rgba(45,45,53,.98), rgba(18,18,23,.98)) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    box-shadow: 0 7px 20px rgba(0,0,0,.35);
}}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input {{
    border-radius: 12px !important;
    background: rgba(18,18,22,.94) !important;
    color: #ffffff !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: rgba(15,17,22,.78);
    border-radius: 14px;
}}
</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "settings_open" not in st.session_state:
    st.session_state.settings_open = False


# ============================================================
# GEMINI
# ============================================================

api_key = None
try:
    api_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    pass

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Не знайдено GEMINI_API_KEY.")
    st.stop()

client = genai.Client(api_key=api_key)


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

DEFAULT_SETTINGS = {
    "calories": 2000,
    "bmr_daily": 1850,
    "initial_weight": 89.0,
    "protein_goal": 160,
    "fat_goal": 70,
    "carbs_goal": 180,
    "include_exercise_in_deficit": True
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        result = DEFAULT_SETTINGS.copy()
        result.update(data)
        return result
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)

settings = load_settings()


# ============================================================
# РОБОТА З ДАНИМИ (GOOGLE SHEETS)
# ============================================================

def empty_dataframe():
    return pd.DataFrame(columns=COLUMNS)

def clean_number(value):
    try:
        number = float(value)
        if pd.isna(number):
            return 0.0
        return number
    except Exception:
        return 0.0

def clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value)
    if text.lower() == "nan":
        return ""
    return text

def load_data():
    try:
        rows = sheet.get_all_records()
        if not rows:
            return empty_dataframe()
        df = pd.DataFrame(rows)
    except Exception:
        return empty_dataframe()

    for column in COLUMNS:
        if column not in df.columns:
            if column in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
                df[column] = 0
            elif column == "Тип":
                df[column] = "Їжа"
            else:
                df[column] = ""

    df = df[COLUMNS].copy()

    for column in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    for column in ["Дата", "Час", "Опис", "Тип"]:
        df[column] = df[column].apply(clean_text)

    return df

df = load_data()


# ============================================================
# ПОТОЧНА ВАГА
# ============================================================

def calculate_current_weight(dataframe, profile_settings):
    initial_weight = clean_number(profile_settings.get("initial_weight", 89.0))
    bmr_daily = clean_number(profile_settings.get("bmr_daily", 1850))

    if dataframe.empty:
        return initial_weight

    work = dataframe.copy()
    work["Дата"] = work["Дата"].apply(clean_text)
    work["Спожито"] = pd.to_numeric(work["Спожито"], errors="coerce").fillna(0)
    work["Спалено"] = pd.to_numeric(work["Спалено"], errors="coerce").fillna(0)

    today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    now = datetime.now(LOCAL_TZ)
    total_balance = 0.0

    for date_value in work["Дата"].unique():
        day = work[work["Дата"] == date_value]
        eaten = float(day["Спожито"].sum())
        exercise = float(day["Спалено"].sum())

        if date_value == today:
            hours = now.hour + now.minute / 60
            bmr = (bmr_daily / 24) * hours
        else:
            bmr = bmr_daily

        if profile_settings.get("include_exercise_in_deficit", True):
            burned = bmr + exercise
        else:
            burned = bmr

        total_balance += (burned - eaten)

    return max(0.0, initial_weight - total_balance / 7700)


current_weight = calculate_current_weight(df, settings)

st.title(f"⚖️ Калорійний трекер — {profile}")


# ============================================================
# КАЛЕНДАР (Вибір дати)
# ============================================================

today_date = datetime.now(LOCAL_TZ).date()
selected_date_obj = st.date_input("📅 Оберіть день", value=today_date)
selected_date = selected_date_obj.strftime("%Y-%m-%d")


# ============================================================
# ВВЕДЕННЯ ЇЖІ / ТРЕНУВАННЯ
# ============================================================

user_input = st.text_input(
    "🍽️ Що з'їв / тренування",
    placeholder="Наприклад: плов з куркою 350 г"
)

if st.button("✅ ОК — додати", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Введи продукт, їжу або тренування.")
    else:
        try:
            prompt = (
                "Ти аналізуєш запис для фітнес-трекера.\n"
                "Визнач, це їжа чи тренування, і оціни калорії та БЖВ (білки, жири, вуглеводи).\n"
                "Поверни ТІЛЬКИ JSON:\n"
                "{\n"
                '  "description": "короткий опис",\n'
                '  "type": "Їжа",\n'
                '  "consumed_kcal": 0,\n'
                '  "burned_kcal": 0,\n'
                '  "protein": 0,\n'
                '  "fat": 0,\n'
                '  "carbs": 0\n'
                "}\n"
                "Усі числа повинні бути числовими. Не додавай markdown."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt + "\n\nЗапис користувача:\n" + user_input.strip(),
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            raw = (response.text or "").strip()
            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw)

            description = clean_text(result.get("description", user_input.strip()))
            entry_type = clean_text(result.get("type", "Їжа"))
            if entry_type not in ["Їжа", "Тренування"]:
                entry_type = "Їжа"

            consumed_kcal = clean_number(result.get("consumed_kcal", 0))
            burned_kcal = clean_number(result.get("burned_kcal", 0))
            protein = clean_number(result.get("protein", 0))
            fat = clean_number(result.get("fat", 0))
            carbs = clean_number(result.get("carbs", 0))

            if entry_type == "Тренування":
                consumed_kcal = 0.0
            else:
                burned_kcal = 0.0

            now = datetime.now(LOCAL_TZ)
            new_row = [
                selected_date,
                now.strftime("%H:%M"),
                description,
                entry_type,
                consumed_kcal,
                burned_kcal,
                protein,
                fat,
                carbs
            ]

            sheet.append_row(new_row)
            st.success("✅ Запис додано в Google Таблицю.")
            st.rerun()

        except Exception as error:
            st.error(f"❌ Помилка: {error}")


# ============================================================
# КНОПКИ КЕРУВАННЯ
# ============================================================

col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("⚙️ Налаштування", use_container_width=True):
        st.session_state.settings_open = not st.session_state.settings_open
        st.rerun()
with col_b2:
    if st.button("🗑️ Видалити останній", use_container_width=True):
        if df.empty:
            st.warning("Лог порожній.")
        else:
            try:
                all_rows = sheet.get_all_values()
                if len(all_rows) > 1:
                    sheet.delete_rows(len(all_rows))
                    st.success("🗑️ Останній запис видалено.")
                    st.rerun()
                else:
                    st.warning("Нічого видаляти.")
            except Exception as e:
                st.error(f"Помилка видалення: {e}")


# ============================================================
# НАЛАШТУВАННЯ ВІКНО
# ============================================================

if st.session_state.settings_open:
    st.subheader("⚙️ Налаштування")
    calories_value = st.number_input("🎯 Добова ціль, ккал", value=int(settings["calories"]))
    bmr_value = st.number_input("🔥 БМР, ккал", value=int(settings["bmr_daily"]))
    initial_weight_value = st.number_input("⚖️ Початкова вага, кг", value=float(settings["initial_weight"]))
    p_goal = st.number_input("🥩 Білки ціль, г", value=int(settings.get("protein_goal", 160)))
    f_goal = st.number_input("🥑 Жири ціль, г", value=int(settings.get("fat_goal", 70)))
    c_goal = st.number_input("🍞 Вуглеводи ціль, г", value=int(settings.get("carbs_goal", 180)))

    if st.button("💾 Зберегти", type="primary", use_container_width=True):
        save_settings({
            "calories": calories_value,
            "bmr_daily": bmr_value,
            "initial_weight": initial_weight_value,
            "protein_goal": p_goal,
            "fat_goal": f_goal,
            "carbs_goal": c_goal,
            "include_exercise_in_deficit": settings.get("include_exercise_in_deficit", True)
        })
        st.session_state.settings_open = False
        st.success("✅ Збережено.")
        st.rerun()


# ============================================================
# СТАТИСТИКА ДНЯ ТА БЖВ
# ============================================================

if df.empty:
    day_df = empty_dataframe()
else:
    day_df = df[df["Дата"].apply(clean_text) == selected_date].copy()

if not day_df.empty:
    consumed = float(day_df["Спожито"].apply(clean_number).sum())
    exercise_burned = float(day_df["Спалено"].apply(clean_number).sum())
    total_protein = float(day_df["Білки"].apply(clean_number).sum())
    total_fat = float(day_df["Жири"].apply(clean_number).sum())
    total_carbs = float(day_df["Вуглеводи"].apply(clean_number).sum())
else:
    consumed = 0.0
    exercise_burned = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0

bmr_daily = clean_number(settings.get("bmr_daily", 1850))
now = datetime.now(LOCAL_TZ)

if selected_date == today_date.strftime("%Y-%m-%d"):
    hours_passed = now.hour + now.minute / 60
    bmr_elapsed = (bmr_daily / 24) * hours_passed
else:
    bmr_elapsed = bmr_daily

total_burned = bmr_elapsed + exercise_burned
balance = total_burned - consumed

if balance > 0:
    status = f"Дефіцит: {balance:.0f} ккал"
    status_color = "#35D07F"
elif balance < 0:
    status = f"Профіцит: {abs(balance):.0f} ккал"
    status_color = "#FF6262"
else:
    status = "Баланс: 0 ккал"
    status_color = "#FFD166"

target_calories = clean_number(settings.get("calories", 2000))


# ============================================================
# ДІАГРАМА ТА БЖВ
# ============================================================

eaten_share = min(max(consumed / target_calories, 0.0), 1.0) if target_calories > 0 else 0.0
eaten_deg = eaten_share * 360
ring_background = f"conic-gradient(#36A2EB 0deg {eaten_deg:.2f}deg, #222 {eaten_deg:.2f}deg 360deg)"

donut_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: transparent; overflow: hidden; }}
body {{ display: flex; justify-content: center; align-items: center; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
.wrapper {{ width: 300px; height: 260px; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
.donut {{ width: 190px; height: 190px; border-radius: 50%; background: {ring_background}; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 25px rgba(0,0,0,.6); }}
.hole {{ width: 135px; height: 135px; border-radius: 50%; background: #15171c; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
.status {{ color: {status_color}; font-size: 11px; font-weight: 800; }}
.balance {{ color: #ffffff; font-size: 20px; font-weight: 900; margin-top: 2px; }}
.sub {{ color: #a0a0a0; font-size: 11px; margin-top: 2px; }}
.macros {{ display: flex; gap: 6px; margin-top: 10px; }}
.badge {{ background: rgba(30,30,40,0.9); border: 1px solid rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; color: #fff; }}
</style>
</head>
<body>
<div class="wrapper">
    <div class="donut">
        <div class="hole">
            <div class="status">📈 {status}</div>
            <div class="balance">{consumed:.0f}</div>
            <div class="sub">з {target_calories:.0f} ккал</div>
        </div>
    </div>
    <div class="macros">
        <div class="badge">🥩 Білки {total_protein:.0f}/{settings.get('protein_goal', 160)} г</div>
        <div class="badge">🥑 Жири {total_fat:.0f}/{settings.get('fat_goal', 70)} г</div>
        <div class="badge">🍞 Вуглеводи {total_carbs:.0f}/{settings.get('carbs_goal', 180)} г</div>
    </div>
</div>
</body>
</html>
"""

components.html(donut_html, height=270, scrolling=False)


# ============================================================
# ВЛОГ
# ============================================================

st.subheader(f"📋 Лог за {selected_date}")

if day_df.empty:
    st.info("За цей день немає записів у Google Таблиці.")
else:
    for _, row in day_df.iloc[::-1].iterrows():
        time_value = clean_text(row.get("Час", ""))[:5]
        description = clean_text(row.get("Опис", ""))
        row_type = clean_text(row.get("Тип", "Їжа"))
        kcal = clean_number(row.get("Спожито" if row_type == "Їжа" else "Спалено", 0))
        icon = "💪" if row_type == "Тренування" else "🍽️"

        with st.container(border=True):
            col_l, col_r = st.columns([4, 1])
            with col_l:
                st.write(f"**{time_value}** {icon} **{description}**")
            with col_r:
                st.write(f"**{kcal:.0f} ккал**")
