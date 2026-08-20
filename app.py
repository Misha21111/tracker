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


# ============================================================
# НАЛАШТУВАННЯ STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Мій Фітнес",
    layout="centered"
)


# ============================================================
# ВИБІР ПРОФІЛЮ
# ============================================================

user_profile = st.sidebar.selectbox(
    "👤 Оберіть профіль:",
    ["Я", "Дружина"]
)

profile_prefix = (
    "user1"
    if user_profile == "Я"
    else "user2"
)

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
WEIGHT_FILE = f"weight_data_{profile_prefix}.json"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"

TRASH_FILE = f"fitness_trash_{profile_prefix}.json"

IMAGE_URL = (
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
            rgba(0, 0, 0, 0.75),
            rgba(0, 0, 0, 0.85)
        ),
        url("{IMAGE_URL}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    #MainMenu,
    footer,
    header {{
        visibility: hidden;
    }}

    div[data-testid="stMetric"],
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px 14px;
        color: white;
    }}

    .food-box,
    .advice-box {{
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
        font-size: 11px;
        background-color: rgba(20, 20, 20, 0.9);
        padding: 8px 6px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    .log-item {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 0;
        font-size: 14px;
    }}

    .log-item:last-child {{
        border-bottom: none;
    }}

    .log-left {{
        word-break: break-word;
        overflow-wrap: break-word;
        margin-right: 10px;
        flex-grow: 1;
    }}

    .log-right {{
        white-space: nowrap;
        font-weight: bold;
        color: #36A2EB;
    }}

    div.stButton > button {{
        min-height: 46px !important;
        height: 46px !important;
        width: 100% !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        background: linear-gradient(180deg, rgba(55,55,55,0.95), rgba(30,30,30,0.95)) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.30) !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "show_advice" not in st.session_state:
    st.session_state["show_advice"] = False

if "edit_mode" not in st.session_state:
    st.session_state["edit_mode"] = False

if "open_camera" not in st.session_state:
    st.session_state["open_camera"] = False

if "edit_log_mode" not in st.session_state:
    st.session_state["edit_log_mode"] = False

if "confirm_clear_day" not in st.session_state:
    st.session_state["confirm_clear_day"] = False


# ============================================================
# GEMINI
# ============================================================

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Не знайдено API ключ!")
    st.stop()

client = genai.Client(api_key=api_key)


# ============================================================
# SETTINGS
# ============================================================

def load_settings():
    default = {
        "calories": 2000,
        "protein": 160,
        "fat": 70,
        "carbs": 180,
        "bmr_daily": 1850,
        "initial_weight": 89.0,
        "include_exercise_in_deficit": True
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**default, **saved}
        except Exception:
            pass
    return default


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


# ============================================================
# WEIGHT FILE
# ============================================================

def load_weight():
    if os.path.exists(WEIGHT_FILE):
        try:
            with open(WEIGHT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_weight": 89.0}


def save_weight(weight_data):
    with open(WEIGHT_FILE, "w", encoding="utf-8") as f:
        json.dump(weight_data, f, ensure_ascii=False, indent=2)


# ============================================================
# DATA
# ============================================================

def load_data():
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE)
            required_columns = ["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]
            for column in required_columns:
                if column not in df.columns:
                    if column in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
                        df[column] = 0
                    else:
                        df[column] = ""
            if "Час" in df.columns:
                df["Час"] = df["Час"].fillna(datetime.now(LOCAL_TZ).strftime("%H:%M"))
            numeric_columns = ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]
            for column in numeric_columns:
                df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])


# ============================================================
# UNDO
# ============================================================

