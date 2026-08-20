import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from google import genai
from google.genai import types


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="⚖️",
    layout="centered"
)


# ============================================================
# ЧАС
# ============================================================

try:
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo("Europe/Kyiv")

except Exception:

    LOCAL_TZ = timezone(
        timedelta(hours=2)
    )


def now_local():

    return datetime.now(
        LOCAL_TZ
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

profile_id = (
    "user1"
    if profile == "Я"
    else "user2"
)


# ============================================================
# ФАЙЛИ
# ============================================================

EXCEL_FILE = (
    f"fitness_entries_{profile_id}.xlsx"
)

SETTINGS_FILE = (
    f"user_settings_{profile_id}.json"
)

UNDO_FILE = (
    f"fitness_undo_{profile_id}.json"
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

#MainMenu {{
    visibility: hidden;
}}

header {{
    visibility: hidden;
}}

footer {{
    visibility: hidden;
}}

.block-container {{
    padding-top: 1rem;
    padding-bottom: 3rem;
    max-width: 850px;
}}

div.stButton > button {{
    min-height: 46px !important;

    border-radius: 14px !important;

    border:
        1px solid
        rgba(255,255,255,0.12) !important;

    background:
        linear-gradient(
            135deg,
            rgba(42,43,51,0.98),
            rgba(19,20,25,0.98)
        ) !important;

    color: #ffffff !important;

    font-weight: 700 !important;

    transition:
        transform 0.15s ease,
        border-color 0.15s ease;
}}

div.stButton > button:hover {{
    transform: translateY(-1px);

    border-color:
        rgba(54,162,235,0.7) !important;
}}

div[data-testid="stMetric"] {{
    background:
        rgba(18,19,24,0.90);

    border:
        1px solid
        rgba(255,255,255,0.08);

    border-radius:
        14px;

    padding:
        10px;
}}

div[data-testid="stExpander"] {{
    border-radius:
        16px !important;

    border:
        1px solid
        rgba(255,255,255,0.10) !important;

    background:
        rgba(18,19,24,0.62) !important;
}}

input,
textarea {{
    border-radius:
        14px !important;
}}

