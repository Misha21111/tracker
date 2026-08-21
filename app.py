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
            prompt = """
Ти аналізуєш запис для фітнес-трекера.
Визнач, це їжа чи тренування, і оціни калорії та БЖВ (білки, жири, вуглеводи).
Поверни ТІЛЬКИ JSON:
{
  "description": "короткий опис",
  "type": "Їжа",
  "consumed_kcal": 0,
  "burned_kcal": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0
}
Усі числа повинні бути числовими. Не додавай markdown.
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt + "\n\nЗапис користувача:\n" + user_input.strip(),
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

                        raw = (response.text or "").strip()
            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").strip()