def load_undo_stack():
    if not os.path.exists(TRASH_FILE):
        return []
    try:
        with open(TRASH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_undo_stack(stack):
    stack = stack[-10:]
    with open(TRASH_FILE, "w", encoding="utf-8") as f:
        json.dump(stack, f, ensure_ascii=False)


def dataframe_to_records(df):
    if df.empty: return []
    result = []
    for record in df.to_dict(orient="records"):
        clean_record = {}
        for key, value in record.items():
            if pd.isna(value): clean_record[key] = ""
            elif isinstance(value, (int, float)): clean_record[key] = float(value)
            else: clean_record[key] = str(value)
        result.append(clean_record)
    return result


def records_to_dataframe(records):
    columns = ["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]
    if not records: return pd.DataFrame(columns=columns)
    df = pd.DataFrame(records)
    for column in columns:
        if column not in df.columns:
            if column in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]: df[column] = 0
            else: df[column] = ""
    df = df[columns]
    for column in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return df


def push_undo(df):
    stack = load_undo_stack()
    stack.append(dataframe_to_records(df))
    stack = stack[-10:]
    save_undo_stack(stack)


def undo_last(df):
    stack = load_undo_stack()
    if not stack: return df, False
    previous_records = stack.pop()
    previous_df = records_to_dataframe(previous_records)
    save_undo_stack(stack)
    previous_df.to_excel(EXCEL_FILE, index=False)
    return previous_df, True


# ============================================================
# РОЗРАХУНОК ДНЯ
# ============================================================

def calculate_day_balance(day_df, date_str, settings, current_time=None):
    if day_df is None or day_df.empty:
        return {"consumed": 0.0, "active": 0.0, "bmr": 0.0, "burned": 0.0, "balance": 0.0}
    bmr_daily = float(settings.get("bmr_daily", 1850))
    include_exercise = bool(settings.get("include_exercise_in_deficit", True))
    consumed = float(pd.to_numeric(day_df["Спожито"], errors="coerce").fillna(0).sum())
    active = float(pd.to_numeric(day_df["Спалено"], errors="coerce").fillna(0).sum())
    today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    if date_str == today:
        if current_time is None: current_time = datetime.now(LOCAL_TZ)
        hours_passed = (current_time.hour + current_time.minute / 60 + current_time.second / 3600)
        bmr = (bmr_daily / 24) * hours_passed
    else:
        bmr = bmr_daily
    burned = bmr
    if include_exercise: burned += active
    balance = burned - consumed
    return {"consumed": consumed, "active": active, "bmr": bmr, "burned": burned, "balance": balance}


# ============================================================
# ІСТОРІЯ
# ============================================================

def calculate_history(df, settings):
    if df.empty: return pd.DataFrame(columns=["Дата", "З'їдено", "БМР", "Активність", "Витрачено", "Баланс", "Накопичений баланс", "Розрахункова вага"])
    work_df = df.copy()
    work_df["Дата"] = work_df["Дата"].astype(str)
    dates = sorted(work_df["Дата"].unique())
    initial_weight = float(settings.get("initial_weight", 89.0))
    rows = []
    accumulated = 0.0
    today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    now = datetime.now(LOCAL_TZ)
    for date_str in dates:
        day_df = work_df[work_df["Дата"] == date_str]
        current_time = now if date_str == today else None
        result = calculate_day_balance(day_df, date_str, settings, current_time)
        accumulated += result["balance"]
        calculated_weight = (initial_weight - accumulated / 7700)
        rows.append({
            "Дата": date_str, "З'їдено": result["consumed"], "БМР": result["bmr"],
            "Активність": result["active"], "Витрачено": result["burned"],
            "Баланс": result["balance"], "Накопичений баланс": accumulated,
            "Розрахункова вага": max(0, calculated_weight)
        })
    return pd.DataFrame(rows)


def get_current_calculated_weight(df, settings):
    history = calculate_history(df, settings)
    initial_weight = float(settings.get("initial_weight", 89.0))
    if history.empty: return initial_weight
    return float(history.iloc[-1]["Розрахункова вага"])


# ============================================================
# LOAD
# ============================================================

user_settings = load_settings()
w_data = load_weight()
df_data = load_data()

# ============================================================
# UI
# ============================================================

st.title(f"🏋️ Фітнес: {user_profile}")

with st.container(border=True):
    user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")
    
    if not st.session_state["open_camera"]:
        if st.button("📸 Увімкнути камеру", use_container_width=True):
            st.session_state["open_camera"] = True
            st.rerun()
    else:
        if st.button("❌ Вимкнути камеру", use_container_width=True):
            st.session_state["open_camera"] = False
            st.rerun()

    submit_btn = st.button("✅ Записати в лог", type="primary", use_container_width=True)
    captured_image = st.camera_input("Зробити фото камерою") if st.session_state["open_camera"] else None

if submit_btn and (user_input or captured_image):
    current_time_str = datetime.now(LOCAL_TZ).strftime("%H:%M")
    current_date_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
    try:
        if captured_image:
            image_bytes = captured_image.getvalue()
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            prompt = "Проаналізуй страву на фото. Поверни суворо JSON: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs."
            response = client.models.generate_content(model="gemini-3.5-flash", contents=[image_part, prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
        else:
            prompt = f'Аналізуй: "{user_input}". Поверни суворо JSON: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs.'
            response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(response.text)
        
        f_desc = data.get("food_description") or user_input or "Фото їжі"
        k_burned = float(data.get("kcal_burned") or 0)
        c_consumed = float(data.get("total_consumed_kcal") or 0)
        prot = float(data.get("total_protein") or 0)
        fat_val = float(data.get("total_fat") or 0)
        carb = float(data.get("total_carbs") or 0)
        
        push_undo(df_data)
        new_entry = pd.DataFrame([{"Дата": current_date_str, "Час": current_time_str, "Опис": f_desc, "Тип": ("Тренування" if k_burned > 0 else "Їжа"), "Спожито": c_consumed, "Спалено": k_burned, "Білки": prot, "Жири": fat_val, "Вуглеводи": carb}])
        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        st.session_state["open_camera"] = False
        st.rerun()
    except Exception as e:
        st.error(f"Помилка: {e}")

# ============================================================
# ДАТИ
# ============================================================

today_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
available_dates = [today_str]
if not df_data.empty:
    unique_dates = sorted(df_data["Дата"].astype(str).unique(), reverse=True)
    for d in unique_dates:
        if d not in available_dates: available_dates.append(d)

selected_date = st.selectbox("📅 Вибрати день для перегляду:", available_dates)

# Кнопки
c_btns = st.columns(3)
if c_btns[0].button("⚙️ Налаштування"):
    st.session_state["edit_mode"] = not st.session_state["edit_mode"]
    st.rerun()
    
has_undo = len(load_undo_stack()) > 0
if c_btns[1].button("🗑️ Видалити останнє"):
    if not df_data.empty:
        push_undo(df_data)
        df_data = df_data.iloc[:-1]
        df_data.to_excel(EXCEL_FILE, index=False)
        st.rerun()
        
if c_btns[2].button("🔄 Повернути", disabled=not has_undo):
    df_data, restored = undo_last(df_data)
    if restored: st.rerun()

# ============================================================
# РЕДАГУВАННЯ НАЛАШТУВАНЬ
# ============================================================

if st.session_state["edit_mode"]:
    with st.container(border=True):
        st.subheader("Налаштування профілю")
        e_cal = st.number_input("Ціль калорій", value=int(user_settings["calories"]))
        e_prot = st.number_input("Ціль білків (г)", value=int(user_settings["protein"]))
        e_fat = st.number_input("Ціль жирів (г)", value=int(user_settings["fat"]))
        e_carb = st.number_input("Ціль вуглеводів (г)", value=int(user_settings["carbs"]))
        e_weight = st.number_input("Початкова вага (кг)", value=float(user_settings.get("initial_weight", 89.0)), step=0.1)
        e_inc = st.checkbox("Враховувати вправи в дефіцит", value=bool(user_settings.get("include_exercise_in_deficit", True)))
        if st.button("💾 Зберегти зміни", type="primary"):
            new_settings = {"calories": e_cal, "protein": e_prot, "fat": e_fat, "carbs": e_carb, "bmr_daily": user_settings.get("bmr_daily", 1850), "initial_weight": e_weight, "include_exercise_in_deficit": e_inc}
            save_settings(new_settings)
            st.session_state["edit_mode"] = False
            st.rerun()

# ============================================================
# ВІДОБРАЖЕННЯ ДНЯ
# ============================================================

day_df = df_data[df_data["Дата"].astype(str) == selected_date] if not df_data.empty else pd.DataFrame()

if not day_df.empty:
    day_res = calculate_day_balance(day_df, selected_date, user_settings, datetime.now(LOCAL_TZ))
    curr_w = get_current_calculated_weight(df_data, user_settings)
    
    st.markdown(f"**📅 {selected_date}**\n\n⚖️ **Вага (розр.): {curr_w:.1f} кг**")

    # Donut Chart - ВИПРАВЛЕНО INDENTATION
    p_deg = (day_df["Білки"].sum() / (day_df["Білки"].sum() + day_df["Жири"].sum() + day_df["Вуглеводи"].sum()) * 360) if (day_df["Білки"].sum() + day_df["Жири"].sum() + day_df["Вуглеводи"].sum()) > 0 else 0
    f_deg = p_deg + ((day_df["Жири"].sum() / (day_df["Білки"].sum() + day_df["Жири"].sum() + day_df["Вуглеводи"].sum())) * 360) if (day_df["Білки"].sum() + day_df["Жири"].sum() + day_df["Вуглеводи"].sum()) > 0 else 0
    c_deg = f_deg + ((day_df["Вуглеводи"].sum() / (day_df["Білки"].sum() + day_df["Жири"].sum() + day_df["Вуглеводи"].sum())) * 360) if (day_df["Білки"].sum() + day_df["Жири"].sum() + day_df["Вуглеводи"].sum()) > 0 else 0

    st.markdown(
        f"""
        <div class="donut-container">
            <div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg);">
                <div class="donut-hole">
                    <b style="font-size: 14px;">{int(day_res['consumed'])} / {user_settings['calories']} ккал</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Log - ВИПРАВЛЕНО INDENTATION
    log_html = "".join([f'<div class="log-item"><div class="log-left">{str(r["Час"])[:5]} {"💪" if r["Тип"]=="Тренування" else "🍽️"} {r["Опис"]}</div><div class="log-right">{int(r["Спалено"] if r["Тип"]=="Тренування" else r["Спожито"])} ккал</div></div>' for _, r in day_df.iterrows()])
    st.markdown(f'<div class="food-box"><b>📝 Лог:</b><br>{log_html}</div>', unsafe_allow_html=True)

    # Gemini - ВИПРАВЛЕНО INDENTATION
    if st.button("💡 Порада Gemini"):
        st.session_state["show_advice"] = True
    
    if st.session_state["show_advice"]:
        prompt = f"Аналіз дня: {day_res}. Дай коротку пораду."
        resp = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
        st.markdown(f'<div class="advice-box"><b>💡 Порада:</b><br>{resp.text}</div>', unsafe_allow_html=True)
else:
    st.info("За цей день немає записів.")
