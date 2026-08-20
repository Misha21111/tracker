import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from google import genai
from google.genai import types


# =========================================================
# ОСНОВНІ НАЛАШТУВАННЯ
# =========================================================

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="⚖️",
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
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"


# =========================================================
# GEMINI
# =========================================================

GEMINI_MODEL = "gemini-3.6-flash"


api_key = (
    st.secrets.get("GEMINI_API_KEY")
    if hasattr(st, "secrets")
    else None
)

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")


client = None

if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception:
        client = None


# =========================================================
# ФОНОВЕ ЗОБРАЖЕННЯ
# =========================================================

IMAGE_URL = (
    "https://i.postimg.cc/"
    "kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)


# =========================================================
# КОЛОНКИ EXCEL
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
    "Вуглеводи"
]


# =========================================================
# CSS
# =========================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background:
            linear-gradient(
                rgba(0, 0, 0, 0.72),
                rgba(0, 0, 0, 0.86)
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
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }}

    /* ---------------- КНОПКИ ---------------- */

    button[kind="primary"],
    button[kind="secondary"] {{
        border-radius: 16px !important;
        min-height: 48px !important;
        font-weight: 700 !important;
        transition:
            transform 0.12s ease,
            box-shadow 0.12s ease !important;
    }}

    button[kind="primary"] {{
        box-shadow:
            0 5px 18px
            rgba(54, 162, 235, 0.25) !important;
    }}

    button:active {{
        transform:
            translateY(2px)
            scale(0.985) !important;

        box-shadow:
            inset 0 3px 8px
            rgba(0, 0, 0, 0.40) !important;
    }}

    /* ---------------- INPUT ---------------- */

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{
        border-radius: 14px !important;
    }}

    /* ---------------- ЗВИЧАЙНІ КАРТКИ ---------------- */

    .fitness-card {{
        background: rgba(14, 17, 23, 0.80);
        border:
            1px solid
            rgba(255, 255, 255, 0.15);

        border-radius: 22px;
        padding: 18px;
        margin: 12px 0;

        box-shadow:
            0 12px 35px
            rgba(0, 0, 0, 0.28);

        color: white;
    }}

    /* ---------------- ВЛОГ ---------------- */

    .log-card {{
        background: rgba(14, 17, 23, 0.78);

        border:
            1px solid
            rgba(255, 255, 255, 0.14);

        border-radius: 18px;

        padding: 16px;

        margin: 10px 0;

        color: white;

        box-shadow:
            0 8px 24px
            rgba(0, 0, 0, 0.20);
    }}

    .log-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;

        gap: 12px;
    }}

    .log-time {{
        font-size: 18px;
        font-weight: 800;
        white-space: nowrap;
    }}

    .log-title {{
        margin-top: 8px;

        font-size: 17px;
        font-weight: 700;

        line-height: 1.45;

        word-break: break-word;
    }}

    .log-kcal {{
        font-size: 18px;
        font-weight: 900;
        white-space: nowrap;
    }}

    .food-kcal {{
        color: #36A2EB;
    }}

    .burn-kcal {{
        color: #ff6384;
    }}

    .watch-kcal {{
        color: #58e68b;
    }}

    .log-meta {{
        margin-top: 8px;

        color: #b9c0cc;

        font-size: 13px;

        line-height: 1.5;
    }}

    .badge {{
        display: inline-block;

        padding:
            4px
            10px;

        border-radius: 999px;

        background:
            rgba(255,255,255,0.10);

        color: #dce3ef;

        font-size: 12px;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []

if "settings_open" not in st.session_state:
    st.session_state.settings_open = False

if "clear_food_input" not in st.session_state:
    st.session_state.clear_food_input = False

if "food_input_value" not in st.session_state:
    st.session_state.food_input_value = ""


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

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

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                saved = json.load(file)

            return {
                **default,
                **saved
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


settings = load_settings()


# =========================================================
# РОБОТА З ДАНИМИ
# =========================================================

def load_data():

    empty_df = pd.DataFrame(
        columns=COLUMNS
    )

    if not os.path.exists(EXCEL_FILE):
        return empty_df

    try:

        df = pd.read_excel(
            EXCEL_FILE
        )

    except Exception:

        return empty_df

    for column in COLUMNS:

        if column not in df.columns:

            if column in [
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи"
            ]:

                df[column] = 0.0

            else:

                df[column] = ""

    df = df[COLUMNS].copy()

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

    df["Дата"] = (
        df["Дата"]
        .astype(str)
    )

    df["Час"] = (
        df["Час"]
        .astype(str)
        .str[:5]
    )

    return df


def save_data(df):

    df.to_excel(
        EXCEL_FILE,
        index=False
    )


df = load_data()


# =========================================================
# UNDO — ДО 10 ДІЙ
# =========================================================

def push_undo(df):

    snapshot = df.to_dict(
        orient="records"
    )

    st.session_state.undo_stack.append(
        snapshot
    )

    st.session_state.undo_stack = (
        st.session_state.undo_stack[-10:]
    )


def restore_snapshot(snapshot):

    restored = pd.DataFrame(
        snapshot,
        columns=COLUMNS
    )

    if restored.empty:

        restored = pd.DataFrame(
            columns=COLUMNS
        )

    save_data(restored)

    return restored


# =========================================================
# ДАТА / ЧАС
# =========================================================

def now_local():

    return datetime.now(
        LOCAL_TZ
    )


def today_string():

    return now_local().strftime(
        "%Y-%m-%d"
    )


today = today_string()


# =========================================================
# ДОБОВА ВИТРАТА
# =========================================================

def calculate_bmr_for_day(
    settings,
    date_string
):

    daily_bmr = float(
        settings.get(
            "bmr_daily",
            1850
        )
    )

    if date_string != today:
        return daily_bmr

    current = now_local()

    hours = (
        current.hour
        +
        current.minute / 60
    )

    progress = hours / 24

    progress = max(
        0,
        min(
            progress,
            1
        )
    )

    return daily_bmr * progress


# =========================================================
# КАЛОРІЇ ГОДИННИКА
# =========================================================

def get_watch_burn(
    df,
    date_string
):

    if df.empty:
        return 0.0

    mask = (
        (df["Дата"].astype(str) == str(date_string))
        &
        (df["Тип"] == "Годинник")
    )

    values = pd.to_numeric(
        df.loc[mask, "Спалено"],
        errors="coerce"
    ).fillna(0)

    if len(values) == 0:
        return 0.0

    # ВАЖЛИВО:
    # беремо ОСТАННЄ значення.
    # Воно не додається до старого.

    return float(
        values.iloc[-1]
    )


# =========================================================
# ТРЕНУВАННЯ
# =========================================================

def get_exercise_burn(
    df,
    date_string
):

    if df.empty:
        return 0.0

    mask = (
        (df["Дата"].astype(str) == str(date_string))
        &
        (df["Тип"] == "Тренування")
    )

    values = pd.to_numeric(
        df.loc[mask, "Спалено"],
        errors="coerce"
    ).fillna(0)

    return float(
        values.sum()
    )


# =========================================================
# СТАТИСТИКА ДНЯ
# =========================================================

def day_totals(
    df,
    settings,
    date_string
):

    if df.empty:

        return (
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0
        )

    day = df[
        df["Дата"].astype(str)
        == str(date_string)
    ].copy()

    food = day[
        day["Тип"] == "Їжа"
    ]

    consumed = float(
        pd.to_numeric(
            food["Спожито"],
            errors="coerce"
        ).fillna(0).sum()
    )

    protein = float(
        pd.to_numeric(
            food["Білки"],
            errors="coerce"
        ).fillna(0).sum()
    )

    fat = float(
        pd.to_numeric(
            food["Жири"],
            errors="coerce"
        ).fillna(0).sum()
    )

    carbs = float(
        pd.to_numeric(
            food["Вуглеводи"],
            errors="coerce"
        ).fillna(0).sum()
    )

    watch = get_watch_burn(
        df,
        date_string
    )

    exercise = get_exercise_burn(
        df,
        date_string
    )

    bmr = calculate_bmr_for_day(
        settings,
        date_string
    )

    total_burned = (
        bmr
        +
        watch
        +
        exercise
    )

    balance = (
        total_burned
        -
        consumed
    )

    return (
        consumed,
        protein,
        fat,
        carbs,
        bmr,
        watch,
        exercise,
        total_burned,
        balance
    )


# =========================================================
# ПОТОЧНА ВАГА
# =========================================================

def calculate_current_weight(
    df,
    settings
):

    initial_weight = float(
        settings.get(
            "initial_weight",
            89.0
        )
    )

    if df.empty:
        return initial_weight

    daily_bmr = float(
        settings.get(
            "bmr_daily",
            1850
        )
    )

    total_balance = 0.0

    dates = sorted(
        df["Дата"]
        .astype(str)
        .unique()
    )

    for date_string in dates:

        day = df[
            df["Дата"].astype(str)
            == date_string
        ]

        food = day[
            day["Тип"] == "Їжа"
        ]

        eaten = float(
            pd.to_numeric(
                food["Спожито"],
                errors="coerce"
            ).fillna(0).sum()
        )

        watch = get_watch_burn(
            df,
            date_string
        )

        exercise = get_exercise_burn(
            df,
            date_string
        )

        if date_string == today:

            bmr = calculate_bmr_for_day(
                settings,
                date_string
            )

        else:

            bmr = daily_bmr

        burned = (
            bmr
            +
            watch
            +
            exercise
        )

        total_balance += (
            burned
            -
            eaten
        )

    return (
        initial_weight
        -
        total_balance / 7700.0
    )


# =========================================================
# КРУЖОК
# =========================================================

def render_donut(
    consumed,
    target,
    balance,
    protein,
    fat,
    carbs,
    protein_goal,
    fat_goal,
    carbs_goal
):

    total_macros = (
        protein
        +
        fat
        +
        carbs
    )

    if total_macros > 0:

        protein_deg = (
            protein
            /
            total_macros
            *
            360
        )

        fat_deg = (
            protein_deg
            +
            fat
            /
            total_macros
            *
            360
        )

        carbs_deg = (
            fat_deg
            +
            carbs
            /
            total_macros
            *
            360
        )

        gradient = (
            "conic-gradient("
            f"#36A2EB 0deg {protein_deg:.2f}deg,"
            f"#FFCE56 {protein_deg:.2f}deg {fat_deg:.2f}deg,"
            f"#FF6384 {fat_deg:.2f}deg {carbs_deg:.2f}deg,"
            f"#252a35 {carbs_deg:.2f}deg 360deg"
            ")"
        )

    else:

        gradient = (
            "conic-gradient("
            "#303641 0deg 360deg"
            ")"
        )

    if balance >= 0:

        status_text = (
            f"Дефіцит: {abs(balance):.0f} ккал"
        )

        status_color = "#58e68b"

    else:

        status_text = (
            f"Профіцит: {abs(balance):.0f} ккал"
        )

        status_color = "#ff6262"

    html = f"""
    <div style="
        width:100%;
        background:rgba(14,17,23,.82);
        border:1px solid rgba(255,255,255,.15);
        border-radius:22px;
        padding:22px 12px 18px;
        box-sizing:border-box;
        text-align:center;
        color:white;
    ">

        <div style="
            font-size:20px;
            font-weight:900;
            margin-bottom:16px;
        ">
            🔥 Баланс дня
        </div>

        <div style="
            display:flex;
            justify-content:center;
        ">

            <div style="
                width:230px;
                height:230px;
                border-radius:50%;
                background:{gradient};
                display:flex;
                align-items:center;
                justify-content:center;
                box-shadow:
                    0 0 30px
                    rgba(0,0,0,.45);
            ">

                <div style="
                    width:154px;
                    height:154px;
                    border-radius:50%;
                    background:#11151c;

                    display:flex;
                    flex-direction:column;

                    justify-content:center;
                    align-items:center;

                    text-align:center;

                    color:white;
                ">

                    <div style="
                        color:{status_color};
                        font-size:15px;
                        font-weight:900;
                    ">
                        {status_text}
                    </div>

                    <div style="
                        font-size:30px;
                        font-weight:900;
                        margin-top:6px;
                    ">
                        {consumed:.0f}
                    </div>

                    <div style="
                        font-size:12px;
                        color:#aeb6c4;
                    ">
                        з'їдено з {target:.0f} ккал
                    </div>

                </div>

            </div>

        </div>

        <div style="
            display:flex;
            justify-content:space-around;
            gap:8px;
            margin-top:18px;
            font-size:13px;
            flex-wrap:wrap;
        ">

            <span>
                🥩 {protein:.0f}/{protein_goal:.0f} г
            </span>

            <span>
                🥑 {fat:.0f}/{fat_goal:.0f} г
            </span>

            <span>
                🍞 {carbs:.0f}/{carbs_goal:.0f} г
            </span>

        </div>

    </div>
    """

    st.components.v1.html(
        html,
        height=350,
        scrolling=False
    )


# =========================================================
# ВЛОГ
# =========================================================

def render_log(day_df):

    for _, row in day_df.iterrows():

        typ = str(
            row["Тип"]
        )

        description = str(
            row["Опис"]
        )

        time_value = str(
            row["Час"]
        )[:5]

        if typ == "Їжа":

            icon = "🍽️"

            kcal = float(
                row["Спожито"]
            )

            kcal_text = (
                f"+{kcal:.0f} ккал"
            )

            kcal_class = (
                "food-kcal"
            )

            meta = (
                f"🥩 {float(row['Білки']):.0f} г"
                f" &nbsp;•&nbsp; "
                f"🥑 {float(row['Жири']):.0f} г"
                f" &nbsp;•&nbsp; "
                f"🍞 {float(row['Вуглеводи']):.0f} г"
            )

            badge = "Їжа"

        elif typ == "Годинник":

            icon = "⌚"

            kcal = float(
                row["Спалено"]
            )

            kcal_text = (
                f"-{kcal:.0f} ккал"
            )

            kcal_class = (
                "watch-kcal"
            )

            meta = (
                "Калорії зі смартгодинника"
            )

            badge = "Годинник"

        else:

            icon = "💪"

            kcal = float(
                row["Спалено"]
            )

            kcal_text = (
                f"-{kcal:.0f} ккал"
            )

            kcal_class = (
                "burn-kcal"
            )

            meta = (
                "Активність / тренування"
            )

            badge = "Тренування"

        html = f"""
        <div class="log-card">

            <div class="log-head">

                <div class="log-time">
                    {time_value} {icon}
                </div>

                <div class="log-kcal {kcal_class}">
                    {kcal_text}
                </div>

            </div>

            <div class="log-title">
                {description}
            </div>

            <div class="log-meta">

                <span class="badge">
                    {badge}
                </span>

                <br><br>

                {meta}

            </div>

        </div>
        """

        st.markdown(
            html,
            unsafe_allow_html=True
        )


# =========================================================
# ЗАГОЛОВОК
# =========================================================

st.title(
    f"⚖️ Фітнес — {user_profile}"
)


# =========================================================
# ВИБІР ДНЯ
# =========================================================

available_dates = [today]

if not df.empty:

    all_dates = sorted(
        df["Дата"]
        .astype(str)
        .unique(),
        reverse=True
    )

    for date_value in all_dates:

        if date_value not in available_dates:

            available_dates.append(
                date_value
            )


selected_date = st.selectbox(
    "📅 День",
    available_dates
)


# =========================================================
# СТАТИСТИКА
# =========================================================

(
    consumed,
    protein,
    fat,
    carbs,
    bmr,
    watch,
    exercise,
    total_burned,
    balance
) = day_totals(
    df,
    settings,
    selected_date
)


current_weight = calculate_current_weight(
    df,
    settings
)


# =========================================================
# КРУЖОК
# =========================================================

render_donut(
    consumed,
    settings["calories"],
    balance,
    protein,
    fat,
    carbs,
    settings["protein"],
    settings["fat"],
    settings["carbs"]
)


# =========================================================
# ВАГА + ОСНОВНІ ЦИФРИ
# =========================================================

st.markdown(
    f"""
    <div class="fitness-card">

        <div style="
            font-size:22px;
            font-weight:900;
        ">
            ⚖️ Поточна вага:
            {current_weight:.1f} кг
        </div>

        <div style="
            display:flex;
            justify-content:space-around;
            gap:12px;
            flex-wrap:wrap;
            margin-top:18px;
        ">

            <div style="text-align:center;">
                🍽️<br>
                <b>{consumed:.0f}</b><br>
                <small>з'їдено</small>
            </div>

            <div style="text-align:center;">
                🔥<br>
                <b>{total_burned:.0f}</b><br>
                <small>спалено</small>
            </div>

            <div style="text-align:center;">
                ❤️<br>
                <b>{bmr:.0f}</b><br>
                <small>добова витрата</small>
            </div>

        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ГОДИННИК
# =========================================================

st.subheader(
    "⌚ Калорії з годинника"
)


watch_value = st.number_input(
    "Спалено сьогодні, ккал",
    min_value=0.0,
    value=float(watch),
    step=10.0,
    key="watch_value"
)


if st.button(
    "⌚ Оновити калорії з годинника",
    use_container_width=True
):

    now = now_local()

    push_undo(df)

    mask = (
        (df["Дата"].astype(str) == today)
        &
        (df["Тип"] == "Годинник")
    )

    if mask.any():

        last_index = df.index[
            mask
        ][-1]

        # ВАЖЛИВО:
        # НЕ додаємо.
        # ЗАМІНЮЄМО.

        df.loc[
            last_index,
            "Спалено"
        ] = float(
            watch_value
        )

        df.loc[
            last_index,
            "Опис"
        ] = "Калорії з годинника"

        df.loc[
            last_index,
            "Час"
        ] = now.strftime("%H:%M")

    else:

        new_watch = pd.DataFrame(
            [{
                "Дата":
                    today,

                "Час":
                    now.strftime("%H:%M"),

                "Опис":
                    "Калорії з годинника",

                "Тип":
                    "Годинник",

                "Спожито":
                    0.0,

                "Спалено":
                    float(watch_value),

                "Білки":
                    0.0,

                "Жири":
                    0.0,

                "Вуглеводи":
                    0.0
            }]
        )

        df = pd.concat(
            [
                df,
                new_watch
            ],
            ignore_index=True
        )

    save_data(df)

    st.rerun()


# =========================================================
# ДОДАВАННЯ ЇЖІ
# =========================================================

st.subheader(
    "🍽️ Додати їжу / тренування"
)


if st.session_state.clear_food_input:

    st.session_state.food_input_value = ""

    st.session_state.clear_food_input = False


user_input = st.text_input(
    "Що з'їв або яке тренування?",
    placeholder=(
        "Наприклад: "
        "200 г курки, рис 150 г"
    ),
    key="food_input_value"
)


if st.button(
    "✅ Додати в лог",
    use_container_width=True,
    type="primary"
):

    text = user_input.strip()

    if not text:

        st.warning(
            "Введи продукт або тренування."
        )

    elif not client:

        st.error(
            "Не знайдено "
            "GEMINI_API_KEY у Secrets / Environment."
        )

    else:

        now = now_local()

        prompt = f"""
Ти аналізуєш запис фітнес-щоденника.

Запис:
"{text}"

Визнач, що це:
1. Їжа
2. Тренування

Для їжі визнач:
- назву продуктів;
- загальні калорії;
- білки;
- жири;
- вуглеводи.

Для тренування визнач:
- опис;
- спалені калорії.

Поверни ТІЛЬКИ JSON такого формату:

{{
    "type": "Їжа",
    "description": "короткий опис",
    "consumed_kcal": 0,
    "burned_kcal": 0,
    "protein": 0,
    "fat": 0,
    "carbs": 0
}}

Якщо це тренування:

{{
    "type": "Тренування",
    "description": "короткий опис",
    "consumed_kcal": 0,
    "burned_kcal": 0,
    "protein": 0,
    "fat": 0,
    "carbs": 0
}}

Усі числові значення повинні бути числами.
"""

        try:

            response = client.models.generate_content(

                model=GEMINI_MODEL,

                contents=prompt,

                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            data = json.loads(
                response.text
            )

            push_undo(df)

            detected_type = (
                "Тренування"
                if data.get("type")
                == "Тренування"
                else "Їжа"
            )

            new_entry = {
                "Дата":
                    now.strftime("%Y-%m-%d"),

                "Час":
                    now.strftime("%H:%M"),

                "Опис":
                    data.get(
                        "description"
                    )
                    or text,

                "Тип":
                    detected_type,

                "Спожито":
                    float(
                        data.get(
                            "consumed_kcal",
                            0
                        )
                        or 0
                    ),

                "Спалено":
                    float(
                        data.get(
                            "burned_kcal",
                            0
                        )
                        or 0
                    ),

                "Білки":
                    float(
                        data.get(
                            "protein",
                            0
                        )
                        or 0
                    ),

                "Жири":
                    float(
                        data.get(
                            "fat",
                            0
                        )
                        or 0
                    ),

                "Вуглеводи":
                    float(
                        data.get(
                            "carbs",
                            0
                        )
                        or 0
                    )
            }

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [new_entry]
                    )
                ],
                ignore_index=True
            )

            save_data(df)

            # Очищаємо поле ПІСЛЯ rerun,
            # щоб введений продукт зник.

            st.session_state.clear_food_input = True

            st.rerun()

        except Exception as error:

            st.error(
                f"Помилка Gemini: {error}"
            )


# =========================================================
# КНОПКИ
# =========================================================

st.divider()


col1, col2, col3 = st.columns(3)


with col1:

    if st.button(
        "⚙️ Налаштування",
        use_container_width=True
    ):

        st.session_state.settings_open = (
            not st.session_state.settings_open
        )

        st.rerun()


with col2:

    undo_disabled = (
        len(
            st.session_state.undo_stack
        )
        == 0
    )

    if st.button(
        "↩️ Відмінити",
        use_container_width=True,
        disabled=undo_disabled
    ):

        snapshot = (
            st.session_state.undo_stack.pop()
        )

        df = restore_snapshot(
            snapshot
        )

        st.rerun()


with col3:

    if st.button(
        "🗑️ Видалити останній",
        use_container_width=True
    ):

        if not df.empty:

            push_undo(df)

            df = (
                df
                .iloc[:-1]
                .copy()
            )

            save_data(df)

            st.rerun()

        else:

            st.info(
                "Лог уже порожній."
            )


# =========================================================
# РЕДАКТОР
# =========================================================

if st.session_state.settings_open:

    st.subheader(
        "⚙️ Редактор"
    )

    e_cal = st.number_input(
        "Ціль калорій",
        value=int(
            settings["calories"]
        ),
        step=10
    )

    e_prot = st.number_input(
        "Ціль білків, г",
        value=int(
            settings["protein"]
        ),
        step=5
    )

    e_fat = st.number_input(
        "Ціль жирів, г",
        value=int(
            settings["fat"]
        ),
        step=5
    )

    e_carb = st.number_input(
        "Ціль вуглеводів, г",
        value=int(
            settings["carbs"]
        ),
        step=5
    )

    e_bmr = st.number_input(
        "Добова витрата / BMR, ккал",
        value=int(
            settings["bmr_daily"]
        ),
        step=10
    )

    e_weight = st.number_input(
        "Початкова вага, кг",
        value=float(
            settings["initial_weight"]
        ),
        min_value=0.0,
        step=0.1
    )

    if st.button(
        "💾 Зберегти зміни",
        type="primary",
        use_container_width=True
    ):

        settings["calories"] = int(
            e_cal
        )

        settings["protein"] = int(
            e_prot
        )

        settings["fat"] = int(
            e_fat
        )

        settings["carbs"] = int(
            e_carb
        )

        settings["bmr_daily"] = int(
            e_bmr
        )

        settings["initial_weight"] = float(
            e_weight
        )

        save_settings(
            settings
        )

        st.session_state.settings_open = False

        st.rerun()


# =========================================================
# ВЛОГ
# =========================================================

st.divider()

st.subheader(
    f"📝 Влог — {selected_date}"
)


day_df = df[
    df["Дата"].astype(str)
    == selected_date
].copy()


if day_df.empty:

    st.info(
        "За цей день записів ще немає."
    )

else:

    render_log(
        day_df
    )
