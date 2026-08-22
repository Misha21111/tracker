import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types

# ============================================================
# STREAMLIT
# ============================================================
st.set_page_config(
    page_title="РњС–Р№ Р¤С–С‚РЅРµСЃ",
    page_icon="вљ–пёЏ",
    layout="centered",
)

# ============================================================
# Р§РђРЎРћР’РР™ РџРћРЇРЎ
# ============================================================
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))

# ============================================================
# РџР РћР¤Р†Р›Р¬
# ============================================================
profile = st.sidebar.selectbox("рџ‘¤ РџСЂРѕС„С–Р»СЊ", ["РЇ", "Р”СЂСѓР¶РёРЅР°"])
profile_id = "user1" if profile == "РЇ" else "user2"
sheet_tab = "РЇ" if profile == "РЇ" else "Р”СЂСѓР¶РёРЅР°"

# ============================================================
# GOOGLE SHEETS
# ============================================================
SPREADSHEET_ID = "1Blo5R_ZDOeAgVkRwXDfY1Wpw12QVrZMVUEfmY_Jlk_U"
COLUMNS = [
    "Р”Р°С‚Р°", "Р§Р°СЃ", "РћРїРёСЃ", "РўРёРї", "РЎРїРѕР¶РёС‚Рѕ", "РЎРїР°Р»РµРЅРѕ",
    "Р‘С–Р»РєРё", "Р–РёСЂРё", "Р’СѓРіР»РµРІРѕРґРё",
]

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(info, scopes=scopes)
    elif os.path.exists("service_account.json"):
        credentials = Credentials.from_service_account_file(
            "service_account.json", scopes=scopes
        )
    else:
        raise RuntimeError(
            "РќРµ Р·РЅР°Р№РґРµРЅРѕ gcp_service_account Сѓ Streamlit Secrets "
            "С– РЅРµРјР°С” service_account.json."
        )

    return gspread.authorize(credentials)

@st.cache_resource(show_spinner=False)
def get_worksheet():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        ws = spreadsheet.worksheet(sheet_tab)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_tab, rows=1000, cols=len(COLUMNS))

    values = ws.get_all_values()
    if not values:
        ws.append_row(COLUMNS, value_input_option="USER_ENTERED")
    elif values[0][:len(COLUMNS)] != COLUMNS:
        # РЇРєС‰Рѕ РІРєР»Р°РґРєР° СЃС‚Р°СЂР°/РїРѕСЂРѕР¶РЅСЏ Р·Р° СЃС‚СЂСѓРєС‚СѓСЂРѕСЋ вЂ” РЅРµ СЃС‚РёСЂР°С”РјРѕ РґР°РЅС–.
        # РџСЂРѕСЃС‚Рѕ РіР°СЂР°РЅС‚СѓС”РјРѕ, С‰Рѕ РїРµСЂС€РёР№ СЂСЏРґРѕРє РјР°С” РїРѕС‚СЂС–Р±РЅС– Р·Р°РіРѕР»РѕРІРєРё.
        if len(values[0]) < len(COLUMNS):
            ws.update("A1:I1", [COLUMNS], value_input_option="USER_ENTERED")

    return ws

