import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# APP
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
# GEMINI
# ============================================================

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


# ============================================================
# ФОН
# ============================================================

IMAGE_URL = (
    "https://i.postimg.cc/"
    "kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
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
# НАЛАШТУВАННЯ ЗА ЗАМОВЧУВАННЯМ
# ============================================================

DEFAULT_SETTINGS = {
    "calories": 2000,
    "protein": 160,
    "fat": 70,
    "carbs": 180,
    "bmr_daily": 1850,
    "initial_weight": 89.0,
    "include_exercise_in_deficit": True
}


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


h1,
h2,
h3 {{
    font-weight: 800 !important;
}}


/* =========================================================
   КНОПКИ
   ========================================================= */

div.stButton > button {{

    min-height: 46px !important;

    border-radius: 14px !important;

    border:
        1px solid
        rgba(255,255,255,.13) !important;

    background:
        linear-gradient(
            135deg,
            rgba(43,43,51,.98),
            rgba(18,18,23,.98)
        ) !important;

    color:
        #ffffff !important;

    font-weight:
        800 !important;

    box-shadow:
        0 7px 20px
        rgba(0,0,0,.28);

    transition:
        all .15s ease;
}}


div.stButton > button:hover {{

    transform:
        translateY(-1px);

    border-color:
        rgba(54,162,235,.65) !important;
}}


div.stButton > button:active {{

    transform:
        translateY(2px)
        scale(.985) !important;

    filter:
        brightness(.78);
}}


div.stButton > button[kind="primary"] {{

    background:
        linear-gradient(
            135deg,
            #36A2EB,
            #1976D2
        ) !important;

    border:
        none !important;
}}


/* =========================================================
   INPUT
   ========================================================= */

input {{

    border-radius:
        12px !important;
}}


/* =========================================================
   КАРТКИ
   ========================================================= */

.card {{

    background:
        rgba(18,19,24,.84);

    border:
        1px solid
        rgba(255,255,255,.10);

    border-radius:
        16px;

    padding:
        14px 16px;

    margin:
        8px 0;
}}


/* =========================================================
   ЛОГ
   ========================================================= */

.log-card {{

    background:
        rgba(12,13,17,.78);

    border:
        1px solid
        rgba(255,255,255,.11);

    border-radius:
        16px;

    padding:
        14px 16px;

    margin:
        10px 0;
}}


.log-title {{

    font-size:
        16px;

    font-weight:
        800;

    line-height:
        1.45;
}}


.log-kcal {{

    font-size:
        18px;

    font-weight:
        900;

    text-align:
        right;

    white-space:
        nowrap;
}}


.log-macros {{

    margin-top:
        8px;

    font-size:
        12px;

    color:
        #bfc3cc;
}}


/* =========================================================
   КРУЖОК
   ========================================================= */

.donut-wrap {{

    display:
        flex;

    justify-content:
        center;

    margin:
        12px 0 2px;
}}


.donut {{

    width:
        230px;

    height:
        230px;

    border-radius:
        50%;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    box-shadow:
        0 0 32px
        rgba(0,0,0,.60);
}}


.hole {{

    width:
        166px;

    height:
        166px;

    border-radius:
        50%;

    background:
        #15171c;

    display:
        flex;

    flex-direction:
        column;

    align-items:
        center;

    justify-content:
        center;

    text-align:
        center;

    box-shadow:
        inset 0 0 24px
        rgba(0,0,0,.9);
}}


.status {{

    font-size:
        13px;

    font-weight:
        900;
}}


.balance {{

    font-size:
        24px;

    font-weight:
        900;

    margin:
        3px 0;
}}


.subline {{

    color:
        #aaa;

    font-size:
        11px;

    margin-top:
        3px;
}}


.weight {{

    color:
        #fff;

    font-size:
        11px;

    font-weight:
        800;

    margin-top:
        5px;
}}


/* =========================================================
   БЖВ
   ========================================================= */

.macro-strip {{

    display:
        flex;

    justify-content:
        space-around;

    gap:
        6px;

    max-width:
        360px;

    margin:
        8px auto 14px;

    padding:
        9px 6px;

    background:
        rgba(20,20,24,.94);

    border:
        1px solid
        rgba(255,255,255,.10);

    border-radius:
        12px;

    font-size:
        11px;

    font-weight:
        900;
}}


.p {{
    color:
        #36A2EB;
}}


.f {{
    color:
        #FFCE56;
}}


.c {{
    color:
        #FF6384;
}}


</style>
""",
    unsafe_allow_html=True
)


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

    text = str(value).strip()

    if text.lower() == "nan":
        return ""

    return text


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

def load_settings():

    if SETTINGS_FILE.exists():

        try:

            with SETTINGS_FILE.open(
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            result = DEFAULT_SETTINGS.copy()

            result.update(data)

            return result

        except Exception:

            pass

    return DEFAULT_SETTINGS.copy()


def save_settings(settings):

    with SETTINGS_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            settings,
            file,
            ensure_ascii=False,
            indent=2
        )


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


    df = df[
        COLUMNS
    ].copy()


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


# ============================================================
# UNDO — ДО 10 ДІЙ
# ============================================================

def load_undo_stack():

    if not TRASH_FILE.exists():

        return []

    try:

        with TRASH_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception:

        return []


def save_undo_stack(stack):

    with TRASH_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            stack[-10:],
            file,
            ensure_ascii=False,
            indent=2,
            default=str
        )


def push_undo(df_before):

    stack = load_undo_stack()

    stack.append(
        df_before.to_dict(
            orient="records"
        )
    )

    save_undo_stack(stack)


def undo_last():

    stack = load_undo_stack()

    if not stack:
        return None

    previous = stack.pop()

    save_undo_stack(stack)

    return pd.DataFrame(
        previous,
        columns=COLUMNS
    )


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


    work = dataframe.copy()


    work["Дата"] = (
        work["Дата"]
        .apply(clean_text)
    )


    work["Спожито"] = (
        pd.to_numeric(
            work["Спожито"],
            errors="coerce"
        )
        .fillna(0)
    )


    work["Спалено"] = (
        pd.to_numeric(
            work["Спалено"],
            errors="coerce"
        )
        .fillna(0)
    )


    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")


    now = datetime.now(
        LOCAL_TZ
    )


    accumulated_deficit = 0.0


    for date_value in (
        work["Дата"].unique()
    ):

        day = work[
            work["Дата"] == date_value
        ]


        eaten = float(
            day["Спожито"].sum()
        )


        exercise = float(
            day["Спалено"].sum()
        )


        if date_value == today:

            hours = (
                now.hour
                +
                now.minute / 60
            )

            base_burn = (
                bmr_daily / 24
            ) * hours

        else:

            base_burn = bmr_daily


        if profile_settings.get(
            "include_exercise_in_deficit",
            True
        ):

            burned = (
                base_burn
                +
                exercise
            )

        else:

            burned = base_burn


        accumulated_deficit += (
            burned
            -
            eaten
        )


    current_weight = (
        initial_weight
        -
        accumulated_deficit / 7700
    )


    return max(
        0.0,
        current_weight
    )


# ============================================================
# GEMINI API
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


if not api_key:

    st.error(
        "⚠️ Не знайдено GEMINI_API_KEY."
    )

    st.info(
        "Додай GEMINI_API_KEY "
        "у Streamlit Secrets."
    )

    st.stop()


client = genai.Client(
    api_key=api_key
)


# ============================================================
# ЗАВАНТАЖЕННЯ
# ============================================================

settings = load_settings()

df = load_data()


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    f"⚖️ Калорійний трекер — {profile}"
)


current_weight = (
    calculate_current_weight(
        df,
        settings
    )
)


st.markdown(
    f"""
    **📅 {
        datetime.now(LOCAL_TZ)
        .strftime("%Y-%m-%d")
    } |
    Поточна вага:
    ~{current_weight:.1f} кг**
    """
)


# ============================================================
# ВВЕДЕННЯ ЇЖІ / ТРЕНУВАННЯ
# ============================================================

st.subheader(
    "🍽️ Додати їжу / 💪 тренування"
)


user_input = st.text_input(
    "Що з'їв або яке було тренування",
    placeholder=(
        "Наприклад: плов з куркою "
        "350 г, чорний хліб 2 скибки"
    ),
    key="user_input"
)


if st.button(
    "✅ Додати в лог",
    type="primary",
    use_container_width=True
):

    if not user_input.strip():

        st.warning(
            "Введи продукт або тренування."
        )

    else:

        prompt = f"""
Ти аналізуєш запис фітнес-трекера.

Користувач написав:
{user_input!r}

Поверни ТІЛЬКИ JSON:

{{
  "description": "короткий опис усіх продуктів або тренування",
  "type": "Їжа",
  "consumed_kcal": 0,
  "burned_kcal": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0
}}

Для Їжа:
consumed_kcal > 0
burned_kcal = 0

Для Тренування:
consumed_kcal = 0
burned_kcal > 0

Білки, жири та вуглеводи
вказуй у грамах.

Усі числа повинні бути
числовими.

Не додавай markdown.

Поверни тільки JSON.
"""


        try:

            response = (
                client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type=(
                            "application/json"
                        )
                    )
                )
            )


            raw = (
                response.text
                or ""
            ).strip()


            if raw.startswith(
                "```"
            ):

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


            result = json.loads(
                raw
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


            consumed = clean_number(
                result.get(
                    "consumed_kcal",
                    0
                )
            )


            burned = clean_number(
                result.get(
                    "burned_kcal",
                    0
                )
            )


            protein = clean_number(
                result.get(
                    "protein",
                    0
                )
            )


            fat = clean_number(
                result.get(
                    "fat",
                    0
                )
            )


            carbs = clean_number(
                result.get(
                    "carbs",
                    0
                )
            )


            if entry_type == "Тренування":

                consumed = 0.0

            else:

                burned = 0.0


            now = datetime.now(
                LOCAL_TZ
            )


            new_row = {

                "Дата":
                    now.strftime(
                        "%Y-%m-%d"
                    ),

                "Час":
                    now.strftime(
                        "%H:%M"
                    ),

                "Опис":
                    (
                        clean_text(
                            result.get(
                                "description"
                            )
                        )
                        or
                        user_input.strip()
                    ),

                "Тип":
                    entry_type,

                "Спожито":
                    consumed,

                "Спалено":
                    burned,

                "Білки":
                    protein,

                "Жири":
                    fat,

                "Вуглеводи":
                    carbs
            }


            # Зберігаємо попередній стан
            # для кнопки "Відмінити".

            push_undo(df)


            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [new_row]
                    )
                ],
                ignore_index=True
            )


            save_data(df)


            # Повністю очищаємо поле.

            st.session_state[
                "user_input"
            ] = ""


            st.success(
                "✅ Додано в лог."
            )


            st.rerun()


        except json.JSONDecodeError:

            st.error(
                "❌ Gemini повернув "
                "неправильний JSON."
            )


        except Exception as error:

            st.error(
                f"❌ Помилка обробки: {error}"
            )


st.divider()


# ============================================================
# ДНІ
# ============================================================

today = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")


dates = [
    today
]


if not df.empty:

    for date_value in sorted(
        df["Дата"]
        .apply(clean_text)
        .unique(),
        reverse=True
    ):

        if (
            date_value
            and
            date_value not in dates
        ):

            dates.append(
                date_value
            )


selected_date = st.selectbox(
    "📅 День",
    dates
)


# ============================================================
# КНОПКИ
# ============================================================

col1, col2, col3 = (
    st.columns(3)
)


with col1:

    settings_button = st.button(
        "✏️ Редактор",
        use_container_width=True
    )


with col2:

    delete_button = st.button(
        "🗑️ Видалити останній",
        use_container_width=True
    )


with col3:

    undo_button = st.button(
        "↩️ Відмінити",
        use_container_width=True
    )


# ============================================================
# РЕДАКТОР
# ============================================================

if settings_button:

    st.session_state[
        "settings_open"
    ] = not st.session_state.get(
        "settings_open",
        False
    )


# ============================================================
# ВИДАЛЕННЯ
# ============================================================

if delete_button:

    if df.empty:

        st.warning(
            "Лог порожній."
        )

    else:

        push_undo(df)


        df = (
            df.iloc[:-1]
            .reset_index(drop=True)
        )


        save_data(df)


        st.success(
            "🗑️ Останній запис видалено."
        )


        st.rerun()


# ============================================================
# ВІДМІНА
# ============================================================

if undo_button:

    restored = undo_last()


    if restored is None:

        st.info(
            "Немає дії для відміни."
        )

    else:

        df = restored

        save_data(df)

        st.success(
            "↩️ Дію відмінено."
        )

        st.rerun()


st.caption(
    "↩️ Історія відміни зберігає "
    "до 10 останніх станів."
)


# ============================================================
# РЕДАКТОР НАЛАШТУВАНЬ
# ============================================================

if st.session_state.get(
    "settings_open",
    False
):

    st.subheader(
        "✏️ Редактор цілей"
    )


    e_cal = st.number_input(
        "🎯 Добова ціль калорій",
        min_value=0,
        value=int(
            settings["calories"]
        ),
        step=50
    )


    e_prot = st.number_input(
        "🥩 Білки, г/добу",
        min_value=0,
        value=int(
            settings["protein"]
        ),
        step=5
    )


    e_fat = st.number_input(
        "🥑 Жири, г/добу",
        min_value=0,
        value=int(
            settings["fat"]
        ),
        step=5
    )


    e_carbs = st.number_input(
        "🍞 Вуглеводи, г/добу",
        min_value=0,
        value=int(
            settings["carbs"]
        ),
        step=5
    )


    e_bmr = st.number_input(
        "🔥 БМР / базова "
        "добова витрата, ккал",
        min_value=0,
        value=int(
            settings["bmr_daily"]
        ),
        step=50
    )


    e_weight = st.number_input(
        "⚖️ Початкова вага, кг",
        min_value=0.0,
        value=float(
            settings["initial_weight"]
        ),
        step=0.1
    )


    e_exercise = st.checkbox(
        "💪 Враховувати тренування "
        "у дефіциті",
        value=bool(
            settings.get(
                "include_exercise_in_deficit",
                True
            )
        )
    )


    if st.button(
        "💾 Зберегти редактор",
        type="primary",
        use_container_width=True
    ):

        save_settings({

            "calories":
                e_cal,

            "protein":
                e_prot,

            "fat":
                e_fat,

            "carbs":
                e_carbs,

            "bmr_daily":
                e_bmr,

            "initial_weight":
                e_weight,

            "include_exercise_in_deficit":
                e_exercise
        })


        st.session_state[
            "settings_open"
        ] = False


        st.rerun()


# ============================================================
# ДАНІ ОБРАНОГО ДНЯ
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

if not day_df.empty:

    consumed = float(
        day_df["Спожито"]
        .apply(clean_number)
        .sum()
    )


    exercise_burned = float(
        day_df["Спалено"]
        .apply(clean_number)
        .sum()
    )


    protein = float(
        day_df["Білки"]
        .apply(clean_number)
        .sum()
    )


    fat = float(
        day_df["Жири"]
        .apply(clean_number)
        .sum()
    )


    carbs = float(
        day_df["Вуглеводи"]
        .apply(clean_number)
        .sum()
    )

else:

    consumed = 0.0

    exercise_burned = 0.0

    protein = 0.0

    fat = 0.0

    carbs = 0.0


# ============================================================
# БМР
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

    hours = (
        now.hour
        +
        now.minute / 60
    )


    bmr_elapsed = (
        bmr_daily / 24
    ) * hours

else:

    bmr_elapsed = bmr_daily


# ============================================================
# ЗАГАЛЬНА ВИТРАТА
# ============================================================

if settings.get(
    "include_exercise_in_deficit",
    True
):

    total_burned = (
        bmr_elapsed
        +
        exercise_burned
    )

else:

    total_burned = (
        bmr_elapsed
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

    status_value = (
        f"−{balance:.0f} ккал"
    )


elif balance < 0:

    status = "ПРОФІЦИТ"

    status_icon = "📈"

    status_color = "#FF6262"

    status_value = (
        f"+{abs(balance):.0f} ккал"
    )


else:

    status = "БАЛАНС"

    status_icon = "⚖️"

    status_color = "#FFD166"

    status_value = (
        "0 ккал"
    )


# ============================================================
# ПОТОЧНА ВАГА
# ============================================================

current_weight = (
    calculate_current_weight(
        df,
        settings
    )
)


# ============================================================
# КРУЖОК БЖВ
# ============================================================

total_macros = (
    protein
    +
    fat
    +
    carbs
)


if total_macros > 0:

    protein_degrees = (
        protein
        /
        total_macros
        *
        360
    )


    fat_degrees = (
        protein_degrees
        +
        fat
        /
        total_macros
        *
        360
    )

else:

    protein_degrees = 0

    fat_degrees = 0


if total_macros <= 0:

    gradient = (
        "conic-gradient("
        "#36A2EB 0deg 120deg,"
        "#FFCE56 120deg 240deg,"
        "#FF6384 240deg 360deg)"
    )

else:

    gradient = (
        "conic-gradient("
        f"#36A2EB 0deg "
        f"{protein_degrees:.2f}deg,"
        f"#FFCE56 "
        f"{protein_degrees:.2f}deg "
        f"{fat_degrees:.2f}deg,"
        f"#FF6384 "
        f"{fat_degrees:.2f}deg "
        f"360deg)"
    )


# ============================================================
# HTML КРУЖКА
# ============================================================

st.markdown(
    f"""
<div class="donut-wrap">

    <div
        class="donut"
        style="
            background:
                {gradient};
        "
    >

        <div class="hole">

            <div
                class="status"
                style="
                    color:
                    {status_color};
                "
            >
                {status_icon}
                {status}
            </div>


            <div
                class="balance"
                style="
                    color:
                    {status_color};
                "
            >
                {status_value}
            </div>


            <div class="subline">
                🍽️ {consumed:.0f}
                /
                {clean_number(settings["calories"]):.0f}
                ккал
            </div>


            <div class="subline">
                🔥 БМР зараз:
                {bmr_elapsed:.0f}
                ккал
            </div>


            <div class="weight">
                ⚖️ {current_weight:.1f} кг
            </div>

        </div>

    </div>

</div>


<div class="macro-strip">

    <span class="p">
        🥩 {protein:.0f}
        /
        {clean_number(settings["protein"]):.0f}
        г
    </span>

    <span class="f">
        🥑 {fat:.0f}
        /
        {clean_number(settings["fat"]):.0f}
        г
    </span>

    <span class="c">
        🍞 {carbs:.0f}
        /
        {clean_number(settings["carbs"]):.0f}
        г
    </span>

</div>
""",
    unsafe_allow_html=True
)


# ============================================================
# КОРОТКА СТАТИСТИКА
# БЕЗ АКТИВНОСТІ З ГОДИННИКА
# ============================================================

st.subheader(
    "📊 Сьогодні"
)


stat1, stat2, stat3 = (
    st.columns(3)
)


with stat1:

    st.metric(
        "🍽️ З'їдено",
        f"{consumed:.0f} ккал"
    )


with stat2:

    st.metric(
        "🔥 БМР за день",
        f"{bmr_daily:.0f} ккал"
    )


with stat3:

    st.metric(
        "🔥 Витрачено зараз",
        f"{total_burned:.0f} ккал"
    )


# ============================================================
# ВЛОГ
# ============================================================

st.subheader(
    f"📝 Влог за {selected_date}"
)


if day_df.empty:

    st.info(
        "За цей день записів немає. "
        "Додай їжу або тренування вище."
    )


else:

    reversed_day = (
        day_df.iloc[::-1]
    )


    for _, row in (
        reversed_day.iterrows()
    ):

        row_type = clean_text(
            row.get(
                "Тип",
                "Їжа"
            )
        )


        if row_type == "Тренування":

            icon = "💪"

            kcal = clean_number(
                row.get(
                    "Спалено",
                    0
                )
            )

            sign = "−"

            color = "#FF6262"

        else:

            icon = "🍽️"

            kcal = clean_number(
                row.get(
                    "Спожито",
                    0
                )
            )

            sign = "+"

            color = "#35D07F"


        time_value = clean_text(
            row.get(
                "Час",
                ""
            )
        )[:5]


        description = clean_text(
            row.get(
                "Опис",
                "Запис"
            )
        )


        protein_row = clean_number(
            row.get(
                "Білки",
                0
            )
        )


        fat_row = clean_number(
            row.get(
                "Жири",
                0
            )
        )


        carbs_row = clean_number(
            row.get(
                "Вуглеводи",
                0
            )
        )


        macro_line = ""


        if row_type == "Їжа":

            macro_line = f"""
<div class="log-macros">

    <span class="p">
        🥩 {protein_row:.0f} г
    </span>

    &nbsp;

    <span class="f">
        🥑 {fat_row:.0f} г
    </span>

    &nbsp;

    <span class="c">
        🍞 {carbs_row:.0f} г
    </span>

</div>
"""


        st.markdown(
            f"""
<div class="log-card">

    <div
        style="
            display:flex;
            justify-content:space-between;
            gap:12px;
        "
    >

        <div class="log-title">

            {time_value}
            {icon}
            {description}

        </div>


        <div
            class="log-kcal"
            style="
                color:{color};
            "
        >

            {sign}
            {kcal:.0f}
            ккал

        </div>

    </div>

    {macro_line}

</div>
""",
            unsafe_allow_html=True
        )


# ============================================================
# ПРОГРЕС КАЛОРІЙ
# ============================================================

target_calories = clean_number(
    settings.get(
        "calories",
        2000
    )
)


if target_calories > 0:

    progress = (
        consumed
        /
        target_calories
    )

    progress = min(
        max(
            progress,
            0.0
        ),
        1.0
    )

else:

    progress = 0.0


st.progress(
    progress
)


st.caption(
    f"🍽️ {consumed:.0f} "
    f"із {target_calories:.0f} ккал"
)


# ============================================================
# КІНЕЦЬ
# ============================================================

st.caption(
    "⚖️ Розрахункова вага "
    "змінюється приблизно на 1 кг "
    "за кожні 7700 ккал "
    "накопиченого дефіциту."
)