</style>
""",
    unsafe_allow_html=True
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

    api_key = None


if not api_key:

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


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

DEFAULT_SETTINGS = {

    # Добова ціль по їжі
    "calories": 2000,

    # Добові БЖВ
    "protein": 160,
    "fat": 70,
    "carbs": 180,

    # Базова добова витрата
    "bmr_daily": 1850,

    # Стартова вага
    "initial_weight": 89.0
}


def load_settings():

    if not os.path.exists(
        SETTINGS_FILE
    ):

        return DEFAULT_SETTINGS.copy()


    try:

        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)


        result = (
            DEFAULT_SETTINGS.copy()
        )

        result.update(data)

        return result


    except Exception:

        return DEFAULT_SETTINGS.copy()


def save_settings(data):

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


settings = load_settings()


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


def empty_dataframe():

    return pd.DataFrame(
        columns=COLUMNS
    )


# ============================================================
# БЕЗПЕЧНІ ПЕРЕТВОРЕННЯ
# ============================================================

def clean_number(value):

    try:

        result = float(value)

        if pd.isna(result):

            return 0.0

        return result

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


    result = str(value)


    if result.lower() == "nan":

        return ""


    return result


# ============================================================
# ЗАВАНТАЖЕННЯ EXCEL
# ============================================================

def load_data():

    if not os.path.exists(
        EXCEL_FILE
    ):

        return empty_dataframe()


    try:

        data = pd.read_excel(
            EXCEL_FILE
        )

    except Exception:

        return empty_dataframe()


    for column in COLUMNS:

        if column in data.columns:

            continue


        if column in [
            "Спожито",
            "Спалено",
            "Білки",
            "Жири",
            "Вуглеводи"
        ]:

            data[column] = 0

        elif column == "Тип":

            data[column] = "Їжа"

        else:

            data[column] = ""


    data = data[
        COLUMNS
    ].copy()


    numeric_columns = [

        "Спожито",
        "Спалено",
        "Білки",
        "Жири",
        "Вуглеводи"
    ]


    for column in numeric_columns:

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        ).fillna(0)


    for column in [
        "Дата",
        "Час",
        "Опис",
        "Тип"
    ]:

        data[column] = (
            data[column]
            .apply(clean_text)
        )


    return data


df = load_data()


# ============================================================
# UNDO
# ============================================================

def load_undo():

    if not os.path.exists(
        UNDO_FILE
    ):

        return []


    try:

        with open(
            UNDO_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            result = json.load(file)


        return result[-10:]


    except Exception:

        return []


def save_undo(history):

    history = history[-10:]


    with open(
        UNDO_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            ensure_ascii=False
        )


def make_snapshot(data):

    result = (
        data
        .copy()
        .to_dict(
            orient="records"
        )
    )

    return result


def add_undo_snapshot(data):

    history = load_undo()

    history.append(
        make_snapshot(data)
    )

    save_undo(history)


def restore_snapshot(snapshot):

    if not snapshot:

        return empty_dataframe()


    result = pd.DataFrame(
        snapshot
    )


    for column in COLUMNS:

        if column not in result.columns:

            result[column] = ""


    result = result[
        COLUMNS
    ].copy()


    for column in [
        "Спожито",
        "Спалено",
        "Білки",
        "Жири",
        "Вуглеводи"
    ]:

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce"
        ).fillna(0)


    return result


def undo_last():

    history = load_undo()


    if not history:

        return None


    snapshot = history.pop()

    save_undo(history)

    return restore_snapshot(
        snapshot
    )


# ============================================================
# ЗБЕРЕГТИ EXCEL
# ============================================================

def save_data(data):

    data.to_excel(
        EXCEL_FILE,
        index=False
    )


# ============================================================
# ВИДАЛИТИ СТАРІ ЗАПИСИ ГОДИННИКА
# ============================================================

def get_watch_row_index(
    data,
    date_value
):

    rows = data[
        (
            data["Дата"]
            .apply(clean_text)
            ==
            date_value
        )
        &
        (
            data["Тип"]
            .apply(clean_text)
            ==
            "Годинник"
        )
    ]


    if rows.empty:

        return None


    return rows.index[-1]


# ============================================================
# ОНОВИТИ ГОДИННИК
#
# КЛЮЧОВА ЛОГІКА:
# нове значення НЕ додається.
# воно ЗАМІНЮЄ старе значення.
# ============================================================

def update_watch_value(
    data,
    date_value,
    time_value,
    calories
):

    data = data.copy()


    existing_index = (
        get_watch_row_index(
            data,
            date_value
        )
    )


    if existing_index is None:

        new_row = {

            "Дата": date_value,

            "Час": time_value,

            "Опис":
                "Активність за даними годинника",

            "Тип":
                "Годинник",

            "Спожито":
                0,

            "Спалено":
                calories,

            "Білки":
                0,

            "Жири":
                0,

            "Вуглеводи":
                0
        }


        data = pd.concat(
            [
                data,
                pd.DataFrame(
                    [new_row]
                )
            ],
            ignore_index=True
        )


    else:

        data.at[
            existing_index,
            "Час"
        ] = time_value


        data.at[
            existing_index,
            "Спалено"
        ] = calories


        data.at[
            existing_index,
            "Опис"
        ] = (
            "Активність "
            "за даними годинника"
        )


    return data


# ============================================================
# РОЗРАХУНОК ПОТОЧНОЇ ВАГИ
# ============================================================

def calculate_current_weight(
    data,
    profile_settings
):

    initial_weight = clean_number(
        profile_settings.get(
            "initial_weight",
            89.0
        )
    )


    daily_bmr = clean_number(
        profile_settings.get(
            "bmr_daily",
            1850
        )
    )


    if data.empty:

        return initial_weight


    today = now_local().strftime(
        "%Y-%m-%d"
    )


    current_time = now_local()


    accumulated_balance = 0.0


    unique_dates = (
        data["Дата"]
        .apply(clean_text)
        .unique()
    )


    for date_value in unique_dates:

        if not date_value:

            continue


        day = data[
            data["Дата"]
            .apply(clean_text)
            ==
            date_value
        ]


        eaten = (
            day["Спожито"]
            .apply(clean_number)
            .sum()
        )


        # --------------------------------------------
        # ГОДИННИК
        # --------------------------------------------

        watch = day[
            day["Тип"]
            .apply(clean_text)
            ==
            "Годинник"
        ]


        watch_calories = 0.0


        if not watch.empty:

            # Важливо:
            # беремо останнє значення,
            # а не суму.
            watch_calories = clean_number(
                watch.iloc[-1]["Спалено"]
            )


        # --------------------------------------------
        # ТРЕНУВАННЯ
        # --------------------------------------------

        workouts = day[
            day["Тип"]
            .apply(clean_text)
            ==
            "Тренування"
        ]


        workout_calories = (
            workouts["Спалено"]
            .apply(clean_number)
            .sum()
        )


        # --------------------------------------------
        # БАЗОВА ВИТРАТА
        # --------------------------------------------

        if date_value == today:

            hours_passed = (
                current_time.hour
                +
                current_time.minute / 60
            )

            base_burn = (
                daily_bmr / 24
            ) * hours_passed

        else:

            base_burn = daily_bmr


        # --------------------------------------------
        # ЗАГАЛЬНА ВИТРАТА
        # --------------------------------------------

        burned = (
            base_burn
            +
            watch_calories
            +
            workout_calories
        )


        accumulated_balance += (
            burned - eaten
        )


    # приблизно 7700 ккал = 1 кг
    weight_change = (
        accumulated_balance / 7700
    )


    return max(
        0.0,
        initial_weight - weight_change
    )


# ============================================================
# РОЗРАХУНОК ДАНИХ ЗА ДЕНЬ
# ============================================================

def calculate_day(
    data,
    selected_date,
    profile_settings
):

    day = data[
        data["Дата"]
        .apply(clean_text)
        ==
        selected_date
    ].copy()


    # --------------------------------------------
    # З'ЇДЕНО
    # --------------------------------------------

    consumed = (
        day["Спожито"]
        .apply(clean_number)
        .sum()
    )


    # --------------------------------------------
    # БЖВ
    # --------------------------------------------

    protein = (
        day["Білки"]
        .apply(clean_number)
        .sum()
    )


    fat = (
        day["Жири"]
        .apply(clean_number)
        .sum()
    )


    carbs = (
        day["Вуглеводи"]
        .apply(clean_number)
        .sum()
    )


    # --------------------------------------------
    # ГОДИННИК
    # --------------------------------------------

    watch = day[
        day["Тип"]
        .apply(clean_text)
        ==
        "Годинник"
    ]


    watch_calories = 0.0


    if not watch.empty:

        watch_calories = clean_number(
            watch.iloc[-1]["Спалено"]
        )


    # --------------------------------------------
    # ТРЕНУВАННЯ
    # --------------------------------------------

    workouts = day[
        day["Тип"]
        .apply(clean_text)
        ==
        "Тренування"
    ]


    workout_calories = (
        workouts["Спалено"]
        .apply(clean_number)
        .sum()
    )


    # --------------------------------------------
    # БАЗОВА ВИТРАТА
    # --------------------------------------------

    today = now_local().strftime(
        "%Y-%m-%d"
    )


    if selected_date == today:

        current = now_local()

        hours_passed = (
            current.hour
            +
            current.minute / 60
        )

        base_burn = (
            clean_number(
                profile_settings[
                    "bmr_daily"
                ]
            )
            /
            24
        ) * hours_passed

    else:

        base_burn = clean_number(
            profile_settings[
                "bmr_daily"
            ]
        )


    # --------------------------------------------
    # ЗАГАЛЬНО СПАЛЕНО
    # --------------------------------------------

    total_burned = (
        base_burn
        +
        watch_calories
        +
        workout_calories
    )


    balance = (
        total_burned
        -
        consumed
    )


    return {

        "day": day,

        "consumed": consumed,

        "protein": protein,

        "fat": fat,

        "carbs": carbs,

        "watch": watch_calories,

        "workout": workout_calories,

        "base": base_burn,

        "burned": total_burned,

        "balance": balance
    }


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    f"⚖️ Мій Фітнес — {profile}"
)


# ============================================================
# ПОТОЧНА ВАГА
# ============================================================

current_weight = calculate_current_weight(
    df,
    settings
)


st.markdown(
    f"""
