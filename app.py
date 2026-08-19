import base64
from datetime import datetime
import json
import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# --- НАЛАШТУВАННЯ СТИЛЮ ТА ФОНУ ---
st.set_page_config(page_title="Мій Фітнес", layout="centered")


def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None


# Точна назва твого файлу з GitHub
IMAGE_FILE = "Screenshot_20260819_1...jpg"
img_base64 = get_base64_image(IMAGE_FILE)

bg_style = ""
if img_base64:
    bg_style = f"""
    .stApp {{
        background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), url("data:image/jpeg;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    """
else:
    bg_style = """
    .stApp {
        background-color: #0b0b0b;
    }
    """

st.markdown(
    f"""
    <style>
    {bg_style}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px 14px;
        color: white;
    }}
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
    }}
    .food-box {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px 16px;
        color: #ffffff;
        font-size: 16px;
        line-height: 1.5;
        margin-top: 10px;
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
        font-size: 12px;
        background-color: rgba(20, 20, 20, 0.9);
        padding: 8px 6px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

EXCEL_FILE = "fitness_entries.xlsx"

# Норми під вагу 89 кг
TARGET_PROTEIN = 160
TARGET_FAT = 70
TARGET_CARBS = 180
BASE_CALORIE_TARGET = 1990

DAYS_UA = {
    "Monday": "Понеділок",
    "Tuesday": "Вівторок",
    "Wednesday": "Середа",
    "Thursday": "Четвер",
    "Friday": "П’ятниця",
    "Saturday": "Субота",
    "Sunday": "Неділя",
}

if "redo_stack" not in st.session_state:
    st.session_state["redo_stack"] = []

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Не знайдено API ключ!")
    st.stop()

client = genai.Client(api_key=api_key)

st.title("🏋️ Мій фітнес (89 кг)")

with st.container(border=True):
    user_input = st.text_input(
        "📥 Введи, що зїв / тренування:",
        placeholder=(
            "Наприклад: з'їв 30г хліба, спалено 300 ккал або Калорії 161"
        ),
    )
    submit_btn = st.button("Записати", type="primary", use_container_width=True)

now = datetime.now()
date_str = now.strftime("%Y-%m-%d")
time_str = now.strftime("%H:%M")


def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    return pd.DataFrame(
        columns=[
            "Дата",
            "Час",
            "Опис",
            "Тип",
            "Спожито",
            "Спалено",
            "Білки",
            "Жири",
            "Вуглеводи",
        ]
    )


df_data = load_data()

if submit_btn and user_input:
    prompt = f"""Аналізуй текст: "{user_input}". 
    Визнач, чи це їжа/калорії які людина спожила, чи це спалені калорії на тренуванні/активності.
    Якщо в тексті є слова "спалено", "тренування", "калорії" у контексті витрати чи просто цифра тренування — записуй їх у kcal_burned. Якщо це їжа — розрахуй спожиті калорії (total_consumed_kcal) та грами БЖВ (total_protein, total_fat, total_carbs) на основі вказаної ваги продуктів.
    Поверни JSON із полями: 
    food_description (опис), 
    kcal_burned (спалені калорії або 0), 
    total_consumed_kcal (спожиті калорії або 0), 
    total_protein (грами білків), 
    total_fat (грами жирів), 
    total_carbs (грами вуглеводів)."""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        data = json.loads(response.text)

        c_consumed = float(data.get("total_consumed_kcal") or 0)
        c_burned = float(data.get("kcal_burned") or 0)
        c_protein = float(data.get("total_protein") or 0)
        c_fat = float(data.get("total_fat") or 0)
        c_carbs = float(data.get("total_carbs") or 0)
        c_desc = str(data.get("food_description") or user_input)

        entry_type = "Тренування" if c_burned > 0 else "Їжа"
        if c_burned > 0 and c_consumed == 0:
            c_desc = f"Тренування ({c_burned} ккал)"

        new_entry = pd.DataFrame(
            [
                {
                    "Дата": date_str,
                    "Час": time_str,
                    "Опис": c_desc,
                    "Тип": entry_type,
                    "Спожито": c_consumed,
                    "Спалено": c_burned,
                    "Білки": c_protein,
                    "Жири": c_fat,
                    "Вуглеводи": c_carbs,
                }
            ]
        )

        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        st.session_state["redo_stack"] = []
        st.success("✅ Записано!")
        st.rerun()
    except Exception as e:
        st.error(f"Помилка запиту до API: {e}")

today_df = df_data[df_data["Дата"].astype(str) == date_str]

consumed = today_df["Спожито"].sum()
burned = today_df["Спалено"].sum()
protein = today_df["Білки"].sum()
fat = today_df["Жири"].sum()
carbs = today_df["Вуглеводи"].sum()

if not today_df.empty:
    st.markdown(f"**📅 {date_str} ({DAYS_UA.get(now.strftime('%A'))})**")

    p_kcal = protein * 4
    f_kcal = fat * 9
    c_kcal = carbs * 4
    total_macro_kcal = p_kcal + f_kcal + c_kcal

    if total_macro_kcal > 0:
        p_pct = round((p_kcal / total_macro_kcal) * 100)
        f_pct = round((f_kcal / total_macro_kcal) * 100)
        p_deg = int((p_pct / 100) * 360)
        f_deg = p_deg + int((f_pct / 100) * 360)
        gradient_style = f"background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg 360deg);"
    else:
        gradient_style = "background: #333;"

    percent_target = min(100, int((consumed / BASE_CALORIE_TARGET) * 100))

    st.markdown(
        f"""
        <div class="donut-container">
            <div class="donut-ring" style="{gradient_style}">
                <div class="donut-hole">
                    <span style="font-size: 20px; font-weight: bold;">{int(consumed)}</span>
                    <span style="font-size: 11px; color: #aaa;">із {BASE_CALORIE_TARGET} ккал</span>
                    <span style="font-size: 12px; color: #4CAF50; margin-top: 2px;"><b>{percent_target}% від норми</b></span>
                </div>
            </div>
            <div class="macros-row">
                <span style="color:#36A2EB;">🥩 Білки: <b>{protein:.0f}/{TARGET_PROTEIN}г</b></span>
                <span style="color:#FFCE56;">🥑 Жири: <b>{fat:.0f}/{TARGET_FAT}г</b></span>
                <span style="color:#FF6384;">🍞 Вугл: <b>{carbs:.0f}/{TARGET_CARBS}г</b></span>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    c1.metric("🍽️ З'їв за день", f"{int(consumed)} ккал")
    c2.metric("💪 Спалено", f"{int(burned)} ккал")

    log_lines = []
    for _, row in today_df.iterrows():
        icon = "💪" if row["Тип"] == "Тренування" else "🍽️"
        kcal_val = (
            row["Спалено"] if row["Тип"] == "Тренування" else row["Спожито"]
        )
        log_lines.append(
            f"• {row['Час']} {icon} {row['Опис']} — <b>{int(kcal_val)} ккал</b>"
        )

    st.markdown(
        f"""
        <div class="food-box">
            <b>📝 Лог за сьогодні:</b><br>
            {"<br>".join(log_lines)}
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    col_undo, col_redo, col_clear = st.columns(3)

    with col_undo:
        if st.button("↩️ Назад", type="secondary", use_container_width=True):
            if not df_data.empty:
                last_entry = df_data.iloc[-1:]
                st.session_state["redo_stack"].append(last_entry)
                if len(st.session_state["redo_stack"]) > 10:
                    st.session_state["redo_stack"].pop(0)

                df_data = df_data.iloc[:-1]
                df_data.to_excel(EXCEL_FILE, index=False)
                st.success("Скасовано!")
                st.rerun()

    with col_redo:
        has_redo = len(st.session_state["redo_stack"]) > 0
        if st.button(
            "↪️ Вперед",
            type="secondary",
            use_container_width=True,
            disabled=not has_redo,
        ):
            if has_redo:
                restored_entry = st.session_state["redo_stack"].pop()
                df_data = pd.concat([df_data, restored_entry], ignore_index=True)
                df_data.to_excel(EXCEL_FILE, index=False)
                st.success("Повернуто!")
                st.rerun()

    with col_clear:
        if st.button("⚠️ Очистити", type="primary", use_container_width=True):
            df_data = df_data[df_data["Дата"].astype(str) != date_str]
            df_data.to_excel(EXCEL_FILE, index=False)
            st.session_state["redo_stack"] = []
            st.success("День очищено!")
            st.rerun()
