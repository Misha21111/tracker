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

st.set_page_config(page_title="Мій Фітнес", page_icon="⚖️", layout="centered")

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except:
    LOCAL_TZ = timezone(timedelta(hours=2))

profile = st.sidebar.selectbox("👤 Профіль", ["Я", "Дружина"])
profile_id = "user1" if profile == "Я" else "user2"
sheet_name_prefix = "Я" if profile == "Я" else "Дружина"
SETTINGS_FILE = f"user_settings_{profile_id}.json"

@st.cache_resource
def init_gsheet():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

gs_client = init_gsheet()
spreadsheet = gs_client.open_by_key("1Blo5R_ZDOeAgVkRwXDfY1Wpw12QVrZMVUEfmY_Jlk_U")
try:
    sheet = spreadsheet.worksheet(sheet_name_prefix)
except:
    sheet = spreadsheet.add_worksheet(title=sheet_name_prefix, rows=1000, cols=10)

COLUMNS = ["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]

st.markdown(f"""<style>.stApp {{ background-image: linear-gradient(rgba(0,0,0,.72), rgba(0,0,0,.90)), url("https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"); background-size: cover; }}</style>""", unsafe_allow_html=True)

if "settings_open" not in st.session_state: st.session_state.settings_open = False
client = genai.Client(api_key=st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY"))

def load_settings():
    if not os.path.exists(SETTINGS_FILE): return {"calories": 2000, "bmr_daily": 1850, "initial_weight": 89.0, "protein_goal": 160, "fat_goal": 70, "carbs_goal": 180}
    with open(SETTINGS_FILE, "r") as f: return json.load(f)

settings = load_settings()

def load_data():
    rows = sheet.get_all_records()
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=COLUMNS)
    for col in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]: df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)
    return df

df = load_data()

st.title(f"⚖️ Калорійний трекер — {profile}")
selected_date = st.date_input("📅 Оберіть день", value=datetime.now(LOCAL_TZ).date()).strftime("%Y-%m-%d")
user_input = st.text_input("🍽️ Що з'їв / тренування")

if st.button("✅ ОК — додати", type="primary", use_container_width=True):
    if user_input.strip():
        prompt = "Ти аналізуєш їжу/тренування. Поверни JSON: {'description': '', 'type': 'Їжа', 'consumed_kcal': 0, 'burned_kcal': 0, 'protein': 0, 'fat': 0, 'carbs': 0}. Тільки JSON."
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt + user_input, config=types.GenerateContentConfig(response_mime_type="application/json"))
        res = json.loads(response.text.replace("```json", "").replace("```", ""))
        sheet.append_row([selected_date, datetime.now(LOCAL_TZ).strftime("%H:%M"), res["description"], res["type"], res["consumed_kcal"], res["burned_kcal"], res["protein"], res["fat"], res["carbs"]])
        st.rerun()

if st.button("⚙️ Налаштування"): st.session_state.settings_open = not st.session_state.settings_open

if st.session_state.settings_open:
    c = st.number_input("Ціль ккал", value=settings["calories"])
    if st.button("💾 Зберегти"):
        save = {"calories": c, "bmr_daily": 1850, "initial_weight": 89.0, "protein_goal": 160, "fat_goal": 70, "carbs_goal": 180}
        with open(SETTINGS_FILE, "w") as f: json.dump(save, f)
        st.rerun()

day_df = df[df["Дата"] == selected_date]
consumed = day_df["Спожито"].sum()
st.write(f"### Спожито: {consumed} ккал")

donut_html = f"<div style='color:white; font-size:30px;'>Спожито: {consumed} / {settings['calories']}</div>"
components.html(donut_html, height=100)

for _, row in day_df.iloc[::-1].iterrows():
    with st.container(border=True):
        st.write(f"{row['Час']} | {row['Опис']} | **{row['Спожито'] if row['Тип']=='Їжа' else row['Спалено']} ккал**")
