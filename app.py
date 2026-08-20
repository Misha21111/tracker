import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
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
    page_icon="🏋️",
    layout="centered"
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
WATCH_FILE = f"watch_data_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"

IMAGE_URL = (
    "https://i.postimg.cc/kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-image:
            linear-gradient(
                rgba(0,0,0,.72),
                rgba(0,0,0,.88)
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

    .block-container {{
        max-width: 900px;
        padding-top: 1rem;
        padding-bottom: 4rem;
    }}

    /* Заголовки */

    .section-title {{
        font-size: 1.35rem;
        font-weight: 900;
        margin: 12px 0;
        color: white;
    }}

    /* Основні блоки */

    .main-box {{
        background: rgba(12,14,20,.84);
        border: 1px solid rgba(255,255,255,.15);
        border-radius: 22px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 12px 35px rgba(0,0,0,.30);
    }}

    /* Кнопки */

    div.stButton > button {{
        min-height: 46px;
        border-radius: 14px;
        font-weight: 800;
        border: 1px solid rgba(255,255,255,.16);
        background: rgba(28,30,40,.94);
        transition:
            transform .08s ease,
            filter .08s ease,
            box-shadow .08s ease;
    }}

    div.stButton > button:hover {{
        filter: brightness(1.12);
        border-color: rgba(255,255,255,.30);
    }}

    div.stButton > button:active {{
        transform: translateY(3px) scale(.975);
        filter: brightness(.78);
        box-shadow:
            inset 0 4px 9px rgba(0,0,0,.45);
    }}

    /* Поля */

    div[data-baseweb="input"] {{
        border-radius: 14px !important;
    }}

    div[data-baseweb="select"] {{
        border-radius: 14px !important;
    }}

    /* Статистика */

    .stats-grid {{
        display: grid;
        grid-template-columns:
            repeat(3, 1fr);
        gap: 9px;
        margin-top: 14px;
    }}

    .stat-box {{
        background: rgba(20,22,30,.88);
        border:
            1px solid
            rgba(255,255,255,.10);
        border-radius: 15px;
        padding: 11px 7px;
        text-align: center;
    }}

    .stat-title {{
        color: #aeb4c0;
        font-size: 11px;
    }}

    .stat-value {{
        color: white;
        font-size: 15px;
        font-weight: 900;
        margin-top: 3px;
    }}

    /* Макроси */

    .macro-grid {{
        display: grid;
        grid-template-columns:
            repeat(3, 1fr);
        gap: 8px;
        margin-top: 13px;
    }}

    .macro {{
        background:
            rgba(18,20,27,.92);
        border:
            1px solid
            rgba(255,255,255,.10);
        border-radius: 14px;
        padding: 9px 5px;
        text-align: center;
        color: white;
        font-size: 12px;
    }}

    .macro-value {{
        font-size: 14px;
        font-weight: 900;
        margin-top: 3px;
    }}

    /* Лог */

    .log-card {{
        background:
            rgba(10,12,17,.86);
        border:
            1px solid
            rgba(255,255,255,.14);
        border-radius: 18px;
        padding: 15px;
        margin: 10px 0;
    }}

    .log-top {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
    }}

    .log-time {{
        font-size: 16px;
        font-weight: 900;
        color: white;
    }}

    .log-description {{
        margin-top: 5px;
        color: white;
        font-size: 15px;
        font-weight: 700;
        line-height: 1.4;
    }}

    .log-kcal {{
        color: #36A2EB;
        font-size: 16px;
        font-weight: 900;
        white-space: nowrap;
    }}

    .product-list {{
        margin-top: 10px;
        padding-top: 9px;
        border-top:
            1px solid
            rgba(255,255,255,.08);
        color: #d9dde6;
        font-size: 13px;
        line-height: 1.6;
    }}

    .product-kcal {{
        color: #36A2EB;
        font-weight: 800;
    }}

    /* Мобільна версія */

    @media (max-width: 600px) {{

        .stats-grid {{
            grid-template-columns:
                repeat(2, 1fr);
        }}

        .macro-grid {{
            grid-template-columns:
                1fr;
        }}

    }}

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# СТАН
# =========================================================

if "edit_mode" not in st.session_state:
    st.session_state["edit_mode"] = False

if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""


# =========================================================
# КОЛОНКИ ДАНИХ
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
    "Продукти"
]