# ============================================================
# Р¤РћРќ + CSS
# ============================================================
BACKGROUND_IMAGE = (
    "https://i.postimg.cc/kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)

st.markdown(
    f"""
<style>
.stApp {{
    background-image: linear-gradient(rgba(0,0,0,.72), rgba(0,0,0,.90)), url("{BACKGROUND_IMAGE}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}
#MainMenu, footer, header {{ visibility: hidden; }}

div.stButton > button {{
    min-height: 46px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,.14) !important;
    background: linear-gradient(135deg, rgba(45,45,53,.98), rgba(18,18,23,.98)) !important;
    color: #fff !important;
    font-weight: 700 !important;
    box-shadow: 0 7px 20px rgba(0,0,0,.35);
    transition: transform .10s ease, box-shadow .10s ease, filter .10s ease;
}}
div.stButton > button:hover {{
    border-color: rgba(54,162,235,.65) !important;
    box-shadow: 0 10px 28px rgba(0,0,0,.45);
}}
div.stButton > button:active {{
    transform: translateY(2px) scale(.985) !important;
    box-shadow: inset 0 3px 9px rgba(0,0,0,.65) !important;
    filter: brightness(.82);
}}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
    border-radius: 12px !important;
    background: rgba(18,18,22,.94) !important;
    color: #fff !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: rgba(15,17,22,.78);
    border-radius: 14px;
}}

.log-card {{
    padding: 14px;
    border: 1px solid rgba(255,255,255,.13);
    border-radius: 16px;
    background: rgba(10,12,16,.72);
    margin-bottom: 10px;
}}
.log-head {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
}}
.log-title {{
    font-size: 17px;
    font-weight: 800;
    line-height: 1.35;
    word-break: break-word;
}}
.log-kcal {{
    white-space: nowrap;
    font-size: 16px;
    font-weight: 900;
}}
.log-sub {{
    margin-top: 8px;
    color: #bfc3cc;
    font-size: 12px;
}}

.balance-card {{
    margin: 10px 0 16px;
    padding: 16px;
    border-radius: 18px;
    background: rgba(15,17,22,.84);
    border: 1px solid rgba(255,255,255,.12);
    text-align: center;
}}
.balance-main {{ font-size: 26px; font-weight: 900; }}
.balance-sub {{ color: #b8bcc5; font-size: 13px; margin-top: 6px; }}
.deficit {{ color: #35D07F; }}
.surplus {{ color: #FF6262; }}
.neutral {{ color: #FFD166; }}

.donut-wrap {{
    width: 280px;
    height: 280px;
    margin: 0 auto 8px;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.donut {{
    width: 220px;
    height: 220px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 30px rgba(0,0,0,.65);
}}
.donut-hole {{
    width: 158px;
    height: 158px;
    border-radius: 50%;
    background: #15171c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    box-shadow: inset 0 0 22px rgba(0,0,0,.9);
    padding: 8px;
}}
.donut-status {{ font-size: 13px; font-weight: 900; }}
.donut-main {{ font-size: 23px; font-weight: 900; margin-top: 3px; }}
.donut-sub {{ color: #c7c7c7; font-size: 10px; margin-top: 6px; }}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# SESSION STATE
# ============================================================
for key, default in {
    "settings_open": False,
    "editor_open": False,
    "undo_stack": [],
    "input_nonce": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# GEMINI
# ============================================================
try:
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
except Exception:
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("вљ пёЏ РќРµ Р·РЅР°Р№РґРµРЅРѕ GEMINI_API_KEY.")
    st.info("Р”РѕРґР°Р№ GEMINI_API_KEY Сѓ Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

# ============================================================
# РќРђР›РђРЁРўРЈР’РђРќРќРЇ
# ============================================================
SETTINGS_FILE = f"user_settings_{profile_id}.json"
TRASH_FILE = f"fitness_trash_{profile_id}.json"

DEFAULT_SETTINGS = {
    "calories": 2000,
    "bmr_daily": 1850,
    "initial_weight": 89.0,
    "include_exercise_in_deficit": True,
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = DEFAULT_SETTINGS.copy()
        result.update(data)
        return result
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

settings = load_settings()

# ============================================================
# DATA HELPERS
# ============================================================
def empty_dataframe():
    return pd.DataFrame(columns=COLUMNS)

def clean_number(value):
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0.0
        return float(value)
    except Exception:
        try:
            return float(str(value).replace(",", ".").strip())
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
    return str(value).strip()

def normalize_dataframe(df):
    if df is None or df.empty:
        return empty_dataframe()
    df = df.copy()
    for col in COLUMNS:
        if col not in df.columns:
            if col in {"РЎРїРѕР¶РёС‚Рѕ", "РЎРїР°Р»РµРЅРѕ", "Р‘С–Р»РєРё", "Р–РёСЂРё", "Р’СѓРіР»РµРІРѕРґРё"}:
                df[col] = 0
            elif col == "РўРёРї":
                df[col] = "Р‡Р¶Р°"
            else:
                df[col] = ""
    df = df[COLUMNS].copy()
    for col in ["РЎРїРѕР¶РёС‚Рѕ", "РЎРїР°Р»РµРЅРѕ", "Р‘С–Р»РєРё", "Р–РёСЂРё", "Р’СѓРіР»РµРІРѕРґРё"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    for col in ["Р”Р°С‚Р°", "Р§Р°СЃ", "РћРїРёСЃ", "РўРёРї"]:
        df[col] = df[col].map(clean_text)
    return df

def load_data():
    try:
        ws = get_worksheet()
        rows = ws.get_all_records()
        return normalize_dataframe(pd.DataFrame(rows)) if rows else empty_dataframe()
    except Exception as e:
        st.error(f"вќЊ РќРµ РІРґР°Р»РѕСЃСЏ РїСЂРѕС‡РёС‚Р°С‚Рё Google Sheets: {e}")
        return empty_dataframe()

def sheet_row_values(row):
    return [
        clean_text(row.get("Р”Р°С‚Р°", "")),
        clean_text(row.get("Р§Р°СЃ", "")),
        clean_text(row.get("РћРїРёСЃ", "")),
        clean_text(row.get("РўРёРї", "Р‡Р¶Р°")) or "Р‡Р¶Р°",
        clean_number(row.get("РЎРїРѕР¶РёС‚Рѕ", 0)),
        clean_number(row.get("РЎРїР°Р»РµРЅРѕ", 0)),
        clean_number(row.get("Р‘С–Р»РєРё", 0)),
        clean_number(row.get("Р–РёСЂРё", 0)),
        clean_number(row.get("Р’СѓРіР»РµРІРѕРґРё", 0)),
    ]

def append_entry(row):
    ws = get_worksheet()
    ws.append_row(sheet_row_values(row), value_input_option="USER_ENTERED")

def delete_last_entry():
    ws = get_worksheet()
    values = ws.get_all_values()
    if len(values) <= 1:
        return None
    last = values[-1]
    ws.delete_rows(len(values))
    return dict(zip(COLUMNS, (last + [""] * len(COLUMNS))[:len(COLUMNS)]))

def replace_all_data(df):
    ws = get_worksheet()
    clean = normalize_dataframe(df)
    # РџРѕРІРЅС–СЃС‚СЋ РѕРЅРѕРІР»СЋС”РјРѕ С‚С–Р»СЊРєРё A:I, РЅРµ Р·Р°С‡С–РїР°СЋС‡Рё С–РЅС€С– РєРѕР»РѕРЅРєРё, СЏРєС‰Рѕ РІРѕРЅРё С”.
    ws.clear()
    ws.update("A1:I1", [COLUMNS], value_input_option="USER_ENTERED")
    if not clean.empty:
        values = [sheet_row_values(row) for _, row in clean.iterrows()]
        ws.update(f"A2:I{len(values)+1}", values, value_input_option="USER_ENTERED")

# ============================================================
# Р’РђР“Рђ
# ============================================================
def calculate_current_weight(dataframe, profile_settings):
    initial_weight = clean_number(profile_settings.get("initial_weight", 89.0))
    bmr_daily = clean_number(profile_settings.get("bmr_daily", 1850))
    if dataframe.empty:
        return initial_weight

    work = normalize_dataframe(dataframe)
    today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    now = datetime.now(LOCAL_TZ)
    total_balance = 0.0

    for date_value in work["Р”Р°С‚Р°"].unique():
        day = work[work["Р”Р°С‚Р°"] == date_value]
        eaten = float(day["РЎРїРѕР¶РёС‚Рѕ"].sum())
        exercise = float(day["РЎРїР°Р»РµРЅРѕ"].sum())
        if date_value == today:
            hours = now.hour + now.minute / 60
            bmr = (bmr_daily / 24) * hours
        else:
            bmr = bmr_daily
        burned = bmr + exercise if profile_settings.get("include_exercise_in_deficit", True) else bmr
        total_balance += burned - eaten

    return max(0.0, initial_weight - total_balance / 7700.0)

# ============================================================
# GEMINI JSON
# ============================================================
def parse_json_response(text):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def analyze_entry(user_text):
    prompt = """
РўРё С„С–С‚РЅРµСЃ-С‚СЂРµРєРµСЂ. РџСЂРѕР°РЅР°Р»С–Р·СѓР№ РѕРґРёРЅ Р·Р°РїРёСЃ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°.
Р’РёР·РЅР°С‡, С†Рµ Р‡Р¶Р° Р°Р±Рѕ РўСЂРµРЅСѓРІР°РЅРЅСЏ.
Р”Р»СЏ Р‡Р¶Р°: РѕС†С–РЅСЋР№ СЃРїРѕР¶РёС‚С– РєРєР°Р» С‚Р° Р‘Р–Р’.
Р”Р»СЏ РўСЂРµРЅСѓРІР°РЅРЅСЏ: РѕС†С–РЅСЋР№ СЃРїР°Р»РµРЅС– РєРєР°Р», Р° СЃРїРѕР¶РёС‚С– РєРєР°Р» С– Р‘Р–Р’ СЃС‚Р°РІ 0.
РќРµ РІРёРіР°РґСѓР№ СЃРєР»Р°РґРЅС– РЅР°Р·РІРё вЂ” РѕРїРёСЃ РјР°С” Р±СѓС‚Рё РєРѕСЂРѕС‚РєРёРј С– Р·СЂРѕР·СѓРјС–Р»РёРј.

РџРѕРІРµСЂРЅРё РўР†Р›Р¬РљР JSON:
{
  "description": "РєРѕСЂРѕС‚РєРёР№ РѕРїРёСЃ",
  "type": "Р‡Р¶Р°",
  "consumed_kcal": 0,
  "burned_kcal": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0
}
РЈСЃС– С‡РёСЃР»Р° вЂ” С‡РёСЃР»Р°, РЅРµ СЂСЏРґРєРё.
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt + "\n\nР—Р°РїРёСЃ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°:\n" + user_text.strip(),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    result = parse_json_response(response.text)

    entry_type = clean_text(result.get("type", "Р‡Р¶Р°"))
    if entry_type not in {"Р‡Р¶Р°", "РўСЂРµРЅСѓРІР°РЅРЅСЏ"}:
        entry_type = "Р‡Р¶Р°"

    consumed = max(0.0, clean_number(result.get("consumed_kcal", 0)))
    burned = max(0.0, clean_number(result.get("burned_kcal", 0)))
    protein = max(0.0, clean_number(result.get("protein", 0)))
    fat = max(0.0, clean_number(result.get("fat", 0)))
    carbs = max(0.0, clean_number(result.get("carbs", 0)))

    if entry_type == "РўСЂРµРЅСѓРІР°РЅРЅСЏ":
        consumed = 0.0
        protein = fat = carbs = 0.0
    else:
        burned = 0.0

    return {
        "description": clean_text(result.get("description", "")) or user_text.strip(),
        "type": entry_type,
        "consumed_kcal": consumed,
        "burned_kcal": burned,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
    }

# ============================================================
# Р—РђР“РћР›РћР’РћРљ
# ============================================================
df = load_data()
current_weight = calculate_current_weight(df, settings)

st.title(f"вљ–пёЏ РљР°Р»РѕСЂС–Р№РЅРёР№ С‚СЂРµРєРµСЂ вЂ” {profile}")
st.markdown(
    f"### рџ“… {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')} | "
    f"РџРѕС‚РѕС‡РЅР° РІР°РіР°: ~{current_weight:.1f} РєРі"
)

# ============================================================
# Р’Р’Р†Р” Р‡Р–Р† / РўР Р•РќРЈР’РђРќРќРЇ
# ============================================================
input_key = f"food_input_{st.session_state.input_nonce}"
user_input = st.text_input(
    "рџЌЅпёЏ Р’Р»РѕРі",
    placeholder="РќР°РїСЂРёРєР»Р°Рґ: РїР»РѕРІ Р· РєСѓСЂРєРѕСЋ 350 Рі, С‡РѕСЂРЅРёР№ С…Р»С–Р± 2 С€РјР°С‚РєРё",
    key=input_key,
)

if st.button("вњ… РћРљ", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Р’РІРµРґРё РїСЂРѕРґСѓРєС‚ Р°Р±Рѕ С‚СЂРµРЅСѓРІР°РЅРЅСЏ.")
    else:
        try:
            result = analyze_entry(user_input)
            now = datetime.now(LOCAL_TZ)
            row = {
                "Р”Р°С‚Р°": now.strftime("%Y-%m-%d"),
                "Р§Р°СЃ": now.strftime("%H:%M"),
                "РћРїРёСЃ": result["description"],
                "РўРёРї": result["type"],
                "РЎРїРѕР¶РёС‚Рѕ": result["consumed_kcal"],
                "РЎРїР°Р»РµРЅРѕ": result["burned_kcal"],
                "Р‘С–Р»РєРё": result["protein"],
                "Р–РёСЂРё": result["fat"],
                "Р’СѓРіР»РµРІРѕРґРё": result["carbs"],
            }
            append_entry(row)
            st.session_state.undo_stack.append({"action": "add", "row": row})
            st.session_state.undo_stack = st.session_state.undo_stack[-10:]
            # РџРѕР»Рµ РїРѕРІРЅС–СЃС‚СЋ РѕС‡РёС‰СѓС”С‚СЊСЃСЏ РїС–СЃР»СЏ СѓСЃРїС–С€РЅРѕРіРѕ Р·Р°РїРёСЃСѓ.
            st.session_state.input_nonce += 1
            st.success("вњ… Р—Р°РїРёСЃ Р·Р±РµСЂРµР¶РµРЅРѕ РІ Google Sheets.")
            st.rerun()
        except Exception as e:
            st.error(f"вќЊ РќРµ РІРґР°Р»РѕСЃСЏ РґРѕРґР°С‚Рё Р·Р°РїРёСЃ: {e}")

# ============================================================
# Р”Р•РќР¬
# ============================================================
today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
dates = [today]
for d in sorted(df["Р”Р°С‚Р°"].unique(), reverse=True) if not df.empty else []:
    d = clean_text(d)
    if d and d not in dates:
        dates.append(d)
selected_date = st.selectbox("рџ“… Р”РµРЅСЊ", dates)

# ============================================================
# РљРќРћРџРљР РљР•Р РЈР’РђРќРќРЇ
# ============================================================
col1, col2, col3 = st.columns(3)
with col1:
    undo_clicked = st.button("в†©пёЏ Р’С–РґРјС–РЅРёС‚Рё", use_container_width=True)
with col2:
    delete_clicked = st.button("рџ—‘пёЏ Р’РёРґР°Р»РёС‚Рё РѕСЃС‚Р°РЅРЅС–Р№", use_container_width=True)
with col3:
    settings_clicked = st.button("вњЏпёЏ Р РµРґР°РєС‚РѕСЂ", use_container_width=True)

def find_matching_row_index(dataframe, row):
    if dataframe.empty:
        return None
    matches = (
        dataframe["Р”Р°С‚Р°"].astype(str).eq(clean_text(row.get("Р”Р°С‚Р°", "")))
        & dataframe["Р§Р°СЃ"].astype(str).eq(clean_text(row.get("Р§Р°СЃ", "")))
        & dataframe["РћРїРёСЃ"].astype(str).eq(clean_text(row.get("РћРїРёСЃ", "")))
        & dataframe["РўРёРї"].astype(str).eq(clean_text(row.get("РўРёРї", "Р‡Р¶Р°")))
    )
    idx = dataframe.index[matches]
    return int(idx[-1]) if len(idx) else None

def remove_matching_last_row(row):
    ws = get_worksheet()
    values = ws.get_all_values()
    if len(values) <= 1:
        return False
    # РќР°Р№РЅР°РґС–Р№РЅС–С€Рµ РґР»СЏ Undo: РІРёРґР°Р»СЏС”РјРѕ РѕСЃС‚Р°РЅРЅС–Р№ СЂСЏРґРѕРє, СЏРєС‰Рѕ РІС–РЅ Р·Р±С–РіР°С”С‚СЊСЃСЏ Р· РґС–С”СЋ.
    last = values[-1]
    last_row = dict(zip(COLUMNS, (last + [""] * len(COLUMNS))[:len(COLUMNS)]))
    same = (
        clean_text(last_row.get("Р”Р°С‚Р°")) == clean_text(row.get("Р”Р°С‚Р°"))
        and clean_text(last_row.get("Р§Р°СЃ")) == clean_text(row.get("Р§Р°СЃ"))
        and clean_text(last_row.get("РћРїРёСЃ")) == clean_text(row.get("РћРїРёСЃ"))
        and clean_text(last_row.get("РўРёРї")) == clean_text(row.get("РўРёРї"))
    )
    if same:
        ws.delete_rows(len(values))
        return True
    return False

if undo_clicked:
    try:
        if not st.session_state.undo_stack:
            st.warning("РќРµРјР°С” РґС–Р№ РґР»СЏ РІС–РґРјС–РЅРё. РњР°РєСЃРёРјСѓРј Р·Р±РµСЂС–РіР°С”С‚СЊСЃСЏ 10 РѕСЃС‚Р°РЅРЅС–С… РґС–Р№.")
        else:
            action = st.session_state.undo_stack.pop()
            if action["action"] == "add":
                if not remove_matching_last_row(action["row"]):
                    st.warning("РќРµ РІРґР°Р»РѕСЃСЏ Р·РЅР°Р№С‚Рё Р·Р°РїРёСЃ РґР»СЏ РІС–РґРјС–РЅРё.")
                else:
                    st.success("в†©пёЏ Р”РѕРґР°РІР°РЅРЅСЏ РІС–РґРјС–РЅРµРЅРѕ.")
            elif action["action"] == "delete":
                append_entry(action["row"])
                st.success("в†©пёЏ Р’РёРґР°Р»РµРЅРЅСЏ РІС–РґРјС–РЅРµРЅРѕ вЂ” Р·Р°РїРёСЃ РїРѕРІРµСЂРЅСѓС‚Рѕ.")
            st.rerun()
    except Exception as e:
        st.error(f"вќЊ РџРѕРјРёР»РєР° РІС–РґРјС–РЅРё: {e}")

if delete_clicked:
    try:
        deleted = delete_last_entry()
        if deleted is None:
            st.warning("РќРµРјР°С” Р·Р°РїРёСЃС–РІ РґР»СЏ РІРёРґР°Р»РµРЅРЅСЏ.")
        else:
            with open(TRASH_FILE, "w", encoding="utf-8") as f:
                json.dump(deleted, f, ensure_ascii=False, indent=2)
            st.session_state.undo_stack.append({"action": "delete", "row": deleted})
            st.session_state.undo_stack = st.session_state.undo_stack[-10:]
            st.success("рџ—‘пёЏ РћСЃС‚Р°РЅРЅС–Р№ Р·Р°РїРёСЃ РІРёРґР°Р»РµРЅРѕ.")
            st.rerun()
    except Exception as e:
        st.error(f"вќЊ РџРѕРјРёР»РєР° РІРёРґР°Р»РµРЅРЅСЏ: {e}")

if settings_clicked:
    st.session_state.settings_open = not st.session_state.settings_open
    st.rerun()

# ============================================================
# Р Р•Р”РђРљРўРћР 
# ============================================================
if st.session_state.settings_open:
    st.subheader("вњЏпёЏ Р РµРґР°РєС‚РѕСЂ")
    new_calories = st.number_input(
        "рџЋЇ Р”РѕР±РѕРІР° РЅРѕСЂРјР° РєР°Р»РѕСЂС–Р№",
        min_value=0,
        value=int(settings.get("calories", 2000)),
        step=50,
    )
    new_bmr = st.number_input(
        "рџ”Ґ Р‘РњР  / РґРѕР±РѕРІР° Р±Р°Р·РѕРІР° РІРёС‚СЂР°С‚Р°",
        min_value=0,
        value=int(settings.get("bmr_daily", 1850)),
        step=50,
    )
    new_weight = st.number_input(
        "вљ–пёЏ РџРѕС‡Р°С‚РєРѕРІР° РІР°РіР°, РєРі",
        min_value=0.0,
        value=float(settings.get("initial_weight", 89.0)),
        step=0.1,
    )
    new_exercise = st.checkbox(
        "рџ’Є Р’СЂР°С…РѕРІСѓРІР°С‚Рё С‚СЂРµРЅСѓРІР°РЅРЅСЏ Сѓ РґРµС„С–С†РёС‚С–",
        value=bool(settings.get("include_exercise_in_deficit", True)),
    )
    if st.button("рџ’ѕ Р—Р±РµСЂРµРіС‚Рё", type="primary", use_container_width=True):
        save_settings({
            "calories": new_calories,
            "bmr_daily": new_bmr,
            "initial_weight": new_weight,
            "include_exercise_in_deficit": new_exercise,
        })
        st.session_state.settings_open = False
        st.success("вњ… РќР°Р»Р°С€С‚СѓРІР°РЅРЅСЏ Р·Р±РµСЂРµР¶РµРЅРѕ.")
        st.rerun()

# ============================================================
# РџР•Р Р•Р—РђР’РђРќРўРђР–Р•РќР† Р”РђРќР† РџР†РЎР›РЇ Р”Р†Р™
# ============================================================
df = load_data()
current_weight = calculate_current_weight(df, settings)
day_df = df[df["Р”Р°С‚Р°"] == selected_date].copy() if not df.empty else empty_dataframe()

consumed = float(day_df["РЎРїРѕР¶РёС‚Рѕ"].sum()) if not day_df.empty else 0.0
exercise_burned = float(day_df["РЎРїР°Р»РµРЅРѕ"].sum()) if not day_df.empty else 0.0

bmr_daily = clean_number(settings.get("bmr_daily", 1850))
now = datetime.now(LOCAL_TZ)
if selected_date == today:
    hours_passed = now.hour + now.minute / 60
    bmr_elapsed = (bmr_daily / 24) * hours_passed
else:
    bmr_elapsed = bmr_daily

total_burned = bmr_elapsed + exercise_burned if settings.get("include_exercise_in_deficit", True) else bmr_elapsed
balance = total_burned - consumed

if balance > 0:
    status_label = "Р”Р•Р¤Р†Р¦РРў"
    status_icon = "рџ“‰"
    status_color = "#35D07F"
    balance_text = f"{balance:.0f} РєРєР°Р»"
    status_class = "deficit"
elif balance < 0:
    status_label = "РџР РћР¤Р†Р¦РРў"
    status_icon = "рџ“€"
    status_color = "#FF6262"
    balance_text = f"+{abs(balance):.0f} РєРєР°Р»"
    status_class = "surplus"
else:
    status_label = "Р‘РђР›РђРќРЎ"
    status_icon = "вљ–пёЏ"
    status_color = "#FFD166"
    balance_text = "0 РєРєР°Р»"
    status_class = "neutral"

# ============================================================
# РљР РЈР–РћРљ РљРђР›РћР Р†Р™ вЂ” РќР• MACROS
# ============================================================
target = max(0.0, clean_number(settings.get("calories", 2000)))
if target > 0:
    eaten_share = min(max(consumed / target, 0.0), 1.0)
else:
    eaten_share = 0.0

eaten_deg = eaten_share * 360
if consumed <= target and target > 0:
    ring_background = (
        f"conic-gradient(#36A2EB 0deg {eaten_deg:.2f}deg, "
        f"#2b2e36 {eaten_deg:.2f}deg 360deg)"
    )
else:
    ring_background = (
        f"conic-gradient(#36A2EB 0deg 360deg)"
    )

donut_html = f"""
<div class="donut-wrap">
  <div class="donut" style="background:{ring_background};">
    <div class="donut-hole">
      <div class="donut-status" style="color:{status_color};">{status_icon} {status_label}</div>
      <div class="donut-main">{consumed:.0f}</div>
      <div class="donut-sub">рџЌЅпёЏ Р·'С—РґРµРЅРѕ / {target:.0f} РєРєР°Р»</div>
      <div class="donut-sub">рџ”Ґ Р‘РњР : {bmr_daily:.0f} РєРєР°Р»/РґРѕР±Сѓ</div>
      <div class="donut-sub">вљ–пёЏ {current_weight:.1f} РєРі</div>
    </div>
  </div>
</div>
"""
st.markdown(donut_html, unsafe_allow_html=True)

# ============================================================
# РћРЎРќРћР’РќР† Р¦РР¤Р Р
# ============================================================
st.subheader("рџ“Љ РЎСЊРѕРіРѕРґРЅС–")
s1, s2, s3 = st.columns(3)
with s1:
    st.metric("рџЌЅпёЏ Р—'С—РґРµРЅРѕ", f"{consumed:.0f} РєРєР°Р»")
with s2:
    st.metric("рџЋЇ Р”РѕР±РѕРІР° РЅРѕСЂРјР°", f"{target:.0f} РєРєР°Р»")
with s3:
    st.metric("рџ”Ґ Р’РёС‚СЂР°С‡РµРЅРѕ", f"{total_burned:.0f} РєРєР°Р»")

st.progress(min(max(consumed / target, 0.0), 1.0) if target > 0 else 0.0)
st.caption(f"рџЌЅпёЏ {consumed:.0f} С–Р· {target:.0f} РєРєР°Р»")

# ============================================================
# Р’Р›РћР“
# ============================================================
st.subheader(f"рџ“‹ Р’Р»РѕРі Р·Р° {selected_date}")
if day_df.empty:
    st.info("Р—Р°РїРёСЃС–РІ С‰Рµ РЅРµРјР°С”. Р”РѕРґР°Р№ С—Р¶Сѓ Р°Р±Рѕ С‚СЂРµРЅСѓРІР°РЅРЅСЏ РІРёС‰Рµ.")
else:
    for _, row in day_df.iloc[::-1].iterrows():
        time_value = clean_text(row.get("Р§Р°СЃ", ""))[:5]
        description = clean_text(row.get("РћРїРёСЃ", ""))
        row_type = clean_text(row.get("РўРёРї", "Р‡Р¶Р°")) or "Р‡Р¶Р°"

        if row_type == "РўСЂРµРЅСѓРІР°РЅРЅСЏ":
            icon = "рџ’Є"
            kcal = clean_number(row.get("РЎРїР°Р»РµРЅРѕ", 0))
            kcal_text = f"-{kcal:.0f} РєРєР°Р»"
            kcal_color = "#FF6262"
        else:
            icon = "рџЌЅпёЏ"
            kcal = clean_number(row.get("РЎРїРѕР¶РёС‚Рѕ", 0))
            kcal_text = f"+{kcal:.0f} РєРєР°Р»"
            kcal_color = "#36A2EB"

        protein = clean_number(row.get("Р‘С–Р»РєРё", 0))
        fat = clean_number(row.get("Р–РёСЂРё", 0))
        carbs = clean_number(row.get("Р’СѓРіР»РµРІРѕРґРё", 0))

        st.markdown(
            f"""
<div class="log-card">
  <div class="log-head">
    <div class="log-title">{time_value} {icon} {description}</div>
    <div class="log-kcal" style="color:{kcal_color};">{kcal_text}</div>
  </div>
  <div class="log-sub">Р‘С–Р»РєРё: {protein:.1f} Рі &nbsp;вЂў&nbsp; Р–РёСЂРё: {fat:.1f} Рі &nbsp;вЂў&nbsp; Р’СѓРіР»РµРІРѕРґРё: {carbs:.1f} Рі</div>
</div>
""",
            unsafe_allow_html=True,
        )

# ============================================================
# РџР†Р”РЎРЈРњРћРљ
# ============================================================
st.divider()
st.markdown(
    f"<div class='balance-card'>"
    f"<div class='balance-main {status_class}'>{status_icon} {status_label}: {balance_text}</div>"
    f"<div class='balance-sub'>Р—'С—РґРµРЅРѕ: {consumed:.0f} РєРєР°Р» вЂў Р’РёС‚СЂР°С‡РµРЅРѕ: {total_burned:.0f} РєРєР°Р»</div>"
    f"</div>",
    unsafe_allow_html=True,
)
st.caption("вљ–пёЏ РћСЂС–С”РЅС‚РёСЂ: РїСЂРёР±Р»РёР·РЅРѕ 7700 РєРєР°Р» РЅР°РєРѕРїРёС‡РµРЅРѕРіРѕ РґРµС„С–С†РёС‚Сѓ в‰€ 1 РєРі Р·РјС–РЅРё РІР°РіРё.")

# ============================================================
# Р”Р†РђР“РќРћРЎРўРРљРђ GOOGLE SHEETS
# ============================================================
with st.expander("рџ”§ РџРµСЂРµРІС–СЂРєР° Google Sheets"):
    try:
        ws = get_worksheet()
        st.success(f"Google Sheets РїС–РґРєР»СЋС‡РµРЅРѕ: РІРєР»Р°РґРєР° В«{ws.title}В»")
        st.caption(f"ID С‚Р°Р±Р»РёС†С–: {SPREADSHEET_ID}")
    except Exception as e:
        st.error(f"Google Sheets РЅРµРґРѕСЃС‚СѓРїРЅРёР№: {e}")
        st.info(
            "Service Account РјР°С” Р±СѓС‚Рё Editor СЃР°РјРµ РґР»СЏ С†С–С”С— С‚Р°Р±Р»РёС†С–. "
            "РўР°РєРѕР¶ Сѓ Google Cloud РјР°СЋС‚СЊ Р±СѓС‚Рё СѓРІС–РјРєРЅРµРЅС– Google Sheets API С‚Р° Google Drive API."
)
