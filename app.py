import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from google import genai
from google.genai import types


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Калорійний трекер",
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
    LOCAL_TZ = timezone(
        timedelta(hours=2)
    )


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
else:
    profile_id = "user2"


# ============================================================
# ФАЙЛИ
# ============================================================

EXCEL_FILE = Path(
    f"fitness_entries_{profile_id}.xlsx"
)

SETTINGS_FILE = Path(
    f"user_settings_{profile_id}.json"
)

TRASH_FILE = Path(
    f"fitness_trash_{profile_id}.json"
)


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
            rgba(0,0,0,0.72),
            rgba(0,0,0,0.88)
        ),
        url("{BACKGROUND_IMAGE}");

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
    max-width: 760px;
    padding-top: 1rem;
    padding-bottom: 4rem;
}}


/* =========================================================
   КНОПКИ
   ========================================================= */

div.stButton > button {{

    min-height: 46px !important;

    border-radius: 15px !important;

    border:
        1px solid
        rgba(255,255,255,0.13) !important;

    background:
        linear-gradient(
            135deg,
            rgba(43,43,53,0.98),
            rgba(20,20,27,0.98)
        ) !important;

    color: #ffffff !important;

    font-weight: 750 !important;

    transition:
        transform 0.12s ease,
        filter 0.12s ease,
        box-shadow 0.12s ease;
}}


div.stButton > button:hover {{

    transform:
        translateY(-1px);

    border-color:
        rgba(54,162,235,0.65) !important;
}}


div.stButton > button:active {{

    transform:
        translateY(2px)
        scale(0.98) !important;

    filter:
        brightness(0.78);

    box-shadow:
        inset 0 3px 7px
        rgba(0,0,0,0.45) !important;
}}


/* =========================================================
   INPUT
   ========================================================= */

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{

    border-radius:
        13px !important;

    background:
        rgba(27,27,36,0.96) !important;

    color:
        #ffffff !important;
}}


/* =========================================================
   КОНТЕЙНЕРИ
   ========================================================= */

div[data-testid="stVerticalBlockBorderWrapper"] {{

    background:
        rgba(14,15,20,0.72);

    border-radius:
        17px;
}}


/* =========================================================
   МЕТРИКИ
   ========================================================= */

.metric-card {{

    background:
        rgba(22,23,30,0.86);

    border:
        1px solid
        rgba(255,255,255,0.09);

    border-radius:
        17px;

    padding:
        13px;

    text-align:
        center;

    margin-bottom:
        8px;
}}


.metric-label {{

    font-size:
        12px;

    color:
        #aaaaaa;
}}


.metric-value {{

    font-size:
        22px;

    font-weight:
        850;

    color:
        #ffffff;

    margin-top:
        4px;
}}


/* =========================================================
   ЛОГ
   ========================================================= */

.log-card {{

    background:
        rgba(16,17,22,0.78);

    border:
        1px solid
        rgba(255,255,255,0.13);

    border-radius:
        18px;

    padding:
        16px;

    margin:
        10px 0;
}}


.log-top {{

    display:
        flex;

    justify-content:
        space-between;

    gap:
        12px;

    align-items:
        flex-start;
}}


.log-time {{

    font-weight:
        850;

    font-size:
        17px;
}}


.log-desc {{

    font-size:
        17px;

    font-weight:
        700;

    line-height:
        1.35;

    margin-top:
        5px;
}}


.log-kcal {{

    font-size:
        18px;

    font-weight:
        850;

    white-space:
        nowrap;
}}


.log-macros {{

    display:
        flex;

    gap:
        8px;

    flex-wrap:
        wrap;

    margin-top:
        11px;
}}


.chip {{

    padding:
        5px 9px;

    border-radius:
        999px;

    background:
        rgba(255,255,255,0.07);

    font-size:
        12px;
}}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# НАЛАШТУВАННЯ ЗА ЗАМОВЧУВАННЯМ
# ============================================================

DEFAULT_SETTINGS = {

    "calories":
        2000,

    "protein":
        160,

    "fat":
        70,

    "carbs":
        180,

    "bmr_daily":
        1850,

    "initial_weight":
        89.0,

    "include_exercise_in_deficit":
        True
}


# ============================================================
# КОЛОНКИ
# ============================================================

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


# ============================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# ============================================================

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


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

