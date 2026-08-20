import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from google import genai
from google.genai import types


# ============================================================
# НАЛАШТУВАННЯ STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="🏋️",
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

EXCEL_FILE = (
    f"fitness_entries_{profile_id}.xlsx"
)

SETTINGS_FILE = (
    f"user_settings_{profile_id}.json"
)

TRASH_FILE = (
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
            rgba(0,0,0,0.70),
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


/* =========================================================
   КНОПКИ
   ========================================================= */

div.stButton > button {{

    min-height: 46px !important;

    border-radius: 14px !important;

    border:
        1px solid
        rgba(255,255,255,0.12) !important;

    background:
        linear-gradient(
            135deg,
            rgba(45,45,53,0.98),
            rgba(18,18,23,0.98)
        ) !important;

    color:
        #ffffff !important;

    font-weight:
        700 !important;

    box-shadow:
        0 7px 20px
        rgba(0,0,0,0.35);

    transition:
        all 0.18s ease;

}}


div.stButton > button:hover {{

    transform:
        translateY(-2px);

    border-color:
        rgba(54,162,235,0.65) !important;

    box-shadow:
        0 10px 28px
        rgba(0,0,0,0.45);

}}


/* =========================================================
   INPUT
   ========================================================= */

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{

    border-radius:
        12px !important;

    background:
        rgba(18,18,22,0.94) !important;

    color:
        #ffffff !important;

}}


/* =========================================================
   METRIC
   ========================================================= */

div[data-testid="stMetric"] {{

    background:
        rgba(20,20,24,0.88);

    border:
        1px solid
        rgba(255,255,255,0.08);

    border-radius:
        14px;

    padding:
        10px;

}}


/* =========================================================
   КОНТЕЙНЕРИ ЛОГУ
   ========================================================= */

div[data-testid="stVerticalBlockBorderWrapper"] {{

    background:
        rgba(20,20,24,0.82);

    border-radius:
        14px;

}}


/* =========================================================
   ЗАГОЛОВКИ
   ========================================================= */

h1,
h2,
h3 {{

    font-weight:
        800;

}}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "camera_enabled" not in st.session_state:

    st.session_state[
        "camera_enabled"
    ] = False


if "settings_open" not in st.session_state:

    st.session_state[
        "settings_open"
    ] = False


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
        "Додай GEMINI_API_KEY у "
        "Streamlit Secrets."
    )

    st.stop()


client = genai.Client(
    api_key=api_key
)


# ============================================================
# НАЛАШТУВАННЯ
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


def load_data():

    if not os.path.exists(
        EXCEL_FILE
    ):

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


    df["Дата"] = (
        df["Дата"]
        .apply(clean_text)
    )


    df["Час"] = (
        df["Час"]
        .apply(clean_text)
    )


    df["Опис"] = (
        df["Опис"]
        .apply(clean_text)
    )


    df["Тип"] = (
        df["Тип"]
        .apply(clean_text)
    )


    return df


df = load_data()


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


    total_deficit = 0.0


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

            bmr = (
                bmr_daily / 24
            ) * hours

        else:

            bmr = bmr_daily


        if profile_settings.get(
            "include_exercise_in_deficit",
            True
        ):

            burned = (
                bmr
                +
                exercise
            )

        else:

            burned = bmr


        daily_balance = (
            burned
            -
            eaten
        )


        total_deficit += (
            daily_balance
        )


    # 7700 ккал ≈ 1 кг жиру
    weight_change = (
        total_deficit / 7700
    )


    current_weight = (
        initial_weight
        -
        weight_change
    )


    return max(
        0.0,
        current_weight
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
    f"🏋️ Мій Фітнес — {profile}"
)


st.markdown(
    f"### ⚖️ Поточна вага: ~{current_weight:.1f} кг"
)


# ============================================================
# ВВЕДЕННЯ
# ============================================================

user_input = st.text_input(
    "📥 Що з'їв / тренування",
    placeholder=(
        "Наприклад: куряча грудка 200 г "
        "або тренування 45 хв"
    )
)


# ============================================================
# КАМЕРА
# ============================================================

camera_col1, camera_col2 = (
    st.columns(2)
)


with camera_col1:

    if not st.session_state[
        "camera_enabled"
    ]:

        if st.button(
            "📸 Увімкнути камеру",
            use_container_width=True
        ):

            st.session_state[
                "camera_enabled"
            ] = True

            st.rerun()

    else:

        if st.button(
            "❌ Вимкнути камеру",
            use_container_width=True
        ):

            st.session_state[
                "camera_enabled"
            ] = False

            st.rerun()