<h2 style="
    margin-top:0;
    margin-bottom:10px;
">
⚖️ Поточна вага:
<span style="color:#ffffff;">
~{current_weight:.1f} кг
</span>
</h2>
""",
    unsafe_allow_html=True
)


# ============================================================
# ВИБІР ДАТИ
# ============================================================

today = now_local().strftime(
    "%Y-%m-%d"
)


available_dates = [
    today
]


for date_value in (
    df["Дата"]
    .apply(clean_text)
    .unique()
):

    if (
        date_value
        and
        date_value not in available_dates
    ):

        available_dates.append(
            date_value
        )


selected_date = st.selectbox(
    "📅 День",
    available_dates
)


# ============================================================
# ДОДАВАННЯ
# ============================================================

st.subheader(
    "📝 Влог"
)


user_input = st.text_input(
    "Запис",
    placeholder=(
        "Наприклад: "
        "2 яйця, 150 г курки і рис"
    ),
    label_visibility="collapsed"
)


add_col1, add_col2 = st.columns(
    [4, 1]
)


with add_col1:

    add_button = st.button(
        "➕ Додати в лог",
        type="primary",
        use_container_width=True
    )


with add_col2:

    watch_button = st.button(
        "⌚ Годинник",
        use_container_width=True
    )


# ============================================================
# ДОДАТИ ЇЖУ / ТРЕНУВАННЯ ЧЕРЕЗ GEMINI
# ============================================================

if add_button:

    if not user_input.strip():

        st.warning(
            "Введи запис."
        )

    else:

        prompt = """