def load_settings():

    if not SETTINGS_FILE.exists():

        return DEFAULT_SETTINGS.copy()

    try:

        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        result = DEFAULT_SETTINGS.copy()

        result.update(data)

        return result

    except Exception:

        return DEFAULT_SETTINGS.copy()


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


# ============================================================
# DATAFRAME
# ============================================================

def empty_dataframe():

    return pd.DataFrame(
        columns=COLUMNS
    )


def load_data():

    if not EXCEL_FILE.exists():

        return empty_dataframe()

    try:

        df = pd.read_excel(
            EXCEL_FILE
        )

    except Exception:

        return empty_dataframe()

    for column in COLUMNS:

        if column not in df.columns:

            if column in [
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи"
            ]:

                df[column] = 0

            elif column == "Тип":

                df[column] = "Їжа"

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
        ).fillna(0)

    for column in [
        "Дата",
        "Час",
        "Опис",
        "Тип"
    ]:

        df[column] = (
            df[column]
            .apply(clean_text)
        )

    return df


def save_data(df):

    df.to_excel(
        EXCEL_FILE,
        index=False
    )


df = load_data()


# ============================================================
# UNDO
# ============================================================

if "undo_stack" not in st.session_state:

    st.session_state[
        "undo_stack"
    ] = []


def push_undo(df):

    stack = st.session_state[
        "undo_stack"
    ]

    stack.append(
        df.to_dict(
            orient="records"
        )
    )

    if len(stack) > 10:

        del stack[0]


def restore_snapshot(records):

    if not records:

        return empty_dataframe()

    result = pd.DataFrame(
        records
    )

    for column in COLUMNS:

        if column not in result.columns:

            if column in [
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи"
            ]:

                result[column] = 0

            else:

                result[column] = ""

    result = result[
        COLUMNS
    ].copy()

    return result


# ============================================================
# ПОТОЧНА ВАГА
# ============================================================

def calculate_current_weight(
    dataframe,
    profile_settings
):

    initial_weight = clean_number(
        profile_settings.get(
            "initial_weight",
            89.0
        )
    )

    bmr_daily = clean_number(
        profile_settings.get(
            "bmr_daily",
            1850
        )
    )

    if dataframe.empty:

        return initial_weight

    now = datetime.now(
        LOCAL_TZ
    )

    today = now.strftime(
        "%Y-%m-%d"
    )

    total_balance = 0.0

    for date_value in (
        dataframe["Дата"]
        .apply(clean_text)
        .unique()
    ):

        day = dataframe[
            dataframe["Дата"]
            .apply(clean_text)
            ==
            date_value
        ]

        eaten = (
            day["Спожито"]
            .apply(clean_number)
            .sum()
        )

        exercise = (
            day[
                day["Тип"]
                .apply(clean_text)
                ==
                "Тренування"
            ]["Спалено"]
            .apply(clean_number)
            .sum()
        )

        watch = (
            day[
                day["Тип"]
                .apply(clean_text)
                ==
                "Годинник"
            ]["Спалено"]
            .apply(clean_number)
            .sum()
        )

        if date_value == today:

            hours = (
                now.hour
                +
                now.minute / 60
            )

            bmr = (
                bmr_daily / 24
            ) * hours

        else:

            bmr = bmr_daily

        burned = (
            bmr
            +
            exercise
            +
            watch
        )

        total_balance += (
            burned
            -
            eaten
        )

    weight_change = (
        total_balance / 7700
    )

    result = (
        initial_weight
        -
        weight_change
    )

    return max(
        0.0,
        result
    )


# ============================================================
# GEMINI
# ============================================================

api_key = None

try:

    api_key = st.secrets.get(
        "GEMINI_API_KEY"
    )

except Exception:

    pass


if not api_key:

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )


client = None

if api_key:

    client = genai.Client(
        api_key=api_key
    )


