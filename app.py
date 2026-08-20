import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


# =========================================================
# ЧАСОВИЙ ПОЯС
# =========================================================

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


# =========================================================
# НАЛАШТУВАННЯ STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# =========================================================
# ПРОФІЛЬ
# =========================================================

user_profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"]
)

profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
UNDO_FILE = f"fitness_undo_{profile_prefix}.json"


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    #MainMenu,
    footer,
    header {
        visibility: hidden;
    }

    .stApp {
        background:
            linear-gradient(
                rgba(0, 0, 0, 0.72),
                rgba(0, 0, 0, 0.88)
            ),
            url("https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg");

        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    .block-container {
        max-width: 760px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .title-box {
        background: rgba(15, 17, 22, 0.88);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 22px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.30);
    }

    .title-main {
        font-size: 28px;
        font-weight: 800;
        color: white;
        margin-bottom: 4px;
    }

    .title-sub {
        font-size: 15px;
        color: rgba(255,255,255,0.65);
    }

    .stats-card {
        background: rgba(15,17,22,0.90);
        border: 1px solid rgba(255,255,255,0.11);
        border-radius: 22px;
        padding: 22px 16px;
        margin: 14px 0;
        box-shadow: 0 8px 30px rgba(0,0,0,0.30);
    }

    .donut-wrap {
        width: 220px;
        height: 220px;
        margin: 8px auto 18px auto;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow:
            0 0 25px rgba(54,162,235,0.16),
            0 0 50px rgba(0,0,0,0.45);
    }

    .donut-hole {
        width: 148px;
        height: 148px;
        border-radius: 50%;
        background: rgba(14,16,21,0.98);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: white;
        border: 1px solid rgba(255,255,255,0.08);
    }

    .donut-kcal {
        font-size: 25px;
        font-weight: 850;
        line-height: 1.15;
    }

    .donut-target {
        font-size: 13px;
        color: rgba(255,255,255,0.60);
        margin-top: 3px;
    }

    .balance {
        font-size: 13px;
        font-weight: 700;
        margin-top: 8px;
    }

    .macro-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-top: 12px;
    }

    .macro {
        background: rgba(255,255,255,0.055);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 11px 5px;
        text-align: center;
    }

    .macro-name {
        font-size: 12px;
        color: rgba(255,255,255,0.58);
    }

    .macro-value {
        font-size: 15px;
        font-weight: 800;
        color: white;
        margin-top: 3px;
    }

    .weight-box {
        text-align: center;
        margin-top: 12px;
        color: rgba(255,255,255,0.75);
        font-size: 14px;
    }

    .log-title {
        font-size: 20px;
        font-weight: 800;
        color: white;
        margin: 22px 0 10px 0;
    }

    .log-card {
        background: rgba(15,17,22,0.88);
        border: 1px solid rgba(255,255,255,0.11);
        border-radius: 18px;
        padding: 15px;
        margin: 10px 0;
    }

    .log-time {
        color: rgba(255,255,255,0.55);
        font-size: 13px;
    }

    .log-description {
        color: white;
        font-size: 16px;
        font-weight: 700;
        margin-top: 3px;
    }

    .log-kcal {
        color: #4db8ff;
        font-size: 16px;
        font-weight: 850;
        text-align: right;
        white-space: nowrap;
    }

    .watch-box {
        background: rgba(25,28,35,0.90);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 18px;
        padding: 15px;
        margin: 14px 0;
    }

    .section-title {
        color: white;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 10px;
    }

    div[data-testid="stButton"] button {
        border-radius: 14px;
        min-height: 46px;
        font-weight: 700;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 14px;
    }

    div[data-testid="stNumberInput"] input {
        border-radius: 14px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# СТАН
# =========================================================

if "undo_stack" not in st.session_state:
    st.session_state["undo_stack"] = []

if "last_editor_signature" not in st.session_state:
    st.session_state["last_editor_signature"] = None

if "settings_open" not in st.session_state:
    st.session_state["settings_open"] = False


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

def default_settings():
    return {
        "calories": 2000,
        "protein": 160,
        "fat": 70,
        "carbs": 180,
        "bmr_daily": 1850,
        "initial_weight": 89.0,
    }


def load_settings():
    defaults = default_settings()

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)

            if isinstance(saved, dict):
                defaults.update(saved)

        except Exception:
            pass

    return defaults


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            settings,
            f,
            ensure_ascii=False,
            indent=2
        )


