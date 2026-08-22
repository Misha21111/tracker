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
# ФАЙЛИ НАЛАШТУВАНЬ ТА СМІТНИКА (Локально)
# ============================================================

SETTINGS_FILE = f"user_settings_{profile_id}.json"
TRASH_FILE = f"fitness_trash_{profile_id}.json"


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
    # Підключаємося за твоїм ID таблиці
    spreadsheet = gs_client.open_by_key("1Blo5R_ZDOeAgVkRwXDfY1Wpw12QVrZMVUEfmY_Jlk_U")
    
    # Вибираємо вкладку залежно від профілю (або створюємо її)
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

    # Перевіряємо заголовок
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
    transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
}}

div.stButton > button:hover {{
    transform: translateY(-1px);
    border-color: rgba(54,162,235,.65) !important;
    box-shadow: 0 10px 28px rgba(0,0,0,.45);
}}

div.stButton > button:active {{
    transform: translateY(2px) scale(.985) !important;
    box-shadow: inset 0 3px 8px rgba(0,0,0,.55) !important;
    filter: brightness(.88);
}}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
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
    st.info("Додай GEMINI_API_KEY у Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

DEFAULT_SETTINGS = {
    "calories": 2000,
    "bmr_daily": 1850,
    "initial_weight": 89.0,
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


# ============================================================
# ЗАГОЛОВОК
# ============================================================

current_weight = calculate_current_weight(df, settings)

st.title(f"⚖️ Калорійний трекер — {profile}")
st.markdown(f"""### 📅 {datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")} | Поточна вага: ~{current_weight:.1f} кг""")


# ============================================================
# ВВЕДЕННЯ ЇЖІ / ТРЕНУВАННЯ
# ============================================================

user_input = st.text_input(
    "🍽️ Що з'їв / тренування",
    placeholder="Наприклад: плов з куркою 350 г, чорний хліб 2 шматки"
)


# ============================================================
# ДОДАТИ ЗАПИС
# ============================================================

if st.button("✅ ОК — додати", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Введи продукт, їжу або тренування.")
    else:
        try:
            prompt = """
Ти аналізуєш запис для фітнес-трекера.
Визнач, це їжа чи тренування, і оціни калорії.
Для їжі: спожиті калорії.
Для тренування: спалені калорії.
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
            model="models/gemini-3.6-flash",

                contents=prompt + "\n\nЗапис користувача:\n" + user_input.strip(),
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            raw = (response.text or "").strip()
            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").strip()

            result = json.loads(raw)

            description = clean_text(result.get("description", user_input.strip()))
            if not description:
                description = user_input.strip()

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
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M"),
                description,
                entry_type,
                consumed_kcal,
                burned_kcal,
                protein,
                fat,
                carbs
            ]

            # Записуємо прямо в Google Таблицю
            sheet.append_row(new_row)

            st.success("✅ Запис додано в Google Таблицю.")
            st.rerun()

        except json.JSONDecodeError:
            st.error("❌ Gemini повернув неправильний JSON.")
        except Exception as error:
            st.error(f"❌ Помилка: {error}")


# ============================================================
# ДЕНЬ
# ============================================================

st.divider()

today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
dates = [today]

if not df.empty:
    for date_value in df["Дата"].apply(clean_text).unique():
        if date_value and date_value not in dates:
            dates.append(date_value)

selected_date = st.selectbox("📅 День", dates)


# ============================================================
# КНОПКИ
# ============================================================

button1, button2 = st.columns(2)

with button1:
    settings_button = st.button("⚙️ Налаштування", use_container_width=True)

with button2:
    delete_button = st.button("🗑️ Видалити останній", use_container_width=True)

if settings_button:
    st.session_state.settings_open = not st.session_state.settings_open
    st.rerun()


# ============================================================
# ВИДАЛЕННЯ ОСТАННЬОГО ЗАПИСУ З GOOGLE SHEETS
# ============================================================

if delete_button:
    if df.empty:
        st.warning("Лог порожній.")
    else:
        try:
            all_rows = sheet.get_all_values()
            if len(all_rows) > 1:
                # Видаляємо останній рядок у таблиці (враховуючи заголовок)
                sheet.delete_rows(len(all_rows))
                st.success("🗑️ Останній запис видалено з Google Таблиці.")
                st.rerun()
            else:
                st.warning("Нічого видаляти (лишився тільки заголовок).")
        except Exception as e:
            st.error(f"Помилка видалення: {e}")


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

if st.session_state.settings_open:
    st.subheader("⚙️ Налаштування")
    calories_value = st.number_input("🎯 Добова ціль, ккал", min_value=0, value=int(settings["calories"]), step=50)
    bmr_value = st.number_input("🔥 БМР / добова базова витрата, ккал", min_value=0, value=int(settings["bmr_daily"]), step=50)
    initial_weight_value = st.number_input("⚖️ Початкова вага, кг", min_value=0.0, value=float(settings["initial_weight"]), step=0.1)
    exercise_in_deficit = st.checkbox("💪 Враховувати спалені на тренуванні калорії в дефіциті", value=settings.get("include_exercise_in_deficit", True))

    if st.button("💾 Зберегти", type="primary", use_container_width=True):
        save_settings({
            "calories": calories_value,
            "bmr_daily": bmr_value,
            "initial_weight": initial_weight_value,
            "include_exercise_in_deficit": exercise_in_deficit
        })
        st.session_state.settings_open = False
        st.success("✅ Налаштування збережено.")
        st.rerun()


# ============================================================
# СТАТИСТИКА ДНЯ
# ============================================================

if df.empty:
    day_df = empty_dataframe()
else:
    day_df = df[df["Дата"].apply(clean_text) == selected_date].copy()

if not day_df.empty:
    consumed = float(day_df["Спожито"].apply(clean_number).sum())
    exercise_burned = float(day_df["Спалено"].apply(clean_number).sum())
else:
    consumed = 0.0
    exercise_burned = 0.0

bmr_daily = clean_number(settings.get("bmr_daily", 1850))
now = datetime.now(LOCAL_TZ)

if selected_date == today:
    hours_passed = now.hour + now.minute / 60
    bmr_elapsed = (bmr_daily / 24) * hours_passed
else:
    bmr_elapsed = bmr_daily

if settings.get("include_exercise_in_deficit", True):
    total_burned = bmr_elapsed + exercise_burned
else:
    total_burned = bmr_elapsed

balance = total_burned - consumed

if balance > 0:
    status = "ДЕФІЦИТ"
    status_icon = "📉"
    status_color = "#35D07F"
    status_value = f"−{balance:.0f} ккал"
elif balance < 0:
    status = "ПРОФІЦИТ"
    status_icon = "📈"
    status_color = "#FF6262"
    status_value = f"+{abs(balance):.0f} ккал"
else:
    status = "БАЛАНС"
    status_icon = "⚖️"
    status_color = "#FFD166"
    status_value = "0 ккал"

current_weight = calculate_current_weight(df, settings)


# ============================================================
# КРУЖОК (DIAGRAM)
# ============================================================

target = max(0.0, clean_number(settings.get("calories", 2000)))
if target > 0:
    eaten_share = min(max(consumed / target, 0.0), 1.0)
else:
    eaten_share = 0.0

eaten_deg = eaten_share * 360

if consumed > target and target > 0:
    over_share = min((consumed - target) / target, 1.0)
    over_deg = over_share * 360
    ring_background = f"conic-gradient(#FF6384 0deg {over_deg:.2f}deg, #FFCE56 {over_deg:.2f}deg 180deg, #36A2EB 180deg 360deg)"
elif target > 0:
    ring_background = f"conic-gradient(#36A2EB 0deg {eaten_deg:.2f}deg, #FFCE56 {eaten_deg:.2f}deg 240deg, #FF6384 240deg 360deg)"
else:
    ring_background = "conic-gradient(#36A2EB 0deg 120deg, #FFCE56 120deg 240deg, #FF6384 240deg 360deg)"

donut_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
html, body {{
    margin: 0; padding: 0; width: 100%; height: 100%; background: transparent; overflow: hidden;
}}
body {{
    display: flex; justify-content: center; align-items: center; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
}}
.wrapper {{ width: 280px; height: 285px; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
.donut {{ width: 210px; height: 210px; border-radius: 50%; background: {ring_background}; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 30px rgba(0,0,0,.65); }}
.hole {{ width: 150px; height: 150px; border-radius: 50%; background: #15171c; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; box-shadow: inset 0 0 22px rgba(0,0,0,.9); }}
.status {{ color: {status_color}; font-size: 13px; font-weight: 900; }}
.balance {{ color: {status_color}; font-size: 22px; font-weight: 900; margin-top: 3px; }}
.sub {{ color: #c7c7c7; font-size: 10px; margin-top: 7px; }}
.weight {{ color: #ffffff; font-size: 10px; font-weight: 800; margin-top: 4px; }}
</style>
</head>
<body>
<div class="wrapper">
    <div class="donut">
        <div class="hole">
            <div class="status">{status_icon} {status}</div>
            <div class="balance">{status_value}</div>
            <div class="sub">🍽️ З'їдено: {consumed:.0f} ккал</div>
            <div class="sub">🔥 БМР: {bmr_daily:.0f} ккал/добу</div>
            <div class="weight">⚖️ {current_weight:.1f} кг</div>
        </div>
    </div>
</div>
</body>
</html>
"""

components.html(donut_html, height=300, scrolling=False)


# ============================================================
# ОСНОВНІ ЦИФРИ
# ============================================================

st.subheader("📊 Сьогодні")

stat1, stat2, stat3, stat4 = st.columns(4)

with stat1:
    st.metric("🍽️ З'їдено", f"{consumed:.0f} ккал")

with stat2:
    st.metric("🔥 БМР / доба", f"{bmr_daily:.0f} ккал")

with stat3:
    if balance > 0:
        st.metric("📉 Дефіцит", f"{balance:.0f} ккал")
    elif balance < 0:
        st.metric("📈 Профіцит", f"{abs(balance):.0f} ккал")
    else:
        st.metric("⚖️ Баланс", "0 ккал")

with stat4:
    st.metric("⚖️ Вага", f"{current_weight:.1f} кг")


# ============================================================
# ПРОГРЕС КАЛОРІЙ
# ============================================================

target_calories = clean_number(settings.get("calories", 2000))
progress = min(max(consumed / target_calories, 0.0), 1.0) if target_calories > 0 else 0.0

st.progress(progress)
st.caption(f"🍽️ {consumed:.0f} із {target_calories:.0f} ккал")


# ============================================================
# ВЛОГ
# ============================================================

st.subheader(f"📋 Влог за {selected_date}")

if day_df.empty:
    st.info("Записів ще немає. Додай їжу або тренування вище.")
else:
    for _, row in day_df.iloc[::-1].iterrows():
        time_value = clean_text(row.get("Час", ""))[:5]
        description = clean_text(row.get("Опис", ""))
        row_type = clean_text(row.get("Тип", "Їжа"))

        if row_type == "Тренування":
            icon = "💪"
            kcal = clean_number(row.get("Спалено", 0))
            kcal_text = f"−{kcal:.0f} ккал"
        else:
            icon = "🍽️"
            kcal = clean_number(row.get("Спожито", 0))
            kcal_text = f"+{kcal:.0f} ккал"

        with st.container(border=True):
            left, right = st.columns([4, 1])
            with left:
                st.write(f"**{time_value}** {icon} **{description}**")
            with right:
                st.write(f"**{kcal_text}**")