photo = None


if st.session_state[
    "camera_enabled"
]:

    photo = st.camera_input(
        "📷 Фото їжі / тренування"
    )


# ============================================================
# ЗАПИС
# ============================================================

if st.button(
    "✅ Додати запис",
    type="primary",
    use_container_width=True
):

    if not user_input and not photo:

        st.warning(
            "Введи запис або зроби фото."
        )

    else:

        try:

            # ==================================================
            # GEMINI PROMPT
            # ==================================================

            prompt = """
Ти аналізуєш запис для фітнес-трекера.

Потрібно визначити:
1. їжа це чи тренування;
2. приблизні калорії;
3. білки;
4. жири;
5. вуглеводи;
6. якщо це тренування — спалені калорії.

Поверни ТІЛЬКИ JSON такого формату:

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
Якщо даних немає — став 0.
Не додавай markdown.
Поверни тільки JSON.
"""


            # ==================================================
            # ФОТО
            # ==================================================

            if photo:

                image_bytes = (
                    photo.getvalue()
                )


                image_part = (
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    )
                )


                response = (
                    client.models.generate_content(
                        model="gemini-2.5-flash",

                        contents=[
                            image_part,
                            prompt
                        ],

                        config=types.GenerateContentConfig(
                            response_mime_type=(
                                "application/json"
                            )
                        )
                    )
                )


            # ==================================================
            # ТЕКСТ
            # ==================================================

            else:

                text_prompt = (
                    prompt
                    +
                    "\n\nЗапис користувача:\n"
                    +
                    user_input
                )


                response = (
                    client.models.generate_content(
                        model="gemini-2.5-flash",

                        contents=text_prompt,

                        config=types.GenerateContentConfig(
                            response_mime_type=(
                                "application/json"
                            )
                        )
                    )
                )


            # ==================================================
            # JSON
            # ==================================================

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


            description = clean_text(
                result.get(
                    "description",
                    user_input or "Запис"
                )
            )


            if not description:

                description = (
                    user_input
                    or "Запис"
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


            consumed_kcal = (
                clean_number(
                    result.get(
                        "consumed_kcal",
                        0
                    )
                )
            )


            burned_kcal = (
                clean_number(
                    result.get(
                        "burned_kcal",
                        0
                    )
                )
            )


            protein_value = (
                clean_number(
                    result.get(
                        "protein",
                        0
                    )
                )
            )


            fat_value = (
                clean_number(
                    result.get(
                        "fat",
                        0
                    )
                )
            )


            carbs_value = (
                clean_number(
                    result.get(
                        "carbs",
                        0
                    )
                )
            )


            if entry_type == "Тренування":

                consumed_kcal = 0.0

            else:

                burned_kcal = 0.0


            # ==================================================
            # НОВИЙ ЗАПИС
            # ==================================================

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
                    description,

                "Тип":
                    entry_type,

                "Спожито":
                    consumed_kcal,

                "Спалено":
                    burned_kcal,

                "Білки":
                    protein_value,

                "Жири":
                    fat_value,

                "Вуглеводи":
                    carbs_value
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


            df.to_excel(
                EXCEL_FILE,
                index=False
            )


            st.session_state[
                "camera_enabled"
            ] = False


            st.success(
                "✅ Запис успішно додано!"
            )


            st.rerun()


        except json.JSONDecodeError:

            st.error(
                "❌ Gemini повернув неправильний JSON."
            )


            st.code(
                raw
            )


        except Exception as error:

            st.error(
                f"❌ Помилка: {error}"
            )


# ============================================================
# РОЗДІЛ
# ============================================================

st.divider()


# ============================================================
# ДАТИ
# ============================================================

today = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")


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


selected_date = st.selectbox(
    "📅 День",
    dates
)


# ============================================================
# КНОПКИ
# ============================================================

button1, button2 = (
    st.columns(2)
)


with button1:

    settings_button = st.button(
        "⚙️ Налаштування",
        use_container_width=True
    )


with button2:

    delete_button = st.button(
        "🗑️ Видалити останній",
        use_container_width=True
    )


if settings_button:

    st.session_state[
        "settings_open"
    ] = not st.session_state[
        "settings_open"
    ]

    st.rerun()


# ============================================================
# ВИДАЛЕННЯ
# ============================================================

if delete_button:

    if df.empty:

        st.warning(
            "Лог порожній."
        )

    else:

        last_row = (
            df.iloc[-1]
            .to_dict()
        )


        try:

            with open(
                TRASH_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    [last_row],
                    file,
                    ensure_ascii=False,
                    indent=2,
                    default=str
                )

        except Exception:

            pass


        df = (
            df.iloc[:-1]
            .reset_index(drop=True)
        )


        df.to_excel(
            EXCEL_FILE,
            index=False
        )


        st.success(
            "🗑️ Останній запис видалено."
        )


        st.rerun()


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

if st.session_state[
    "settings_open"
]:

    st.subheader(
        "⚙️ Налаштування"
    )


    calories_value = st.number_input(
        "🎯 Ціль калорій",
        min_value=0,
        value=int(
            settings["calories"]
        ),
        step=50
    )


    protein_value = st.number_input(
        "🥩 Білки, г",
        min_value=0,
        value=int(
            settings["protein"]
        ),
        step=5
    )


    fat_value = st.number_input(
        "🥑 Жири, г",
        min_value=0,
        value=int(
            settings["fat"]
        ),
        step=5
    )


    carbs_value = st.number_input(
        "🍞 Вуглеводи, г",
        min_value=0,
        value=int(
            settings["carbs"]
        ),
        step=5
    )


    bmr_value = st.number_input(
        "🔥 Добова базова витрата",
        min_value=0,
        value=int(
            settings["bmr_daily"]
        ),
        step=50
    )


    initial_weight_value = (
        st.number_input(
            "⚖️ Початкова вага, кг",
            min_value=0.0,
            value=float(
                settings["initial_weight"]
            ),
            step=0.1
        )
    )


    exercise_in_deficit = (
        st.checkbox(
            "💪 Враховувати спалені "
            "на тренуванні калорії "
            "в дефіциті",

            value=settings.get(
                "include_exercise_in_deficit",
                True
            )
        )
    )


    if st.button(
        "💾 Зберегти",
        type="primary",
        use_container_width=True
    ):

        new_settings = {

            "calories":
                calories_value,

            "protein":
                protein_value,

            "fat":
                fat_value,

            "carbs":
                carbs_value,

            "bmr_daily":
                bmr_value,

            "initial_weight":
                initial_weight_value,

            "include_exercise_in_deficit":
                exercise_in_deficit
        }


        save_settings(
            new_settings
        )


        st.session_state[
            "settings_open"
        ] = False


        st.success(
            "✅ Налаштування збережено."
        )


        st.rerun()


# ============================================================
# ДАНІ ВИБРАНОГО ДНЯ
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
# СТАТИСТИКА ДНЯ
# ============================================================

consumed = 0.0
exercise_burned = 0.0
protein = 0.0
fat = 0.0
carbs = 0.0


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


# ============================================================
# ВИТРАТА КАЛОРІЙ
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
# БАЛАНС
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

    status_value = "0 ккал"


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
# КРУЖОК
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

    width: 260px;

    height: 285px;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

}}