def analyze_record(text):

    prompt = """

Ти аналізуєш запис для фітнес-трекера.

Визнач:

1. чи це їжа;
2. чи це тренування;
3. приблизні калорії;
4. білки;
5. жири;
6. вуглеводи;
7. якщо це тренування — спалені калорії.

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

Для їжі:

type = "Їжа"
consumed_kcal > 0
burned_kcal = 0

Для тренування:

type = "Тренування"
consumed_kcal = 0
burned_kcal > 0

Усі числа повинні бути числовими.

Не додавай markdown.

Поверни тільки JSON.
"""

    response = client.models.generate_content(

        model="gemini-3.6-flash",

        contents=[
            prompt,
            "\nЗапис користувача:\n",
            text
        ],

        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    raw = (
        response.text
        or ""
    ).strip()

    raw = (
        raw
        .replace(
            "```json",
            ""
        )
        .replace(
            "```",
            ""
        )
        .strip()
    )

    return json.loads(
        raw
    )


# ============================================================
# ЗАГОЛОВОК
# ============================================================

current_weight = (
    calculate_current_weight(
        df,
        settings
    )
)

st.title(
    "⚖️ Калорійний трекер"
)

st.caption(
    f"📅 "
    f"{datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')}"
    f" | Поточна вага: "
    f"~{current_weight:.1f} кг"
)


# ============================================================
# КНОПКИ
# ============================================================

col1, col2 = st.columns(2)


with col1:

    undo_available = bool(
        st.session_state[
            "undo_stack"
        ]
    )

    if st.button(
        "↩️ Відмінити",
        use_container_width=True,
        disabled=not undo_available
    ):

        records = (
            st.session_state[
                "undo_stack"
            ].pop()
        )

        df = restore_snapshot(
            records
        )

        save_data(
            df
        )

        st.rerun()


with col2:

    if st.button(
        "🗑️ Видалити останній запис",
        use_container_width=True,
        disabled=df.empty
    ):

        push_undo(
            df
        )

        df = (
            df.iloc[:-1]
            .reset_index(drop=True)
        )

        save_data(
            df
        )

        st.rerun()


# ============================================================
# ДАТА
# ============================================================

today = datetime.now(
    LOCAL_TZ
).strftime(
    "%Y-%m-%d"
)

dates = [
    today
]

if not df.empty:

    for date_value in (
        df["Дата"]
        .apply(clean_text)
        .unique()
    ):

        if (
            date_value
            and
            date_value not in dates
        ):

            dates.append(
                date_value
            )

dates = sorted(
    dates,
    reverse=True
)


selected_date = st.selectbox(
    "📅 День",
    dates
)


# ============================================================
# ДАНІ ДНЯ
# ============================================================

if df.empty:

    day_df = empty_dataframe()

else:

    day_df = df[
        df["Дата"]
        .apply(clean_text)
        ==
        selected_date
    ].copy()


# ============================================================
# СТАТИСТИКА
# ============================================================

consumed = 0.0
exercise_burned = 0.0
watch_burned = 0.0

protein = 0.0
fat = 0.0
carbs = 0.0


if not day_df.empty:

    consumed = (
        day_df["Спожито"]
        .apply(clean_number)
        .sum()
    )

    exercise_burned = (
        day_df[
            day_df["Тип"]
            .apply(clean_text)
            ==
            "Тренування"
        ]["Спалено"]
        .apply(clean_number)
        .sum()
    )

    watch_burned = (
        day_df[
            day_df["Тип"]
            .apply(clean_text)
            ==
            "Годинник"
        ]["Спалено"]
        .apply(clean_number)
        .sum()
    )

    protein = (
        day_df["Білки"]
        .apply(clean_number)
        .sum()
    )

    fat = (
        day_df["Жири"]
        .apply(clean_number)
        .sum()
    )

    carbs = (
        day_df["Вуглеводи"]
        .apply(clean_number)
        .sum()
    )


# ============================================================
# ДОБОВА ВИТРАТА
# ============================================================

bmr_daily = clean_number(
    settings.get(
        "bmr_daily",
        1850
    )
)

now = datetime.now(
    LOCAL_TZ
)


if selected_date == today:

    hours_passed = (
        now.hour
        +
        now.minute / 60
    )

    bmr_elapsed = (
        bmr_daily / 24
    ) * hours_passed

else:

    bmr_elapsed = bmr_daily


total_burned = (
    bmr_elapsed
    +
    exercise_burned
    +
    watch_burned
)


# ============================================================
# ДЕФІЦИТ / ПРОФІЦИТ
# ============================================================

balance = (
    total_burned
    -
    consumed
)


if balance > 0:

    status = "ДЕФІЦИТ"
    status_icon = "📉"
    status_color = "#35D07F"

elif balance < 0:

    status = "ПРОФІЦИТ"
    status_icon = "📈"
    status_color = "#FF6262"

else:

    status = "БАЛАНС"
    status_icon = "⚖️"
    status_color = "#FFD166"


# ============================================================
# КРУЖОК БМЖ
# ============================================================

macro_total = (
    protein
    +
    fat
    +
    carbs
)


if macro_total > 0:

    protein_degrees = (
        protein
        /
        macro_total
        *
        360
    )

    fat_degrees = (
        protein_degrees
        +
        fat
        /
        macro_total
        *
        360
    )

else:

    protein_degrees = 120
    fat_degrees = 240


donut_html = f"""

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

</head>

<body style="
margin:0;
padding:0;
background:transparent;
">

<div style="
height:330px;
display:flex;
align-items:center;
justify-content:center;
font-family:
-apple-system,
BlinkMacSystemFont,
'Segoe UI',
Arial,
sans-serif;
">

<div style="
width:240px;
height:240px;
border-radius:50%;

background:
conic-gradient(

#36A2EB
0deg
{protein_degrees:.2f}deg,

#FFCE56
{protein_degrees:.2f}deg
{fat_degrees:.2f}deg,

#FF6384
{fat_degrees:.2f}deg
360deg
);

display:flex;
align-items:center;
justify-content:center;

box-shadow:
0 0 32px
rgba(0,0,0,0.55);
">


<div style="
width:174px;
height:174px;

border-radius:50%;

background:#15171c;

display:flex;
flex-direction:column;

align-items:center;
justify-content:center;

text-align:center;

box-shadow:
inset 0 0 22px
rgba(0,0,0,0.9);
">


<div style="
color:{status_color};
font-size:13px;
font-weight:900;
">

{status_icon} {status}

</div>


<div style="
color:{status_color};
font-size:26px;
font-weight:900;
margin-top:4px;
">

{abs(balance):.0f} ккал

</div>


<div style="
color:#c9c9c9;
font-size:11px;
margin-top:8px;
">

🍽️ {consumed:.0f}
/
{clean_number(settings["calories"]):.0f}
ккал

</div>


<div style="
color:#c9c9c9;
font-size:11px;
margin-top:3px;
">

🔥 {total_burned:.0f} ккал витрачено

</div>


<div style="
color:#ffffff;
font-size:11px;
font-weight:800;
margin-top:4px;
">

⚖️ {current_weight:.1f} кг

</div>


</div>

</div>

</div>

</body>

</html>

"""


components.html(
    donut_html,
    height=335,
    scrolling=False
)


# ============================================================
# КОРОТКА СТАТИСТИКА
# ============================================================

s1, s2, s3 = st.columns(3)


with s1:

    st.markdown(
        f"""
        <div class="metric-card">

        <div class="metric-label">
        🍽️ З'їдено
        </div>

        <div class="metric-value">
        {consumed:.0f} ккал
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )


with s2:

    st.markdown(
        f"""
        <div class="metric-card">

        <div class="metric-label">
        🔥 Витрачено
        </div>

        <div class="metric-value">
        {total_burned:.0f} ккал
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )


with s3:

    st.markdown(
        f"""
        <div class="metric-card">

        <div class="metric-label">
        ⚖️ Вага
        </div>

        <div class="metric-value">
        {current_weight:.1f} кг
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# КАЛОРІЇ З ГОДИННИКА
# ============================================================

st.subheader(
    "⌚ Калорії з годинника"
)


watch_input = st.number_input(
    "Спалено сьогодні, ккал",
    min_value=0.0,
    value=float(watch_burned),
    step=10.0,
    key=f"watch_{selected_date}"
)


if st.button(
    "⌚ Оновити",
    use_container_width=True
):

    push_undo(
        df
    )

    mask = (

        df["Дата"]
        .apply(clean_text)
        ==
        selected_date

    ) & (

        df["Тип"]
        .apply(clean_text)
        ==
        "Годинник"

    )

    df = df[
        ~mask
    ].copy()


    if watch_input > 0:

        now = datetime.now(
            LOCAL_TZ
        )

        new_watch = {

            "Дата":
                selected_date,

            "Час":
                now.strftime("%H:%M"),

            "Опис":
                "Калорії з годинника",

            "Тип":
                "Годинник",

            "Спожито":
                0,

            "Спалено":
                float(watch_input),

            "Білки":
                0,

            "Жири":
                0,

            "Вуглеводи":
                0
        }

        df = pd.concat(
            [
                df,
                pd.DataFrame(
                    [new_watch]
                )
            ],
            ignore_index=True
        )


    save_data(
        df
    )

    st.rerun()


# ============================================================
# ДОДАТИ ЇЖУ
# ============================================================

st.subheader(
    "🍽️ Додати їжу"
)


entry_text = st.text_input(
    "Продукт / страва",
    placeholder=(
        "Наприклад: "
        "плов з куркою, "
        "чорний хліб, 5 яєць"
    )
)


manual_kcal = st.number_input(
    "Калорії, ккал",
    min_value=0.0,
    value=0.0,
    step=10.0
)


if st.button(
    "✅ ОК",
    type="primary",
    use_container_width=True
):

    if not entry_text.strip():

        st.warning(
            "Введи продукт."
        )

    elif client is None:

        st.error(
            "Не знайдено "
            "GEMINI_API_KEY."
        )

    else:

        try:

            result = analyze_record(
                entry_text.strip()
            )


            entry_type = clean_text(
                result.get(
                    "type",
                    "Їжа"
                )
            )


            if entry_type not in [
                "Їжа",
                "Тренування"
            ]:

                entry_type = "Їжа"


            consumed_kcal = clean_number(
                result.get(
                    "consumed_kcal",
                    0
                )
            )


            burned_kcal = clean_number(
                result.get(
                    "burned_kcal",
                    0
                )
            )


            if manual_kcal > 0:

                if entry_type == "Їжа":

                    consumed_kcal = (
                        float(manual_kcal)
                    )

                else:

                    burned_kcal = (
                        float(manual_kcal)
                    )


            if entry_type == "Їжа":

                burned_kcal = 0.0

            else:

                consumed_kcal = 0.0


            push_undo(
                df
            )


            now = datetime.now(
                LOCAL_TZ
            )


            description = clean_text(
                result.get(
                    "description",
                    ""
                )
            )


            if not description:

                description = (
                    entry_text.strip()
                )


            new_row = {

                "Дата":
                    selected_date,

                "Час":
                    now.strftime("%H:%M"),

                "Опис":
                    description,

                "Тип":
                    entry_type,

                "Спожито":
                    consumed_kcal,

                "Спалено":
                    burned_kcal,

                "Білки":
                    clean_number(
                        result.get(
                            "protein",
                            0
                        )
                    ),

                "Жири":
                    clean_number(
                        result.get(
                            "fat",
                            0
                        )
                    ),

                "Вуглеводи":
                    clean_number(
                        result.get(
                            "carbs",
                            0
                        )
                    )
            }


            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [new_row]
                    )
                ],
                ignore_index=True
            )


            save_data(
                df
            )


            st.success(
                "✅ Запис додано."
            )


            st.rerun()


        except json.JSONDecodeError:

            st.error(
                "❌ Gemini повернув "
                "неправильний JSON."
            )


        except Exception as error:

            st.error(
                f"❌ Помилка Gemini: "
                f"{error}"
            )


# ============================================================
# ТРЕНУВАННЯ ВРУЧНУ
# ============================================================

with st.expander(
    "💪 Додати тренування"
):

    training_name = st.text_input(
        "Назва тренування",
        placeholder=(
            "Наприклад: "
            "ходьба 60 хв"
        )
    )


    training_kcal = st.number_input(
        "Спалено, ккал",
        min_value=0.0,
        value=0.0,
        step=10.0
    )


    if st.button(
        "💪 Додати тренування",
        use_container_width=True
    ):

        if (
            training_name.strip()
            and
            training_kcal > 0
        ):

            push_undo(
                df
            )


            now = datetime.now(
                LOCAL_TZ
            )


            new_training = {

                "Дата":
                    selected_date,

                "Час":
                    now.strftime("%H:%M"),

                "Опис":
                    training_name.strip(),

                "Тип":
                    "Тренування",

                "Спожито":
                    0,

                "Спалено":
                    float(training_kcal),

                "Білки":
                    0,

                "Жири":
                    0,

                "Вуглеводи":
                    0
            }


            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [new_training]
                    )
                ],
                ignore_index=True
            )


            save_data(
                df
            )

            st.rerun()


# ============================================================
# РЕДАКТОР
# ============================================================

with st.expander(
    "✏️ Редактор"
):

    st.caption(
        "Змінюй будь-яке поле. "
        "Після збереження всі "
        "показники перерахуються."
    )


    if day_df.empty:

        st.info(
            "За цей день "
            "немає записів."
        )

    else:

        edited_df = st.data_editor(

            day_df,

            num_rows="dynamic",

            use_container_width=True,

            hide_index=True,

            key=f"editor_{selected_date}"
        )


        if st.button(
            "💾 Зберегти зміни",
            use_container_width=True
        ):

            push_undo(
                df
            )


            df = df[
                df["Дата"]
                .apply(clean_text)
                !=
                selected_date
            ].copy()


            edited_df = edited_df[
                COLUMNS
            ].copy()


            for column in [
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи"
            ]:

                edited_df[column] = (
                    pd.to_numeric(
                        edited_df[column],
                        errors="coerce"
                    )
                    .fillna(0)
                )


            df = pd.concat(
                [
                    df,
                    edited_df
                ],
                ignore_index=True
            )


            save_data(
                df
            )

            st.rerun()


# ============================================================
# ВЛОГ
# ============================================================

st.subheader(
    f"📋 Влог за {selected_date}"
)


if day_df.empty:

    st.info(
        "Записів ще немає."
    )

else:

    reversed_day = (
        day_df.iloc[::-1]
    )


    for _, row in (
        reversed_day.iterrows()
    ):

        row_type = clean_text(
            row["Тип"]
        )


        if row_type == "Тренування":

            icon = "💪"

            kcal = clean_number(
                row["Спалено"]
            )

            sign = "−"


        elif row_type == "Годинник":

            icon = "⌚"

            kcal = clean_number(
                row["Спалено"]
            )

            sign = "−"


        else:

            icon = "🍽️"

            kcal = clean_number(
                row["Спожито"]
            )

            sign = "+"


        description = clean_text(
            row["Опис"]
        )


        time_value = clean_text(
            row["Час"]
        )[:5]


        protein_value = clean_number(
            row["Білки"]
        )


        fat_value = clean_number(
            row["Жири"]
        )


        carbs_value = clean_number(
            row["Вуглеводи"]
        )


        macro_html = ""


        if row_type == "Їжа":

            macro_html = f"""

            <div class="log-macros">

                <span class="chip">
                    🥩 {protein_value:.0f} г
                </span>

                <span class="chip">
                    🥑 {fat_value:.0f} г
                </span>

                <span class="chip">
                    🍞 {carbs_value:.0f} г
                </span>

            </div>

            """


        st.markdown(

            f"""

            <div class="log-card">

                <div class="log-top">

                    <div>

                        <div class="log-time">

                            {time_value}
                            {icon}

                        </div>


                        <div class="log-desc">

                            {description}

                        </div>

                    </div>


                    <div class="log-kcal">

                        {sign}{kcal:.0f} ккал

                    </div>

                </div>


                {macro_html}

            </div>

            """,

            unsafe_allow_html=True

        )


# ============================================================
# ПІДСУМОК
# ============================================================

st.divider()


if balance > 0:

    st.success(
        f"📉 Дефіцит: "
        f"{balance:.0f} ккал"
    )


elif balance < 0:

    st.error(
        f"📈 Профіцит: "
        f"{abs(balance):.0f} ккал"
    )


else:

    st.info(
        "⚖️ Баланс: 0 ккал"
    )


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

with st.expander(
    "⚙️ Налаштування"
):

    calories_value = st.number_input(
        "🎯 Добова норма калорій",
        min_value=0,
        value=int(
            settings["calories"]
        ),
        step=50
    )


    bmr_value = st.number_input(
        "🔥 Добова базова витрата",
        min_value=0,
        value=int(
            settings["bmr_daily"]
        ),
        step=50
    )


    initial_weight_value = st.number_input(
        "⚖️ Початкова вага, кг",
        min_value=0.0,
        value=float(
            settings["initial_weight"]
        ),
        step=0.1
    )


    exercise_enabled = st.checkbox(
        "💪 Враховувати тренування "
        "в дефіциті",
        value=settings.get(
            "include_exercise_in_deficit",
            True
        )
    )


    if st.button(
        "💾 Зберегти налаштування",
        use_container_width=True
    ):

        settings.update({

            "calories":
                calories_value,

            "bmr_daily":
                bmr_value,

            "initial_weight":
                initial_weight_value,

            "include_exercise_in_deficit":
                exercise_enabled
        })


        save_settings(
            settings
        )


        st.rerun()