# =========================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# =========================================================

def empty_df():
    return pd.DataFrame(columns=COLUMNS)


def to_number(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def load_settings():

    default = {
        "calories": 2000,
        "protein": 160,
        "fat": 70,
        "carbs": 180,
        "bmr_daily": 1850,
        "initial_weight": 89.0
    }

    if os.path.exists(SETTINGS_FILE):

        try:

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            return {
                **default,
                **data
            }

        except Exception:
            pass

    return default


def save_settings(settings):

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            settings,
            file,
            ensure_ascii=False,
            indent=2
        )


def load_data():

    if not os.path.exists(EXCEL_FILE):
        return empty_df()

    try:

        df = pd.read_excel(EXCEL_FILE)

    except Exception:

        return empty_df()

    for column in COLUMNS:

        if column not in df.columns:
            df[column] = ""

    for column in [
        "Спожито",
        "Спалено",
        "Білки",
        "Жири",
        "Вуглеводи"
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0.0)

    df["Дата"] = df["Дата"].astype(str)
    df["Час"] = df["Час"].astype(str).str[:5]
    df["Продукти"] = df["Продукти"].fillna("")

    return df[COLUMNS]


def save_data(df):

    df.to_excel(
        EXCEL_FILE,
        index=False
    )


def load_watch():

    if not os.path.exists(WATCH_FILE):
        return {}

    try:

        with open(
            WATCH_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def save_watch(data):

    with open(
        WATCH_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def load_trash():

    if not os.path.exists(TRASH_FILE):
        return []

    try:

        with open(
            TRASH_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def save_trash(data):

    # Максимум 10 останніх дій
    data = data[-10:]

    with open(
        TRASH_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# РОЗРАХУНОК ВАГИ
# =========================================================

def calculate_current_weight(
    df,
    settings,
    watch
):

    initial_weight = to_number(
        settings.get(
            "initial_weight",
            89.0
        )
    )

    bmr_daily = to_number(
        settings.get(
            "bmr_daily",
            1850
        )
    )

    if df.empty and not watch:
        return initial_weight

    dates = set()

    if not df.empty:
        dates.update(
            df["Дата"]
            .astype(str)
            .tolist()
        )

    dates.update(
        str(x)
        for x in watch.keys()
    )

    total_balance = 0.0

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    for date_string in dates:

        if not df.empty:

            day_df = df[
                df["Дата"].astype(str)
                == str(date_string)
            ]

        else:

            day_df = empty_df()

        consumed = (
            float(day_df["Спожито"].sum())
            if not day_df.empty
            else 0.0
        )

        watch_kcal = to_number(
            watch.get(
                str(date_string),
                0
            )
        )

        if str(date_string) == today:

            now = datetime.now(
                LOCAL_TZ
            )

            hours = (
                now.hour
                + now.minute / 60
            )

            bmr = (
                bmr_daily
                * hours
                / 24
            )

        else:

            bmr = bmr_daily

        burned = bmr + watch_kcal

        total_balance += (
            burned - consumed
        )

    # 7700 ккал ≈ 1 кг
    calculated = (
        initial_weight
        - total_balance / 7700
    )

    return max(
        0.0,
        calculated
    )


# =========================================================
# GEMINI
# =========================================================

try:

    api_key = (
        st.secrets.get("GEMINI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )

except Exception:

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )


if not api_key:

    st.error(
        "⚠️ Не знайдено GEMINI_API_KEY."
    )

    st.stop()


client = genai.Client(
    api_key=api_key
)


def analyze_text(text):

    prompt = f"""
Ти аналізуєш харчування або тренування.

Запис користувача:
{text}

Поверни ТІЛЬКИ JSON:

{{
  "type": "food",
  "description": "короткий опис",
  "total_consumed_kcal": 0,
  "burned_kcal": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0,
  "items": [
    {{
      "name": "назва продукту",
      "kcal": 0
    }}
  ]
}}

Правила:

1. Якщо це їжа:
- порахуй загальні ккал;
- білки;
- жири;
- вуглеводи;
- КОЖЕН продукт окремо;
- для кожного продукту обов'язково kcal.

2. Якщо це тренування:
- type = "exercise";
- total_consumed_kcal = 0;
- burned_kcal = оцінка спалених калорій.

3. Не додавай продукти,
яких користувач не називав.

4. Якщо вага продукту не вказана,
використай нормальну порцію.

5. Відповідь тільки JSON.
"""

    response = client.models.generate_content(

        # Саме Gemini 3.6
        model="gemini-3.6-flash",

        contents=prompt,

        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(
        response.text
    )


# =========================================================
# ЗАВАНТАЖЕННЯ
# =========================================================

settings = load_settings()
df = load_data()
watch = load_watch()

calculated_weight = calculate_current_weight(
    df,
    settings,
    watch
)


# =========================================================
# ЗАГОЛОВОК
# =========================================================

st.markdown(
    f"""
    <div class="main-box">

        <div style="
            font-size:28px;
            font-weight:900;
        ">
            🏋️ Мій Фітнес
        </div>

        <div style="
            font-size:16px;
            margin-top:5px;
            color:#d5d9e2;
        ">
            ⚖️ Поточна вага:
            <b>{calculated_weight:.1f} кг</b>
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ВВЕДЕННЯ ЇЖІ
# =========================================================

st.markdown(
    '<div class="section-title">🍽️ Додати у влог</div>',
    unsafe_allow_html=True
)

user_input = st.text_input(
    "Що з'їв або яке тренування?",
    key="input_text",
    placeholder=(
        "Напр.: 200 г курки, "
        "150 г рису і яблуко"
    ),
    label_visibility="collapsed"
)


col_add, col_cancel = st.columns(2)


with col_add:

    add_button = st.button(
        "✅ Додати",
        type="primary",
        use_container_width=True
    )


with col_cancel:

    cancel_button = st.button(
        "↩️ Відмінити",
        use_container_width=True
    )


# Відмінити введений текст
if cancel_button:

    st.session_state["input_text"] = ""

    st.rerun()


# =========================================================
# ДОДАВАННЯ ЗАПИСУ
# =========================================================

if add_button:

    text = st.session_state.get(
        "input_text",
        ""
    ).strip()

    if not text:

        st.warning(
            "Спочатку введи продукт "
            "або тренування."
        )

    else:

        try:

            data = analyze_text(
                text
            )

            now = datetime.now(
                LOCAL_TZ
            )

            items = data.get(
                "items",
                []
            )

            product_lines = []

            for item in items:

                name = str(
                    item.get(
                        "name",
                        ""
                    )
                ).strip()

                kcal = to_number(
                    item.get(
                        "kcal",
                        0
                    )
                )

                if name:

                    product_lines.append(
                        f"{name} — {kcal:.0f} ккал"
                    )

            entry = {

                "Дата":
                    now.strftime(
                        "%Y-%m-%d"
                    ),

                "Час":
                    now.strftime(
                        "%H:%M"
                    ),

                "Опис":
                    data.get(
                        "description"
                    )
                    or text,

                "Тип":
                    (
                        "Тренування"
                        if data.get(
                            "type"
                        ) == "exercise"
                        else "Їжа"
                    ),

                "Спожито":
                    to_number(
                        data.get(
                            "total_consumed_kcal",
                            0
                        )
                    ),

                "Спалено":
                    to_number(
                        data.get(
                            "burned_kcal",
                            0
                        )
                    ),

                "Білки":
                    to_number(
                        data.get(
                            "protein",
                            0
                        )
                    ),

                "Жири":
                    to_number(
                        data.get(
                            "fat",
                            0
                        )
                    ),

                "Вуглеводи":
                    to_number(
                        data.get(
                            "carbs",
                            0
                        )
                    ),

                "Продукти":
                    "\n".join(
                        product_lines
                    )
            }

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [entry]
                    )
                ],
                ignore_index=True
            )

            save_data(df)

            # ВАЖЛИВО:
            # після OK поле очищається
            st.session_state[
                "input_text"
            ] = ""

            st.rerun()

        except Exception as error:

            st.error(
                f"Помилка Gemini: {error}"
            )


st.divider()


# =========================================================
# ВИБІР ДНЯ
# =========================================================

today = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")

available_dates = [today]

if not df.empty:

    for date_value in sorted(
        df["Дата"]
        .astype(str)
        .unique(),
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
# КАЛОРІЇ З ГОДИННИКА
# =========================================================

st.markdown(
    '<div class="section-title">⌚ Калорії з годинника</div>',
    unsafe_allow_html=True
)

current_watch = to_number(
    watch.get(
        selected_date,
        0
    )
)


watch_col1, watch_col2 = st.columns(
    [4, 1]
)


with watch_col1:

    watch_value = st.number_input(
        "Спалено сьогодні, ккал",
        min_value=0.0,
        value=current_watch,
        step=10.0,
        key=f"watch_value_{selected_date}"
    )


with watch_col2:

    st.write("")

    update_watch = st.button(
        "🔄 Оновити",
        use_container_width=True
    )


if update_watch:

    # =====================================================
    # ГОЛОВНЕ:
    # НЕ +=
    # А ПОВНА ЗАМІНА ЗНАЧЕННЯ
    # =====================================================

    watch[selected_date] = float(
        watch_value
    )

    save_watch(watch)

    st.rerun()


# =========================================================
# СТАТИСТИКА
# =========================================================

day_df = df[
    df["Дата"].astype(str)
    == str(selected_date)
].copy()


consumed = (
    float(day_df["Спожито"].sum())
    if not day_df.empty
    else 0.0
)

protein = (
    float(day_df["Білки"].sum())
    if not day_df.empty
    else 0.0
)

fat = (
    float(day_df["Жири"].sum())
    if not day_df.empty
    else 0.0
)

carbs = (
    float(day_df["Вуглеводи"].sum())
    if not day_df.empty
    else 0.0
)


watch_burned = to_number(
    watch.get(
        selected_date,
        0
    )
)


bmr_daily = to_number(
    settings.get(
        "bmr_daily",
        1850
    )
)


if selected_date == today:

    now = datetime.now(
        LOCAL_TZ
    )

    hours = (
        now.hour
        + now.minute / 60
    )

    bmr_today = (
        bmr_daily
        * hours
        / 24
    )

else:

    bmr_today = bmr_daily


total_burned = (
    bmr_today
    + watch_burned
)


balance = (
    total_burned
    - consumed
)


target_calories = to_number(
    settings.get(
        "calories",
        2000
    )
)


# =========================================================
# КОЛЬОРОВІ СЕКТОРИ
# =========================================================

macro_total = (
    protein
    + fat
    + carbs
)

if macro_total > 0:

    protein_deg = (
        protein
        / macro_total
        * 360
    )

    fat_deg = (
        protein_deg
        + fat
        / macro_total
        * 360
    )

else:

    protein_deg = 0
    fat_deg = 0


# =========================================================
# ДЕФІЦИТ / ПРОФІЦИТ
# =========================================================

if balance >= 0:

    balance_text = (
        f"Дефіцит: {balance:.0f} ккал"
    )

    balance_color = "#43e97b"

else:

    balance_text = (
        f"Профіцит: "
        f"{abs(balance):.0f} ккал"
    )

    balance_color = "#ff5f6d"


# =========================================================
# СПРАВЖНІЙ КРУЖОК
# =========================================================

donut_html = f"""
<!DOCTYPE html>

<html>

<head>

<style>

body {{
    margin:0;
    background:transparent;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    color:white;
}}

.wrapper {{
    width:100%;
    display:flex;
    justify-content:center;
}}

.card {{
    width:100%;
    box-sizing:border-box;

    background:
        rgba(10,12,17,.84);

    border:
        1px solid
        rgba(255,255,255,.14);

    border-radius:22px;

    padding:18px;

    text-align:center;
}}

.title {{
    font-size:21px;
    font-weight:900;
    margin-bottom:12px;
}}

.donut-wrap {{
    display:flex;
    justify-content:center;
    align-items:center;
}}

.donut {{

    width:230px;
    height:230px;

    border-radius:50%;

    background:
        conic-gradient(
            #36A2EB 0deg {protein_deg}deg,
            #FFCE56 {protein_deg}deg {fat_deg}deg,
            #FF6384 {fat_deg}deg 360deg
        );

    display:flex;
    align-items:center;
    justify-content:center;

    box-shadow:
        0 0 30px
        rgba(0,0,0,.50);
}}

.hole {{

    width:154px;
    height:154px;

    border-radius:50%;

    background:
        rgba(12,14,20,.98);

    display:flex;
    flex-direction:column;

    align-items:center;
    justify-content:center;

    text-align:center;
}}

.balance {{
    color:{balance_color};
    font-size:14px;
    font-weight:900;
    margin-bottom:5px;
}}

.main {{
    font-size:30px;
    font-weight:900;
    line-height:1;
}}

.sub {{
    margin-top:5px;
    color:#9ca3af;
    font-size:12px;
}}

.macros {{
    display:grid;
    grid-template-columns:
        repeat(3,1fr);

    gap:8px;

    margin-top:15px;
}}

.macro {{
    background:
        rgba(20,22,30,.90);

    border:
        1px solid
        rgba(255,255,255,.10);

    border-radius:13px;

    padding:9px 4px;

    font-size:12px;
}}

.value {{
    display:block;
    font-size:14px;
    font-weight:900;
    margin-top:3px;
}}

</style>

</head>

<body>

<div class="wrapper">

<div class="card">

<div class="title">
📊 Баланс дня
</div>

<div class="donut-wrap">

<div class="donut">

<div class="hole">

<div class="balance">
{balance_text}
</div>

<div class="main">
{consumed:.0f}
</div>

<div class="sub">
ккал із {target_calories:.0f}
</div>

</div>

</div>

</div>


<div class="macros">

<div class="macro">

🥩 Білки

<span class="value">
{protein:.0f} / {settings.get("protein",160):.0f} г
</span>

</div>


<div class="macro">

🥑 Жири

<span class="value">
{fat:.0f} / {settings.get("fat",70):.0f} г
</span>

</div>


<div class="macro">

🍞 Вуглеводи

<span class="value">
{carbs:.0f} / {settings.get("carbs",180):.0f} г
</span>

</div>

</div>

</div>

</div>

</body>

</html>
"""


components.html(
    donut_html,
    height=390,
    scrolling=False
)


# =========================================================
# СТАТИСТИКА
# =========================================================

st.markdown(
    f"""
    <div class="stats-grid">

        <div class="stat-box">

            <div class="stat-title">
                ⌚ Годинник
            </div>

            <div class="stat-value">
                {watch_burned:.0f} ккал
            </div>

        </div>


        <div class="stat-box">

            <div class="stat-title">
                🔥 Витрата
            </div>

            <div class="stat-value">
                {total_burned:.0f} ккал
            </div>

        </div>


        <div class="stat-box">

            <div class="stat-title">
                ⚖️ Вага
            </div>

            <div class="stat-value">
                {calculated_weight:.1f} кг
            </div>

        </div>

    </div>
    """,
    unsafe_allow_html=True
)


st.divider()


# =========================================================
# КНОПКИ
# =========================================================

button_1, button_2, button_3 = st.columns(3)


with button_1:

    settings_button = st.button(
        "⚙️ Налаштування",
        use_container_width=True
    )


with button_2:

    undo_button = st.button(
        "↩️ Відмінити",
        use_container_width=True
    )


with button_3:

    clear_button = st.button(
        "🗑️ Очистити день",
        use_container_width=True
    )


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

if settings_button:

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


if st.session_state["edit_mode"]:

    st.markdown(
        '<div class="section-title">✏️ Редактор цілей</div>',
        unsafe_allow_html=True
    )

    with st.form(
        "settings_form"
    ):

        new_calories = st.number_input(
            "🎯 Калорії",
            value=int(
                settings.get(
                    "calories",
                    2000
                )
            ),
            step=10
        )

        new_protein = st.number_input(
            "🥩 Білки, г",
            value=int(
                settings.get(
                    "protein",
                    160
                )
            ),
            step=5
        )

        new_fat = st.number_input(
            "🥑 Жири, г",
            value=int(
                settings.get(
                    "fat",
                    70
                )
            ),
            step=5
        )

        new_carbs = st.number_input(
            "🍞 Вуглеводи, г",
            value=int(
                settings.get(
                    "carbs",
                    180
                )
            ),
            step=5
        )

        new_bmr = st.number_input(
            "🔥 Добова витрата BMR, ккал",
            value=int(
                settings.get(
                    "bmr_daily",
                    1850
                )
            ),
            step=50
        )

        new_weight = st.number_input(
            "⚖️ Початкова вага, кг",
            value=float(
                settings.get(
                    "initial_weight",
                    89
                )
            ),
            min_value=0.0,
            step=0.1
        )

        save_settings_button = (
            st.form_submit_button(
                "💾 Зберегти",
                type="primary",
                use_container_width=True
            )
        )

    if save_settings_button:

        settings = {

            "calories":
                new_calories,

            "protein":
                new_protein,

            "fat":
                new_fat,

            "carbs":
                new_carbs,

            "bmr_daily":
                new_bmr,

            "initial_weight":
                new_weight
        }

        save_settings(
            settings
        )

        st.session_state[
            "edit_mode"
        ] = False

        st.rerun()


# =========================================================
# ВІДМІНА ОСТАННІХ 10 ДІЙ
# =========================================================

if undo_button:

    trash = load_trash()

    if not trash:

        st.info(
            "Немає записів для відміни."
        )

    else:

        last_deleted = trash.pop()

        restored = pd.DataFrame(
            [last_deleted]
        )

        df = pd.concat(
            [
                df,
                restored
            ],
            ignore_index=True
        )

        save_data(df)
        save_trash(trash)

        st.rerun()


# =========================================================
# ОЧИСТИТИ ДЕНЬ
# =========================================================

if clear_button:

    if day_df.empty:

        st.info(
            "У цьому дні немає записів."
        )

    else:

        trash = load_trash()

        for _, row in day_df.iterrows():

            trash.append(
                row.to_dict()
            )

        save_trash(trash)

        df = df[
            df["Дата"].astype(str)
            != str(selected_date)
        ].reset_index(
            drop=True
        )

        save_data(df)

        st.rerun()


# =========================================================
# ВЛОГ
# =========================================================

st.markdown(
    '<div class="section-title">📝 Влог</div>',
    unsafe_allow_html=True
)


if day_df.empty:

    st.info(
        "За цей день записів ще немає."
    )

else:

    for index, row in day_df.iterrows():

        original_index = int(index)

        entry_type = str(
            row["Тип"]
        )

        if entry_type == "Тренування":

            icon = "💪"

            kcal = to_number(
                row["Спалено"]
            )

        else:

            icon = "🍽️"

            kcal = to_number(
                row["Спожито"]
            )

        description = str(
            row["Опис"]
        )

        products = str(
            row.get(
                "Продукти",
                ""
            )
            or ""
        ).strip()


        # ---------------------------------------------
        # КАРТКА ЛОГУ
        # ---------------------------------------------

        products_html = ""

        if products:

            lines = products.split(
                "\n"
            )

            rendered_lines = []

            for line in lines:

                if " — " in line:

                    name, kcal_text = (
                        line.rsplit(
                            " — ",
                            1
                        )
                    )

                    rendered_lines.append(
                        f"""
                        <div>
                            {name}
                            <span class="product-kcal">
                                — {kcal_text}
                            </span>
                        </div>
                        """
                    )

                else:

                    rendered_lines.append(
                        f"<div>{line}</div>"
                    )

            products_html = (
                '<div class="product-list">'
                + "".join(
                    rendered_lines
                )
                + "</div>"
            )


        st.markdown(
            f"""
            <div class="log-card">

                <div class="log-top">

                    <div>

                        <div class="log-time">
                            {str(row["Час"])[:5]}
                            {icon}
                        </div>

                        <div class="log-description">
                            {description}
                        </div>

                    </div>

                    <div class="log-kcal">
                        {kcal:+.0f} ккал
                    </div>

                </div>

                {products_html}

            </div>
            """,
            unsafe_allow_html=True
        )


        # ---------------------------------------------
        # РЕДАКТОР ЗАПИСУ
        # ---------------------------------------------

        with st.expander(
            "✏️ Редагувати"
        ):

            new_description = st.text_input(
                "Опис",
                value=description,
                key=f"description_{original_index}"
            )

            edit_col1, edit_col2 = st.columns(2)

            with edit_col1:

                new_kcal = st.number_input(
                    "🔥 Калорії",
                    value=float(
                        row["Спожито"]
                        if entry_type == "Їжа"
                        else row["Спалено"]
                    ),
                    min_value=0.0,
                    step=1.0,
                    key=f"kcal_{original_index}"
                )

                new_protein = st.number_input(
                    "🥩 Білки, г",
                    value=float(
                        row["Білки"]
                    ),
                    min_value=0.0,
                    step=0.1,
                    key=f"protein_{original_index}"
                )

            with edit_col2:

                new_fat = st.number_input(
                    "🥑 Жири, г",
                    value=float(
                        row["Жири"]
                    ),
                    min_value=0.0,
                    step=0.1,
                    key=f"fat_{original_index}"
                )

                new_carbs = st.number_input(
                    "🍞 Вуглеводи, г",
                    value=float(
                        row["Вуглеводи"]
                    ),
                    min_value=0.0,
                    step=0.1,
                    key=f"carbs_{original_index}"
                )


            save_entry_button = st.button(
                "💾 Зберегти запис",
                key=f"save_entry_{original_index}",
                type="primary",
                use_container_width=True
            )


            if save_entry_button:

                df.loc[
                    original_index,
                    "Опис"
                ] = new_description

                if entry_type == "Їжа":

                    df.loc[
                        original_index,
                        "Спожито"
                    ] = new_kcal

                else:

                    df.loc[
                        original_index,
                        "Спалено"
                    ] = new_kcal

                df.loc[
                    original_index,
                    "Білки"
                ] = new_protein

                df.loc[
                    original_index,
                    "Жири"
                ] = new_fat

                df.loc[
                    original_index,
                    "Вуглеводи"
                ] = new_carbs

                save_data(df)

                st.rerun()


        # ---------------------------------------------
        # ВИДАЛЕННЯ ОКРЕМОГО ЗАПИСУ
        # ---------------------------------------------

        if st.button(
            "🗑️ Видалити запис",
            key=f"delete_{original_index}",
            use_container_width=True
        ):

            trash = load_trash()

            trash.append(
                row.to_dict()
            )

            save_trash(
                trash
            )

            df = df.drop(
                index=original_index
            ).reset_index(
                drop=True
            )

            save_data(df)

            st.rerun()


# =========================================================
# НИЖНЯ ІНФОРМАЦІЯ
# =========================================================

st.divider()

st.caption(
    "⚖️ 7700 ккал накопиченого "
    "дефіциту ≈ 1 кг. "
    "Вага перераховується автоматично "
    "після зміни їжі або калорій годинника."
)