.donut {{

    width: 210px;

    height: 210px;

    border-radius: 50%;

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

    display: flex;

    justify-content: center;

    align-items: center;

    box-shadow:
        0 0 30px
        rgba(0,0,0,0.65);

}}


.hole {{

    width: 150px;

    height: 150px;

    border-radius: 50%;

    background:
        #15171c;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    text-align: center;

    box-shadow:
        inset 0 0 22px
        rgba(0,0,0,0.9);

}}


.status {{

    color:
        {status_color};

    font-size:
        13px;

    font-weight:
        900;

    letter-spacing:
        0.4px;

}}


.balance {{

    color:
        {status_color};

    font-size:
        22px;

    font-weight:
        900;

    margin-top:
        3px;

}}


.consumed {{

    color:
        #bbbbbb;

    font-size:
        10px;

    margin-top:
        8px;

}}


.burned {{

    color:
        #bbbbbb;

    font-size:
        10px;

    margin-top:
        3px;

}}


.weight {{

    color:
        #ffffff;

    font-size:
        10px;

    font-weight:
        800;

    margin-top:
        4px;

}}


.macros {{

    width:
        210px;

    display:
        flex;

    justify-content:
        space-around;

    margin-top:
        8px;

    padding:
        7px 0;

    border-radius:
        11px;

    background:
        rgba(20,20,24,0.96);

    border:
        1px solid
        rgba(255,255,255,0.10);

    font-size:
        10px;

    font-weight:
        800;

}}


.protein {{
    color: #36A2EB;
}}

.fat {{
    color: #FFCE56;
}}

