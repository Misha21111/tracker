import json
import os
import re
from datetime import datetime, timedelta, timezone

import gspread
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from google.oauth2.service_account import Credentials

# ============================================================
# ЧАСОВИЙ ПОЯС ТА НАЛАШТУВАННЯ
# ============================================================

try:
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))

st.set_page_config(page_title="Мій Фітнес", page_icon="⚖️", layout="centered")

# ============================================================
# АВТОРИЗАЦІЯ GEMINI ТА GOOGLE SHEETS
# ============================================================

# Gemini API
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Відсутній GEMINI_API_KEY у st.secrets чи змінних середовища.")
    st.stop()

client = genai.Client(api_key=api_key)
GEMINI_MODEL = "gemini-3.6-flash"  # Робоча стабільна модель

# Google Sheets
COLUMNS = [
    "Дата",
    "Час",
    "Опис",
    "Тип",
    "Спожито",
    "Спалено",
    "Білки",
    "Жири",
    "Вуглеводи",
    "Продукти",
]


@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        return gspread.authorize(creds)
    return None


def get_worksheet(profile_prefix: str):
    gc = get_gspread_client()
    if not gc:
        return None
    sheet_url = st.secrets.get("GSHEET_URL")
    if not sheet_url:
        st.error("⚠️ Вкажіть GSHEET_URL у secrets.toml")
        return None

    sh = gc.open_by_url(sheet_url)
    sheet_name = (
        f"Entries_{profile_prefix}"  # Окремий аркуш для кожного профілю
    )

    try:
        ws = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")
        ws.append_row(COLUMNS)
    return ws


# ============================================================
# ПРОФІЛЬ ТА ФАЙЛИ
# ============================================================

user_profile = st.sidebar.selectbox(
    "👤 Профіль", ["Я", "Дружина"], key="user_profile_select"
)
profile_prefix = "user1" if user_profile == "Я" else "user2"

SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
WATCH_FILE = f"watch_burned_{profile_prefix}.json"
IMAGE_URL = (
    "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"
)

# ============================================================
# CSS СТИЛІ
# ============================================================