Ти аналізатор фітнес-щоденника.

Проаналізуй текст користувача.

Поверни ТІЛЬКИ JSON:

{
  "description": "...",
  "type": "Їжа",
  "consumed_kcal": 0,
  "burned_kcal": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0
}

Можливі типи:

Їжа
Тренування

Якщо це їжа:

consumed_kcal =
оцінка калорій їжі.

burned_kcal = 0.

protein =
білки в грамах.

fat =
жири в грамах.

carbs =
вуглеводи в грамах.

Якщо це тренування:

consumed_kcal = 0.

burned_kcal =
оцінка спалених калорій.

protein = 0.
fat = 0.
carbs = 0.

Якщо кількість продукту не вказана,
зроби розумну оцінку.

Всі числа повинні бути числовими.

Не використовуй markdown.

Поверни тільки JSON.
"""


        try:

            response = client.models.generate_content(
                model="gemini-2.5-flash",

                contents=[
                    prompt,
                    "\nЗапис:\n",
                    user_input
                ],

                config=types.GenerateContentConfig(
                    response_mime_type=
                        "application/json"
                )
            )


            raw = (
                response.text
                or ""
            ).strip()


            if raw.startswith("```"):

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


            description = clean_text(
                result.get(
                    "description",
                    user_input
                )
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


            if entry_type == "Їжа":

                burned_kcal = 0


            else:

                consumed_kcal = 0
                protein = 0
                fat = 0
                carbs = 0


            add_undo_snapshot(
                df
            )


            current = now_local()


            new_row = {

                "Дата":
                    current.strftime(
                        "%Y-%m-%d"
                    ),

                "Час":
                    current.strftime(
                        "%H:%M"
                    ),

                "Опис":
                    description,

                "Тип":
                    entry_type,

                "Спожито":
                    consumed_kcal,

                "Спалено":
                    burned_kcal,

                "Білки":
                    protein,

                "Жири":
                    fat,

                "Вуглеводи":
                    carbs
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


            save_data(df)


            st.success(
                "✅ Додано."
            )


            st.rerun()


        except Exception as error:

            st.error(
                f"❌ Не вдалося "
                f"розібрати запис: {error}"
            )


# ============================================================
# ОНОВЛЕННЯ ГОДИННИКА
# ============================================================

if watch_button:

    watch_value = st.number_input(
        "🔥 Калорії активності за годинником",
        min_value=0.0,
        value=0.0,
        step=1.0,
        key="watch_manual_value"
    )


    if watch_value > 0:

        add_undo_snapshot(
            df
        )


        current = now_local()


        df = update_watch_value(
            df,
            today,
            current.strftime(
                "%H:%M"
            ),
            watch_value
        )


        save_data(df)


        st.success(
            f"⌚ Значення замінено: "
            f"{watch_value:.0f} ккал"
        )


        st.rerun()


# ============================================================
# UNDO
# ============================================================

history = load_undo()


undo_col1, undo_col2 = st.columns(
    [3, 1]
)


with undo_col1:

    st.caption(
        f"↩️ Доступно скасувань: "
        f"{len(history)} / 10"
    )


with undo_col2:

    undo_button = st.button(
        "↩️ Відмінити",
        disabled=(
            len(history) == 0
        ),
        use_container_width=True
    )


if undo_button:

    restored = undo_last()


    if restored is not None:

        df = restored

        save_data(df)

        st.success(
            "↩️ Зміну скасовано."
        )

        st.rerun()


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

with st.expander(
    "⚙️ Налаштування"
):

    calories_target = st.number_input(
        "🎯 Добова норма калорій",
        min_value=0,
        value=int(
            settings["calories"]
        ),
        step=50
    )


    protein_target = st.number_input(
        "🥩 Білки — потреба, г",
        min_value=0,
        value=int(
            settings["protein"]
        ),
        step=5
    )


    fat_target = st.number_input(
        "🥑 Жири — потреба, г",
        min_value=0,
        value=int(
            settings["fat"]
        ),
        step=5
    )


    carbs_target = st.number_input(
        "🍞 Вуглеводи — потреба, г",
        min_value=0,
        value=int(
            settings["carbs"]
        ),
        step=5
    )


    bmr_target = st.number_input(
        "🔥 Базова витрата за добу, ккал",
        min_value=0,
        value=int(
            settings["bmr_daily"]
        ),
        step=50
    )


    initial_weight = st.number_input(
        "⚖️ Початкова вага, кг",
        min_value=0.0,
        value=float(
            settings["initial_weight"]
        ),
        step=0.1
    )


    if st.button(
        "💾 Зберегти",
        use_container_width=True
    ):

        settings = {

            "calories":
                calories_target,

            "protein":
                protein_target,

            "fat":
                fat_target,

            "carbs":
                carbs_target,

            "bmr_daily":
                bmr_target,

            "initial_weight":
                initial_weight
        }


        save_settings(
            settings
        )


        st.success(
            "✅ Збережено."
        )


        st.rerun()


# ============================================================
# ДАНІ ДНЯ
# ============================================================

day_info = calculate_day(
    df,
    selected_date,
    settings
)


day_df = day_info["day"]


consumed = day_info[
    "consumed"
]

protein = day_info[
    "protein"
]

fat = day_info[
    "fat"
]

carbs = day_info[
    "carbs"
]

watch_calories = day_info[
    "watch"
]

workout_calories = day_info[
    "workout"
]

base_burn = day_info[
    "base"
]

total_burned = day_info[
    "burned"
]

balance = day_info[
    "balance"
]


# ============================================================
# СТАТУС
# ============================================================

if balance > 0:

    status = "ДЕФІЦИТ"

    status_icon = "📉"

    status_color = "#35D07F"

    balance_text = (
        f"−{balance:.0f} ккал"
    )


elif balance < 0:

    status = "ПРОФІЦИТ"

    status_icon = "📈"

    status_color = "#FF6262"

    balance_text = (
        f"+{abs(balance):.0f} ккал"
    )


else:

    status = "БАЛАНС"

    status_icon = "⚖️"

    status_color = "#FFD166"

    balance_text = (
        "0 ккал"
    )


# ============================================================
# КРУЖОК
# ============================================================

total_macro = (
    protein
    +
    fat
    +
    carbs
)


if total_macro > 0:

    protein_deg = (
        protein
        /
        total_macro
        *
        360
    )

    fat_deg = (
        protein_deg
        +
        fat
        /
        total_macro
        *
        360
    )

else:

    protein_deg = 0

    fat_deg = 0


donut_html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<style>

html,
body {{

    margin: 0;

    padding: 0;

    width: 100%;

    height: 100%;

    background: transparent;

    overflow: hidden;
}}


body {{

    display: flex;

    justify-content: center;

    align-items: center;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;
}}


.wrapper {{

    width: 300px;

    height: 310px;

    display: flex;

    justify-content: center;

    align-items: center;
}}


.donut {{

    width: 230px;

    height: 230px;

    border-radius: 50%;

    background:
        conic-gradient(

            #36A2EB
            0deg
            {protein_deg:.2f}deg,

            #FFCE56
            {protein_deg:.2f}deg
            {fat_deg:.2f}deg,

            #FF6384
            {fat_deg:.2f}deg
            360deg
        );

    display: flex;

    justify-content: center;

    align-items: center;

    box-shadow:
        0 0 40px
        rgba(0,0,0,0.70);
}}


.hole {{

    width: 166px;

    height: 166px;

    border-radius: 50%;

    background:
        #15171D;

    display: flex;

    flex-direction: column;

    justify-content: center;

    align-items: center;

    text-align: center;
}}


.status {{

    color:
        {status_color};

    font-size:
        13px;

    font-weight:
        900;
}}


.balance {{

    color:
        {status_color};

    font-size:
        23px;

    font-weight:
        900;

    margin-top:
        3px;
}}


.small {{

    color:
        #C7C7C7;

    font-size:
        10px;

    margin-top:
        4px;
}}


.weight {{

    color:
        #FFFFFF;

    font-size:
        11px;

    font-weight:
        800;

    margin-top:
        5px;
}}

</style>

</head>

<body>

<div class="wrapper">

<div class="donut">

<div class="hole">

<div class="status">
{status_icon} {status}
</div>

<div class="balance">
{balance_text}
</div>

<div class="small">
🍽️ {consumed:.0f} ккал
</div>

<div class="small">
🔥 {total_burned:.0f} ккал
</div>

<div class="weight">
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
    height=315,
    scrolling=False
)


# ============================================================
# КАЛОРІЇ
# ============================================================

st.subheader(
    "🔥 Калорії"
)


c1, c2, c3 = st.columns(3)


with c1:

    st.metric(
        "🍽️ З'їдено",
        f"{consumed:.0f} ккал"
    )


with c2:

    st.metric(
        "⌚ Годинник",
        f"{watch_calories:.0f} ккал"
    )


with c3:

    st.metric(
        "💪 Тренування",
        f"{workout_calories:.0f} ккал"
    )


# ============================================================
# БЖВ ПОТРЕБА / З'ЇДЕНО
# ============================================================

st.subheader(
    "🥗 БЖВ — потреба / з'їдено"
)


b1, b2, b3 = st.columns(3)


with b1:

    st.metric(
        "🥩 Білки",
        (
            f"{protein:.0f} / "
            f"{clean_number(settings['protein']):.0f} г"
        )
    )


with b2:

    st.metric(
        "🥑 Жири",
        (
            f"{fat:.0f} / "
            f"{clean_number(settings['fat']):.0f} г"
        )
    )


with b3:

    st.metric(
        "🍞 Вуглеводи",
        (
            f"{carbs:.0f} / "
            f"{clean_number(settings['carbs']):.0f} г"
        )
    )


# ============================================================
# ПРОГРЕС КАЛОРІЙ
# ============================================================

target_calories = clean_number(
    settings["calories"]
)


if target_calories > 0:

    progress = (
        consumed
        /
        target_calories
    )

else:

    progress = 0


progress = max(
    0,
    min(
        1,
        progress
    )
)


st.progress(
    progress
)


st.caption(
    f"🍽️ {consumed:.0f} / "
    f"{target_calories:.0f} ккал"
)


# ============================================================
# ЛОГ
# ============================================================

st.subheader(
    f"📝 Лог за {selected_date}"
)


if day_df.empty:

    st.info(
        "За цей день записів немає."
    )

else:

    # Виводимо від нових до старих
    for index in reversed(
        day_df.index.tolist()
    ):

        row = df.loc[index]


        description = clean_text(
            row["Опис"]
        )


        time_value = clean_text(
            row["Час"]
        )[:5]


        row_type = clean_text(
            row["Тип"]
        )


        consumed_value = clean_number(
            row["Спожито"]
        )


        burned_value = clean_number(
            row["Спалено"]
        )


        # ====================================================
        # ЇЖА
        # ====================================================

        if row_type == "Їжа":

            icon = "🍽️"

            title = (
                f"{description} "
                f"— {consumed_value:.0f} ккал"
            )

            right_text = (
                f"+{consumed_value:.0f} ккал"
            )


        # ====================================================
        # ГОДИННИК
        # ====================================================

        elif row_type == "Годинник":

            icon = "⌚"

            title = (
                "Активність за даними годинника"
            )

            right_text = (
                f"-{burned_value:.0f} ккал"
            )


        # ====================================================
        # ТРЕНУВАННЯ
        # ====================================================

        elif row_type == "Тренування":

            icon = "💪"

            title = (
                f"{description} "
                f"— {burned_value:.0f} ккал"
            )

            right_text = (
                f"-{burned_value:.0f} ккал"
            )


        else:

            icon = "📝"

            title = description

            right_text = ""


        # ====================================================
        # КАРТКА
        # ====================================================

        with st.container(
            border=True
        ):

            left, right = st.columns(
                [4, 1]
            )


            with left:

                st.markdown(
                    f"""
                    <div style="
                        font-size:16px;
                        font-weight:700;
                        padding:4px 0;
                    ">
                    {time_value}
                    &nbsp;
                    {icon}
                    &nbsp;
                    {title}
                    </div>
                    """,
                    unsafe_allow_html=True
                )


            with right:

                st.markdown(
                    f"""
                    <div style="
                        text-align:right;
                        font-weight:800;
                        padding-top:6px;
                    ">
                    {right_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )


            # =================================================
            # РЕДАКТОР
            # =================================================

            with st.expander(
                "✏️ Редагувати"
            ):

                edit_description = st.text_input(
                    "Опис",
                    value=description,
                    key=(
                        f"desc_{index}"
                    )
                )


                type_options = [
                    "Їжа",
                    "Тренування",
                    "Годинник"
                ]


                if row_type in type_options:

                    current_type_index = (
                        type_options.index(
                            row_type
                        )
                    )

                else:

                    current_type_index = 0


                edit_type = st.selectbox(
                    "Тип",
                    type_options,
                    index=current_type_index,
                    key=(
                        f"type_{index}"
                    )
                )


                # =================================================
                # ЇЖА
                # =================================================

                if edit_type == "Їжа":

                    edit_consumed = st.number_input(
                        "🍽️ Калорії",
                        min_value=0.0,
                        value=consumed_value,
                        step=1.0,
                        key=(
                            f"eat_{index}"
                        )
                    )


                    e1, e2, e3 = (
                        st.columns(3)
                    )


                    with e1:

                        edit_protein = st.number_input(
                            "Білки, г",
                            min_value=0.0,
                            value=clean_number(
                                row["Білки"]
                            ),
                            step=1.0,
                            key=(
                                f"p_{index}"
                            )
                        )


                    with e2:

                        edit_fat = st.number_input(
                            "Жири, г",
                            min_value=0.0,
                            value=clean_number(
                                row["Жири"]
                            ),
                            step=1.0,
                            key=(
                                f"f_{index}"
                            )
                        )


                    with e3:

                        edit_carbs = st.number_input(
                            "Вуглеводи, г",
                            min_value=0.0,
                            value=clean_number(
                                row["Вуглеводи"]
                            ),
                            step=1.0,
                            key=(
                                f"c_{index}"
                            )
                        )


                    edit_burned = 0.0


                # =================================================
                # ГОДИННИК
                # =================================================

                elif edit_type == "Годинник":

                    st.info(
                        "⌚ Це накопичене "
                        "значення за день. "
                        "При зміні воно "
                        "замінить старе."
                    )


                    edit_burned = st.number_input(
                        "🔥 Активність годинника, ккал",
                        min_value=0.0,
                        value=burned_value,
                        step=1.0,
                        key=(
                            f"watch_{index}"
                        )
                    )


                    edit_consumed = 0.0

                    edit_protein = 0.0

                    edit_fat = 0.0

                    edit_carbs = 0.0


                # =================================================
                # ТРЕНУВАННЯ
                # =================================================

                else:

                    edit_burned = st.number_input(
                        "🔥 Спалено, ккал",
                        min_value=0.0,
                        value=burned_value,
                        step=1.0,
                        key=(
                            f"workout_{index}"
                        )
                    )


                    edit_consumed = 0.0

                    edit_protein = 0.0

                    edit_fat = 0.0

                    edit_carbs = 0.0


                save_col, delete_col = (
                    st.columns(2)
                )


                # =================================================
                # ЗБЕРЕГТИ
                # =================================================

                with save_col:

                    if st.button(
                        "💾 Зберегти",
                        key=(
                            f"save_{index}"
                        ),
                        use_container_width=True
                    ):

                        add_undo_snapshot(
                            df
                        )


                        # -----------------------------------------
                        # ЯКЩО ЦЕ ГОДИННИК
                        # -----------------------------------------

                        if edit_type == "Годинник":

                            # Видаляємо всі старі
                            # записи годинника
                            # за цей день.

                            indexes_to_remove = (
                                df[
                                    (
                                        df["Дата"]
                                        .apply(clean_text)
                                        ==
                                        clean_text(
                                            row["Дата"]
                                        )
                                    )
                                    &
                                    (
                                        df["Тип"]
                                        .apply(clean_text)
                                        ==
                                        "Годинник"
                                    )
                                ]
                                .index
                                .tolist()
                            )


                            df = df.drop(
                                indexes_to_remove
                            )


                            # Створюємо ОДИН
                            # актуальний запис.

                            new_watch = {

                                "Дата":
                                    clean_text(
                                        row["Дата"]
                                    ),

                                "Час":
                                    time_value,

                                "Опис":
                                    "Активність "
                                    "за даними годинника",

                                "Тип":
                                    "Годинник",

                                "Спожито":
                                    0,

                                "Спалено":
                                    edit_burned,

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


                        # -----------------------------------------
                        # ЗВИЧАЙНИЙ ЗАПИС
                        # -----------------------------------------

                        else:

                            # Якщо редагуємо
                            # звичайний запис.

                            # Для їжі
                            # тільки спожито.

                            if edit_type == "Їжа":

                                final_consumed = (
                                    edit_consumed
                                )

                                final_burned = 0.0


                            else:

                                final_consumed = 0.0

                                final_burned = (
                                    edit_burned
                                )


                            df.at[
                                index,
                                "Опис"
                            ] = (
                                edit_description
                            )


                            df.at[
                                index,
                                "Тип"
                            ] = (
                                edit_type
                            )


                            df.at[
                                index,
                                "Спожито"
                            ] = (
                                final_consumed
                            )


                            df.at[
                                index,
                                "Спалено"
                            ] = (
                                final_burned
                            )


                            df.at[
                                index,
                                "Білки"
                            ] = (
                                edit_protein
                            )


                            df.at[
                                index,
                                "Жири"
                            ] = (
                                edit_fat
                            )


                            df.at[
                                index,
                                "Вуглеводи"
                            ] = (
                                edit_carbs
                            )


                        save_data(
                            df
                        )


                        st.success(
                            "✅ Запис оновлено."
                        )


                        st.rerun()


                # =================================================
                # ВИДАЛИТИ
                # =================================================

                with delete_col:

                    if st.button(
                        "🗑️ Видалити",
                        key=(
                            f"delete_{index}"
                        ),
                        use_container_width=True
                    ):

                        add_undo_snapshot(
                            df
                        )


                        if row_type == "Годинник":

                            # Видаляємо весь
                            # запис годинника
                            # за цей день.

                            indexes_to_remove = (
                                df[
                                    (
                                        df["Дата"]
                                        .apply(clean_text)
                                        ==
                                        clean_text(
                                            row["Дата"]
                                        )
                                    )
                                    &
                                    (
                                        df["Тип"]
                                        .apply(clean_text)
                                        ==
                                        "Годинник"
                                    )
                                ]
                                .index
                            )


                            df = df.drop(
                                indexes_to_remove
                            )


                        else:

                            df = df.drop(
                                index
                            )


                        df = (
                            df
                            .reset_index(
                                drop=True
                            )
                        )


                        save_data(
                            df
                        )


                        st.success(
                            "🗑️ Запис видалено."
                        )


                        st.rerun()


# ============================================================
# НИЖНІЙ СТАТУС
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
        "⚖️ Калорійний баланс: 0 ккал"
    )


# ============================================================
# ТЕХНІЧНА ІНФОРМАЦІЯ
# ============================================================

st.caption(
    "⚖️ Орієнтир для зміни ваги: "
    "7700 ккал накопиченого дефіциту "
    "≈ 1 кг."
)