.carbs {{
    color: #FF6384;
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
                {status_value}
            </div>

            <div class="consumed">
                🍽️ {consumed:.0f} /
                {clean_number(settings["calories"]):.0f}
                ккал
            </div>

            <div class="burned">
                🔥 {total_burned:.0f} ккал
            </div>

            <div class="weight">
                ⚖️ {current_weight:.1f} кг
            </div>

        </div>

    </div>


    <div class="macros">

        <span class="protein">
            🥩 {protein:.0f}г
        </span>

        <span class="fat">
            🥑 {fat:.0f}г
        </span>

        <span class="carbs">
            🍞 {carbs:.0f}г
        </span>

    </div>

</div>

</body>

</html>
"""


# ============================================================
# ВИВІД КРУЖКА
# ============================================================

components.html(
    donut_html,
    height=300,
    scrolling=False
)


# ============================================================
# СТАТИСТИКА — ТУТ ВЖЕ НЕМАЄ HTML
# ============================================================

st.subheader(
    "📊 Статистика"
)


stat1, stat2, stat3, stat4 = (
    st.columns(4)
)


with stat1:

    st.metric(
        "🍽️ З'їдено",
        f"{consumed:.0f} ккал"
    )


with stat2:

    st.metric(
        "🔥 Спалено",
        f"{total_burned:.0f} ккал"
    )


with stat3:

    if balance > 0:

        st.metric(
            "📉 Дефіцит",
            f"{balance:.0f} ккал"
        )

    elif balance < 0:

        st.metric(
            "📈 Профіцит",
            f"{abs(balance):.0f} ккал"
        )

    else:

        st.metric(
            "⚖️ Баланс",
            "0 ккал"
        )


with stat4:

    st.metric(
        "⚖️ Вага",
        f"{current_weight:.1f} кг"
    )


# ============================================================
# МАКРОСИ
# ============================================================

st.subheader(
    "🥗 Макроси"
)


macro1, macro2, macro3 = (
    st.columns(3)
)


with macro1:

    st.metric(
        "🥩 Білки",
        (
            f"{protein:.0f} / "
            f"{clean_number(settings['protein']):.0f} г"
        )
    )


with macro2:

    st.metric(
        "🥑 Жири",
        (
            f"{fat:.0f} / "
            f"{clean_number(settings['fat']):.0f} г"
        )
    )


with macro3:

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

    calorie_progress = (
        consumed
        /
        target_calories
    )

    calorie_progress = min(
        max(
            calorie_progress,
            0.0
        ),
        1.0
    )

else:

    calorie_progress = 0.0


st.progress(
    calorie_progress
)


st.caption(
    f"🍽️ {consumed:.0f} "
    f"із {target_calories:.0f} ккал"
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

    # Останні зверху
    reversed_day = (
        day_df.iloc[::-1]
    )


    for _, row in reversed_day.iterrows():

        time_value = clean_text(
            row.get(
                "Час",
                ""
            )
        )[:5]


        description = clean_text(
            row.get(
                "Опис",
                ""
            )
        )


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


            kcal_text = (
                f"-{kcal:.0f} ккал"
            )

        else:

            icon = "🍽️"

            kcal = clean_number(
                row.get(
                    "Спожито",
                    0
                )
            )


            kcal_text = (
                f"+{kcal:.0f} ккал"
            )


        with st.container(
            border=True
        ):

            log_left, log_right = (
                st.columns(
                    [4, 1]
                )
            )


            with log_left:

                if time_value:

                    st.write(
                        f"**{time_value}** "
                        f"{icon} "
                        f"{description}"
                    )

                else:

                    st.write(
                        f"{icon} "
                        f"{description}"
                    )


            with log_right:

                st.write(
                    f"**{kcal_text}**"
                )


# ============================================================
# ПІДСУМОК
# ============================================================

st.divider()


if balance > 0:

    st.success(
        f"📉 Дефіцит за день: "
        f"{balance:.0f} ккал"
    )

elif balance < 0:

    st.error(
        f"📈 Профіцит за день: "
        f"{abs(balance):.0f} ккал"
    )

else:

    st.info(
        "⚖️ Сьогодні баланс калорій приблизно нульовий."
    )


# ============================================================
# ІНФОРМАЦІЯ ПРО ВАГУ
# ============================================================

st.caption(
    "⚖️ Розрахункова вага змінюється "
    "приблизно на 1 кг за кожні 7700 ккал "
    "накопиченого дефіциту."
)