user_settings = load_settings()


# =========================================================
# ДАНІ
# =========================================================

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
]


def empty_dataframe():
    return pd.DataFrame(columns=COLUMNS)


def normalize_dataframe(df):
    if df is None or df.empty:
        return empty_dataframe()

    df = df.copy()

    for col in COLUMNS:
        if col not in df.columns:
            if col in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
                df[col] = 0.0
            else:
                df[col] = ""

    df = df[COLUMNS]

    df["Дата"] = df["Дата"].astype(str)
    df["Час"] = df["Час"].astype(str)
    df["Опис"] = df["Опис"].astype(str)
    df["Тип"] = df["Тип"].astype(str)

    for col in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0.0)

    return df


def load_data():
    if not os.path.exists(EXCEL_FILE):
        return empty_dataframe()

    try:
        df = pd.read_excel(EXCEL_FILE)
        return normalize_dataframe(df)
    except Exception:
        return empty_dataframe()


def save_data(df):
    df = normalize_dataframe(df)

    df.to_excel(
        EXCEL_FILE,
        index=False
    )


df_data = load_data()


# =========================================================
# UNDO — ДО 10 ОСТАННІХ ЗМІН
# =========================================================

def dataframe_to_records(df):
    return normalize_dataframe(df).to_dict(
        orient="records"
    )


def records_to_dataframe(records):
    if not records:
        return empty_dataframe()

    return normalize_dataframe(
        pd.DataFrame(records)
    )


def push_undo(df):
    snapshot = dataframe_to_records(df)

    stack = st.session_state.get(
        "undo_stack",
        []
    )

    stack.append(snapshot)

    # Максимум 10 відмін
    stack = stack[-10:]

    st.session_state["undo_stack"] = stack


def undo_last():
    stack = st.session_state.get(
        "undo_stack",
        []
    )

    if not stack:
        return False

    previous = stack.pop()

    restored = records_to_dataframe(previous)

    save_data(restored)

    st.session_state["undo_stack"] = stack

    return True


# =========================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# =========================================================

def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def calculate_balance_for_day(
    day_df,
    settings,
    include_partial_today=False
):
    if day_df.empty:
        consumed = 0.0
        exercise = 0.0
    else:
        consumed = day_df["Спожито"].sum()
        exercise = day_df["Спалено"].sum()

    bmr_daily = safe_float(
        settings.get("bmr_daily", 1850)
    )

    if include_partial_today:
        now = datetime.now(LOCAL_TZ)

        hours = (
            now.hour +
            now.minute / 60 +
            now.second / 3600
        )

        bmr = bmr_daily / 24 * hours
    else:
        bmr = bmr_daily

    burned = bmr + exercise

    balance = burned - consumed

    return (
        float(consumed),
        float(burned),
        float(balance)
    )


def calculate_current_weight(df, settings):
    initial_weight = safe_float(
        settings.get("initial_weight", 89.0)
    )

    bmr_daily = safe_float(
        settings.get("bmr_daily", 1850)
    )

    if df.empty:
        return initial_weight

    work = normalize_dataframe(df)

    total_balance = 0.0

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    unique_dates = work["Дата"].unique()

    for date_str in unique_dates:

        day = work[
            work["Дата"] == str(date_str)
        ]

        consumed = float(
            day["Спожито"].sum()
        )

        exercise = float(
            day["Спалено"].sum()
        )

        if str(date_str) == today:
            now = datetime.now(LOCAL_TZ)

            hours = (
                now.hour +
                now.minute / 60 +
                now.second / 3600
            )

            bmr = (
                bmr_daily / 24
            ) * hours
        else:
            bmr = bmr_daily

        burned = bmr + exercise

        total_balance += burned - consumed

    # 7700 ккал ≈ 1 кг
    return initial_weight - (
        total_balance / 7700
    )