st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(0,0,0,.72), rgba(0,0,0,.88)), url("{IMAGE_URL}") center / cover fixed;
    }}
    #MainMenu, footer {{ visibility: hidden; }}
    .block-container {{ max-width: 760px; padding-top: 1rem; padding-bottom: 4rem; }}
    
    div.stButton > button {{
        border-radius: 16px !important;
        min-height: 48px !important;
        border: 1px solid rgba(255,255,255,.18) !important;
        background: rgba(30,32,40,.94) !important;
        color: white !important;
        font-weight: 700 !important;
    }}
    
    .section {{
        background: rgba(10,12,17,.68);
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 22px;
        padding: 18px;
        margin: 12px 0;
    }}
    .donut-wrap {{ display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 12px 0 18px; }}
    .donut {{ width: 230px; height: 230px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
    .donut-hole {{ width: 164px; height: 164px; border-radius: 50%; background: #11131a; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: white; }}
    .balance {{ font-size: 12px; font-weight: 800; }}
    .kcal-main {{ font-size: 24px; font-weight: 900; }}
    .macros {{ display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; }}
    .macro {{ border-radius: 14px; padding: 8px 11px; background: rgba(20,22,29,.92); font-size: 12px; font-weight: 700; }}
    .macro.p {{ color: #36A2EB; }} .macro.f {{ color: #FFCE56; }} .macro.c {{ color: #FF6384; }}
    .log-card {{ background: rgba(13,15,21,.80); border: 1px solid rgba(255,255,255,.13); border-radius: 18px; padding: 14px; margin: 12px 0; }}
    .log-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }}
    .status {{ text-align: center; font-weight: 900; font-size: 17px; padding: 12px; border-radius: 16px; margin: 12px 0; }}
    .deficit {{ color: #5ee89a; background: rgba(20,120,65,.30); }}
    .surplus {{ color: #ff7373; background: rgba(140,30,35,.30); }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ФУНКЦІЇ ДАНИХ
# ============================================================


def clean_json_response(text: str):
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def load_settings():
    default = {
        "calories": 2000,
        "protein": 160,
        "fat": 70,
        "carbs": 180,
        "bmr_daily": 1850,
        "start_weight": 91.8,
    }
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


def load_data_gsheets(ws):
    empty = pd.DataFrame(columns=COLUMNS)
    if ws is None:
        return empty
    try:
        records = ws.get_all_records()
        if not records:
            return empty
        df = pd.DataFrame(records)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = "" if col in ["Опис", "Тип", "Продукти"] else 0
        df = df[COLUMNS]
        for col in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        df["Дата"] = df["Дата"].astype(str).str[:10]
        return df
    except Exception as e:
        st.error(f"Помилка завантаження з Google Sheets: {e}")
        return empty


def append_row_gsheets(ws, row_dict):
    if ws:
        row_values = [str(row_dict.get(col, "")) for col in COLUMNS]
        ws.append_row(row_values)


def load_watch():
    if not os.path.exists(WATCH_FILE):
        return {}
    try:
        with open(WATCH_FILE, "r", encoding="utf-8") as f:
            return {str(k)[:10]: float(v) for k, v in json.load(f).items()}
    except Exception:
        return {}


def save_watch(d):
    with open(WATCH_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def today_bmr(settings, date_str):
    daily = float(settings.get("bmr_daily", 1850))
    today_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    if str(date_str)[:10] == today_str:
        now = datetime.now(LOCAL_TZ)
        hours = now.hour + now.minute / 60
        return daily * min(hours / 24, 1.0)
    return daily


def calculate_day(df, date_str, settings, watch_burned=0):
    target_date = str(date_str)[:10]
    day = df[df["Дата"].astype(str).str[:10] == target_date].copy()
    food = day[day["Тип"].astype(str) == "Їжа"]

    consumed = float(food["Спожито"].sum())
    protein = float(food["Білки"].sum())
    fat = float(food["Жири"].sum())
    carbs = float(food["Вуглеводи"].sum())

    exercise_df = day[
        (day["Тип"].astype(str) == "Тренування")
        & (~day["Опис"].str.contains("годинник", case=False, na=False))
    ]
    exercise = float(exercise_df["Спалено"].sum())
    watch = float(watch_burned or 0)

    burned = today_bmr(settings, target_date) + exercise + watch
    balance = burned - consumed
    return consumed, burned, balance, protein, fat, carbs, exercise, watch


# ============================================================
# ІНІЦІАЛІЗАЦІЯ ДАНИХ
# ============================================================

ws = get_worksheet(profile_prefix)
settings = load_settings()
df = load_data_gsheets(ws)
watch_by_date = load_watch()

st.title("⚖️ Мій Фітнес (Google Sheets)")
st.caption(f"Профіль: {user_profile}")

# ============================================================
# ФОРМА ДОДАВАННЯ
# ============================================================

st.markdown("### 🍽️ Додати запис")


def handle_add_click():
    st.session_state["pending_input"] = st.session_state.get("food_input", "")
    st.session_state["food_input"] = ""


st.text_input(
    "Що з'їв / яке тренування?",
    placeholder="Наприклад: плов з куркою 350 г, 2 яйця",
    key="food_input",
)
st.button(
    "✅ Додати в лог", use_container_width=True, on_click=handle_add_click
)

# ============================================================
# ОБРОБКА З GEMINI
# ============================================================

if "pending_input" in st.session_state:
    text = (st.session_state.pop("pending_input", "") or "").strip()
    if text:
        prompt = f"""
        Ти харчовий трекер. Проаналізуй цей запис: "{text}"
        Поверни ТІЛЬКИ валідний JSON.
        Формат:
        {{
          "type": "Їжа" або "Тренування",
          "description": "короткий опис",
          "total_kcal": число,
          "burned_kcal": число,
          "protein": число,
          "fat": число,
          "carbs": число,
          "products": [
            {{"name": "назва продукту", "kcal": число, "protein": число, "fat": число, "carbs": число}}
          ]
        }}
        """
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            data = clean_json_response(response.text)
            if data:
                entry_type = (
                    "Тренування"
                    if str(data.get("type", "")).lower().startswith("трен")
                    else "Їжа"
                )
                now = datetime.now(LOCAL_TZ)

                new_row = {
                    "Дата": now.strftime("%Y-%m-%d"),
                    "Час": now.strftime("%H:%M"),
                    "Опис": str(data.get("description") or text),
                    "Тип": entry_type,
                    "Спожито": (
                        float(data.get("total_kcal", 0))
                        if entry_type == "Їжа"
                        else 0.0
                    ),
                    "Спалено": (
                        float(data.get("burned_kcal", 0))
                        if entry_type == "Тренування"
                        else 0.0
                    ),
                    "Білки": float(data.get("protein", 0)),
                    "Жири": float(data.get("fat", 0)),
                    "Вуглеводи": float(data.get("carbs", 0)),
                    "Продукти": json.dumps(
                        data.get("products", []), ensure_ascii=False
                    ),
                }

                append_row_gsheets(ws, new_row)
                st.success("✅ Запис успішно збережено в Google Таблицю!")
                st.rerun()
        except Exception as e:
            st.error(f"Помилка аналізу Gemini: {e}")

# ============================================================
# КАЛЕНДАР (ВИБІР ДАТИ)
# ============================================================

st.markdown("---")
selected_date_dt = st.date_input(
    "📅 Оберіть дату для перегляду:",
    value=datetime.now(LOCAL_TZ).date(),
    format="YYYY-MM-DD",
)
selected_date = selected_date_dt.strftime("%Y-%m-%d")

# ============================================================
# ГОДИННИК ТА РОЗРАХУНОК ДНЯ
# ============================================================

watch_key = f"watch_{profile_prefix}_{selected_date}"
if watch_key not in st.session_state:
    st.session_state[watch_key] = float(watch_by_date.get(selected_date, 0))


def on_watch_change():
    watch_by_date[selected_date] = float(st.session_state[watch_key])
    save_watch(watch_by_date)


st.number_input(
    "⌚ Спалені калорії з годинника (ккал)",
    min_value=0.0,
    step=10.0,
    key=watch_key,
    on_change=on_watch_change,
)

watch_now = float(st.session_state[watch_key])
consumed, burned, balance, protein, fat, carbs, exercise, watch = calculate_day(
    df, selected_date, settings, watch_now
)
target = float(settings["calories"])

# Відмальовка віджету
total_macros = protein + fat + carbs
if total_macros > 0:
    p_deg = protein / total_macros * 360
    f_deg = p_deg + (fat / total_macros * 360)
    c_deg = f_deg + (carbs / total_macros * 360)
    gradient = f"conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg)"
else:
    gradient = "conic-gradient(rgba(255,255,255,.14) 0deg 360deg)"

balance_label = (
    f"📉 Дефіцит: {abs(balance):.0f} ккал"
    if balance >= 0
    else f"📈 Профіцит: {abs(balance):.0f} ккал"
)
balance_class = "deficit" if balance >= 0 else "surplus"

st.markdown(
    f"""
<div class="section">
    <div class="donut-wrap">
        <div class="donut" style="background:{gradient};">
            <div class="donut-hole">
                <div class="balance">{balance_label}</div>
                <div class="kcal-main">{consumed:.0f}</div>
                <div class="kcal-sub">з {target:.0f} ккал</div>
            </div>
        </div>
        <div class="macros">
            <div class="macro p">🥩 Білки {protein:.0f}/{settings["protein"]} г</div>
            <div class="macro f">🥑 Жири {fat:.0f}/{settings["fat"]} г</div>
            <div class="macro c">🍞 Вуглеводи {carbs:.0f}/{settings["carbs"]} г</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# ВЛОГ ЗА ОБРАНИЙ ДЕНЬ
# ============================================================

st.markdown(f"### 📝 Лог за {selected_date}")

day_df = df[df["Дата"].astype(str).str[:10] == selected_date].copy()

if day_df.empty:
    st.info("За цей день немає записів у Google Таблиці.")
else:
    for _, row in day_df.iloc[::-1].iterrows():
        entry_type = str(row["Тип"])
        icon = "🍽️" if entry_type == "Їжа" else "💪"
        kcal = float(row["Спожито"] if entry_type == "Їжа" else row["Спалено"])

        st.markdown(
            f"""
        <div class="log-card">
            <div class="log-head">
                <div class="log-title">{str(row["Час"])[:5]} {icon} {row["Опис"]}</div>
                <div class="log-kcal">{kcal:+.0f} ккал</div>
            </div>
            <div style="font-size: 12px; margin-top: 5px; opacity: 0.8;">
                🥩 {row["Білки"]}г | 🥑 {row["Жири"]}г | 🍞 {row["Вуглеводи"]}г
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