# =========================================================
# GEMINI
# =========================================================

api_key = (
    st.secrets.get("GEMINI_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
)

client = None

if api_key:
    try:
        client = genai.Client(
            api_key=api_key
        )
    except Exception:
        client = None


# =========================================================
# ЗАГОЛОВОК
# =========================================================

calculated_weight = calculate_current_weight(
    df_data,
    user_settings
)

today_str = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")

today_df = df_data[
    df_data["Дата"] == today_str
].copy()


# =========================================================
# ВЕРХ
# =========================================================

st.markdown(
    f"""
    <div class="title-box">
        <div class="title-main">
            ⚖️ Поточна вага: {calculated_weight:.1f} кг
        </div>
        <div class="title-sub">
            {today_str} · {user_profile}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ДОДАВАННЯ ЗАПИСУ
# =========================================================

st.markdown(
    '<div class="section-title">📝 Додати в лог</div>',
    unsafe_allow_html=True
)

user_input = st.text_input(
    "Що з'їв / що зробив",
    placeholder="Наприклад: 2 яйця, 150 г курки, рис 200 г"
)

add_col1, add_col2 = st.columns(
    [3, 1]
)

with add_col1:
    add_button = st.button(
        "➕ Додати в лог",
        type="primary",
        use_container_width=True
    )

with add_col2:
    undo_button = st.button(
        "↩️ Відмінити",
        use_container_width=True,
        disabled=(
            len(
                st.session_state["undo_stack"]
            ) == 0
        )
    )


# =========================================================
# UNDO
# =========================================================

if undo_button:
    if undo_last():
        st.success(
            "↩️ Останню зміну скасовано"
        )
        st.rerun()


# =========================================================
# ДОДАТИ ЧЕРЕЗ GEMINI
# =========================================================

if add_button:

    if not user_input.strip():
        st.warning(
            "Введи продукт або тренування."
        )
    elif client is None:
        st.error(
            "Не знайдено GEMINI_API_KEY. "
            "Додай ключ у Secrets."
        )
    else:

        current_time = datetime.now(
            LOCAL_TZ
        ).strftime("%H:%M")

        prompt = f"""
Ти ведеш щоденник харчування.

Проаналізуй цей запис:
"{user_input}"

Потрібно повернути ТІЛЬКИ JSON.

Формат:

{{
  "description": "короткий опис",
  "type": "Їжа",
  "consumed_kcal": 0,
  "burned_kcal": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0
}}

Правила:

1. Якщо це їжа:
   type = "Їжа"
   consumed_kcal > 0
   burned_kcal = 0

2. Якщо це тренування:
   type = "Тренування"
   burned_kcal > 0
   consumed_kcal = 0

3. Білки, жири та вуглеводи
   вказуй у грамах.

4. Якщо точну кількість неможливо визначити,
   зроби адекватну приблизну оцінку.

5. Не додавай markdown.
6. Не додавай пояснення.
"""

        try:

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            data = json.loads(
                response.text
            )

            new_row = pd.DataFrame(
                [{
                    "Дата": today_str,
                    "Час": current_time,
                    "Опис": (
                        data.get("description")
                        or user_input
                    ),
                    "Тип": (
                        data.get("type")
                        or "Їжа"
                    ),
                    "Спожито": safe_float(
                        data.get(
                            "consumed_kcal",
                            0
                        )
                    ),
                    "Спалено": safe_float(
                        data.get(
                            "burned_kcal",
                            0
                        )
                    ),
                    "Білки": safe_float(
                        data.get(
                            "protein",
                            0
                        )
                    ),
                    "Жири": safe_float(
                        data.get(
                            "fat",
                            0
                        )
                    ),
                    "Вуглеводи": safe_float(
                        data.get(
                            "carbs",
                            0
                        )
                    ),
                }]
            )

            push_undo(df_data)

            df_data = pd.concat(
                [
                    df_data,
                    new_row
                ],
                ignore_index=True
            )

            save_data(df_data)

            st.success(
                "✅ Запис додано"
            )

            st.rerun()

        except Exception as e:
            st.error(
                f"Помилка аналізу: {e}"
            )


# =========================================================
# ВИБІР ДНЯ
# =========================================================

available_dates = [today_str]

if not df_data.empty:

    for date_value in sorted(
        df_data["Дата"].astype(str).unique(),
        reverse=True
    ):
        if date_value not in available_dates:
            available_dates.append(
                date_value
            )

selected_date = st.selectbox(
    "📅 День",
    available_dates
)


# =========================================================
# ДАНІ ОБРАНОГО ДНЯ
# =========================================================

day_df = df_data[
    df_data["Дата"] == selected_date
].copy()


# =========================================================
# РЕДАГУВАННЯ
# =========================================================

st.markdown(
    '<div class="section-title">✏️ Редактор</div>',
    unsafe_allow_html=True
)

if not day_df.empty:

    editor_df = day_df.copy()

    editor_df = editor_df[
        [
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
    ]

    edited_df = st.data_editor(
        editor_df,
        key=f"editor_{selected_date}",
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Дата": st.column_config.TextColumn(
                "Дата",
                disabled=True
            ),
            "Час": st.column_config.TextColumn(
                "Час"
            ),
            "Опис": st.column_config.TextColumn(
                "Продукт / опис",
                width="large"
            ),
            "Тип": st.column_config.SelectboxColumn(
                "Тип",
                options=[
                    "Їжа",
                    "Тренування"
                ]
            ),
            "Спожито": st.column_config.NumberColumn(
                "З'їдено, ккал",
                min_value=0.0,
                step=1.0,
                format="%.0f"
            ),
            "Спалено": st.column_config.NumberColumn(
                "Спалено, ккал",
                min_value=0.0,
                step=1.0,
                format="%.0f"
            ),
            "Білки": st.column_config.NumberColumn(
                "Білки, г",
                min_value=0.0,
                step=0.1,
                format="%.1f"
            ),
            "Жири": st.column_config.NumberColumn(
                "Жири, г",
                min_value=0.0,
                step=0.1,
                format="%.1f"
            ),
            "Вуглеводи": st.column_config.NumberColumn(
                "Вуглеводи, г",
                min_value=0.0,
                step=0.1,
                format="%.1f"
            ),
        },
    )

    # -----------------------------------------------------
    # ВИЯВЛЕННЯ ЗМІН
    # -----------------------------------------------------

    original_compare = (
        normalize_dataframe(editor_df)
        .reset_index(drop=True)
    )

    edited_compare = (
        normalize_dataframe(edited_df)
        .reset_index(drop=True)
    )

    if not original_compare.equals(
        edited_compare
    ):

        # Замінюємо записи саме цього дня
        # на відредаговані записи.
        other_days = df_data[
            df_data["Дата"] != selected_date
        ].copy()

        push_undo(df_data)

        df_data = pd.concat(
            [
                other_days,
                edited_compare
            ],
            ignore_index=True
        )

        df_data = normalize_dataframe(
            df_data
        )

        save_data(df_data)

        st.rerun()

else:

    st.info(
        "За цей день записів немає."
    )


# =========================================================
# АКТУАЛЬНО ПЕРЕРАХОВУЄМО ДЕНЬ
# =========================================================

df_data = load_data()

day_df = df_data[
    df_data["Дата"] == selected_date
].copy()


# =========================================================
# СТАТИСТИКА
# =========================================================

consumed = float(
    day_df["Спожито"].sum()
) if not day_df.empty else 0.0

burned_from_entries = float(
    day_df["Спалено"].sum()
) if not day_df.empty else 0.0

protein = float(
    day_df["Білки"].sum()
) if not day_df.empty else 0.0

fat = float(
    day_df["Жири"].sum()
) if not day_df.empty else 0.0

carbs = float(
    day_df["Вуглеводи"].sum()
) if not day_df.empty else 0.0


# =========================================================
# КАЛОРІЇ ГОДИННИКА
#
# ВАЖЛИВО:
# Це ОКРЕМЕ значення.
# Воно замінює попереднє значення,
# а не додається до нього.
# =========================================================

watch_key = (
    f"watch_calories_{selected_date}"
)

saved_watch = float(
    st.session_state.get(
        watch_key,
        0.0
    )
)

if selected_date == today_str:

    st.markdown(
        """
        <div class="watch-box">
            <div class="section-title">
                ⌚ Калорії з годинника
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    watch_calories = st.number_input(
        "Спалено за годинником, ккал",
        min_value=0.0,
        value=saved_watch,
        step=10.0,
        key=f"watch_input_{selected_date}",
        help=(
            "Нове значення замінює попереднє. "
            "Воно не додається повторно."
        )
    )

    # Значення просто замінюється
    st.session_state[
        watch_key
    ] = float(watch_calories)

else:

    watch_calories = float(
        st.session_state.get(
            watch_key,
            0.0
        )
    )


# =========================================================
# ВИДАЛЯЄМО КАЛОРІЇ ГОДИННИКА З ЛОГУ
# =========================================================
#
# Якщо в редакторі є тренування,
# воно залишається окремим записом.
#
# Значення годинника НЕ накопичується.
#
# =========================================================

total_activity_burned = (
    burned_from_entries +
    watch_calories
)


# =========================================================
# BMR
# =========================================================

bmr_daily = float(
    user_settings.get(
        "bmr_daily",
        1850
    )
)

if selected_date == today_str:

    now = datetime.now(
        LOCAL_TZ
    )

    hours_passed = (
        now.hour +
        now.minute / 60 +
        now.second / 3600
    )

    bmr_used = (
        bmr_daily / 24
    ) * hours_passed

else:

    bmr_used = bmr_daily


# =========================================================
# ЗАГАЛЬНЕ СПАЛЮВАННЯ
# =========================================================

total_burned = (
    bmr_used +
    total_activity_burned
)


# =========================================================
# ДЕФІЦИТ / ПРОФІЦИТ
# =========================================================

balance = (
    total_burned -
    consumed
)


if balance >= 0:
    balance_text = (
        f"Дефіцит {abs(balance):.0f} ккал"
    )
    balance_color = "#55e88a"
else:
    balance_text = (
        f"Профіцит {abs(balance):.0f} ккал"
    )
    balance_color = "#ff7b7b"


# =========================================================
# КРУЖОК
# =========================================================

target_calories = float(
    user_settings.get(
        "calories",
        2000
    )
)

progress = (
    consumed / target_calories
    if target_calories > 0
    else 0
)

progress = max(
    0.0,
    min(progress, 1.0)
)

degrees = progress * 360


st.markdown(
    f"""
    <div class="stats-card">

        <div class="donut-wrap"
             style="
                background:
                conic-gradient(
                    #36A2EB 0deg,
                    #36A2EB {degrees}deg,
                    rgba(255,255,255,0.10) {degrees}deg,
                    rgba(255,255,255,0.10) 360deg
                );
             ">

            <div class="donut-hole">

                <div class="donut-kcal">
                    {consumed:.0f}
                </div>

                <div class="donut-target">
                    / {target_calories:.0f} ккал
                </div>

                <div class="balance"
                     style="color:{balance_color};">
                    {balance_text}
                </div>

            </div>

        </div>

        <div class="macro-grid">

            <div class="macro">
                <div class="macro-name">
                    🥩 Білки
                </div>
                <div class="macro-value">
                    {protein:.1f} / {float(user_settings.get("protein",160)):.0f} г
                </div>
            </div>

            <div class="macro">
                <div class="macro-name">
                    🥑 Жири
                </div>
                <div class="macro-value">
                    {fat:.1f} / {float(user_settings.get("fat",70)):.0f} г
                </div>
            </div>

            <div class="macro">
                <div class="macro-name">
                    🍞 Вуглеводи
                </div>
                <div class="macro-value">
                    {carbs:.1f} / {float(user_settings.get("carbs",180)):.0f} г
                </div>
            </div>

        </div>

        <div class="weight-box">
            🔥 BMR: {bmr_daily:.0f} ккал/добу
            ·
            🔥 Спалено активністю: {total_activity_burned:.0f} ккал
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ЛОГ
# =========================================================

st.markdown(
    '<div class="log-title">📝 Лог за день</div>',
    unsafe_allow_html=True
)

if day_df.empty:

    st.info(
        "Поки що немає записів."
    )

else:

    # Сортування від нових до старих
    display_df = day_df.copy()

    display_df["_sort"] = display_df[
        "Час"
    ].astype(str)

    display_df = display_df.sort_values(
        "_sort",
        ascending=False
    )

    for index, row in display_df.iterrows():

        time_value = str(
            row["Час"]
        )[:5]

        description = str(
            row["Опис"]
        )

        row_type = str(
            row["Тип"]
        )

        if row_type == "Тренування":
            icon = "💪"
            kcal_value = safe_float(
                row["Спалено"]
            )
            kcal_sign = "-"
        else:
            icon = "🍽️"
            kcal_value = safe_float(
                row["Спожито"]
            )
            kcal_sign = "+"

        st.markdown(
            f"""
            <div class="log-card">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    gap:12px;
                    align-items:flex-start;
                ">

                    <div style="flex:1;">

                        <div class="log-time">
                            {time_value} {icon}
                        </div>

                        <div class="log-description">
                            {description}
                        </div>

                    </div>

                    <div class="log-kcal">
                        {kcal_sign}{kcal_value:.0f} ккал
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

st.divider()

settings_button = st.button(
    "⚙️ Налаштування цілей",
    use_container_width=True
)

if settings_button:
    st.session_state[
        "settings_open"
    ] = not st.session_state[
        "settings_open"
    ]


if st.session_state["settings_open"]:

    st.markdown(
        '<div class="section-title">⚙️ Налаштування</div>',
        unsafe_allow_html=True
    )

    new_calories = st.number_input(
        "Добова ціль калорій",
        min_value=0,
        value=int(
            user_settings.get(
                "calories",
                2000
            )
        ),
        step=50
    )

    new_protein = st.number_input(
        "Добова ціль білків, г",
        min_value=0,
        value=int(
            user_settings.get(
                "protein",
                160
            )
        ),
        step=5
    )

    new_fat = st.number_input(
        "Добова ціль жирів, г",
        min_value=0,
        value=int(
            user_settings.get(
                "fat",
                70
            )
        ),
        step=5
    )

    new_carbs = st.number_input(
        "Добова ціль вуглеводів, г",
        min_value=0,
        value=int(
            user_settings.get(
                "carbs",
                180
            )
        ),
        step=5
    )

    new_bmr = st.number_input(
        "BMR за добу, ккал",
        min_value=0,
        value=int(
            user_settings.get(
                "bmr_daily",
                1850
            )
        ),
        step=50
    )

    new_weight = st.number_input(
        "Початкова вага, кг",
        min_value=0.0,
        value=float(
            user_settings.get(
                "initial_weight",
                89.0
            )
        ),
        step=0.1
    )

    save_settings_button = st.button(
        "💾 Зберегти налаштування",
        type="primary",
        use_container_width=True
    )

    if save_settings_button:

        save_settings(
            {
                "calories": new_calories,
                "protein": new_protein,
                "fat": new_fat,
                "carbs": new_carbs,
                "bmr_daily": new_bmr,
                "initial_weight": new_weight,
            }
        )

        st.success(
            "✅ Налаштування збережено"
        )

        st.rerun()


# =========================================================
# НИЗ
# =========================================================

st.caption(
    "Зміни в редакторі автоматично перераховують "
    "калорії, Б/Ж/В, баланс і вагу."
)
