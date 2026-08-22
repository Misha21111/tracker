import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import gspread
from google.oauth2.service_account import Credentials

from google import genai
from google.genai import types


# ============================================================
# STREAMLIT
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

    LOCAL_TZ = ZoneInfo(
        "Europe/Warsaw"
    )

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
# GOOGLE SHEETS
# ============================================================

GOOGLE_SHEET_NAME = st.secrets.get(
    "GOOGLE_SHEET_NAME",
    "Мій Фітнес"
)


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


@st.cache_resource
def get_google_client():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    if "gcp_service_account" in st.secrets:

        service_account_info = dict(
            st.secrets[
                "gcp_service_account"
            ]
        )

        credentials = (
            Credentials.from_service_account_info(
                service_account_info,
                scopes=scopes
            )
        )

    else:

        credentials = (
            Credentials.from_service_account_file(
                "service_account.json",
                scopes=scopes
            )
        )

    return gspread.authorize(
        credentials
    )


@st.cache_resource
def get_google_spreadsheet():

    client = get_google_client()

    return client.open(
        GOOGLE_SHEET_NAME
    )


def get_google_worksheet():

    spreadsheet = (
        get_google_spreadsheet()
    )

    try:

        worksheet = (
            spreadsheet.worksheet(
                profile_id
            )
        )

    except gspread.WorksheetNotFound:

        worksheet = (
            spreadsheet.add_worksheet(
                title=profile_id,
                rows=2000,
                cols=len(COLUMNS)
            )
        )

        worksheet.append_row(
            COLUMNS,
            value_input_option="USER_ENTERED"
        )

    return worksheet


def ensure_google_headers(
    worksheet
):

    first_row = worksheet.row_values(
        1
    )

    if first_row != COLUMNS:

        worksheet.clear()

        worksheet.append_row(
            COLUMNS,
            value_input_option="USER_ENTERED"
        )


def google_sheet_to_dataframe():

    worksheet = (
        get_google_worksheet()
    )

    ensure_google_headers(
        worksheet
    )

    records = worksheet.get_all_records()

    if not records:

        return pd.DataFrame(
            columns=COLUMNS
        )

    df = pd.DataFrame(
        records
    )

    for column in COLUMNS:

        if column not in df.columns:

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

    return df


def append_google_row(
    row
):

    worksheet = (
        get_google_worksheet()
    )

    values = [
        row.get(
            "Дата",
            ""
        ),

        row.get(
            "Час",
            ""
        ),

        row.get(
            "Опис",
            ""
        ),

        row.get(
            "Тип",
            "Їжа"
        ),

        clean_number(
            row.get(
                "Спожито",
                0
            )
        ),

        clean_number(
            row.get(
                "Спалено",
                0
            )
        ),

        clean_number(
            row.get(
                "Білки",
                0
            )
        ),

        clean_number(
            row.get(
                "Жири",
                0
            )
        ),

        clean_number(
            row.get(
                "Вуглеводи",
                0
            )
        )
    ]

    worksheet.append_row(
        values,
        value_input_option="USER_ENTERED"
    )


def delete_last_google_row():

    worksheet = (
        get_google_worksheet()
    )

    all_values = (
        worksheet.get_all_values()
    )

    if len(all_values) <= 1:

        return False

    worksheet.delete_rows(
        len(all_values)
    )

    return True


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

SETTINGS_FILE = (
    f"user_settings_{profile_id}.json"
)


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

            data = json.load(
                file
            )

        result = (
            DEFAULT_SETTINGS.copy()
        )

        result.update(
            data
        )

        return result

    except Exception:

        return DEFAULT_SETTINGS.copy()


def save_settings(
    settings
):

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
# CSS
# ============================================================

BACKGROUND_IMAGE = (
    "https://i.postimg.cc/"
    "kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)


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

    min-height:
        46px !important;

    border-radius:
        14px !important;

    border:
        1px solid
        rgba(255,255,255,0.12)
        !important;

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
        all 0.15s ease;

}}


div.stButton > button:hover {{

    transform:
        translateY(-2px);

    border-color:
        rgba(54,162,235,0.65)
        !important;

    box-shadow:
        0 10px 28px
        rgba(0,0,0,0.45);

}}


div.stButton > button:active {{

    transform:
        translateY(2px)
        scale(0.985)
        !important;

    box-shadow:
        inset 0 3px 8px
        rgba(0,0,0,0.55)
        !important;

    filter:
        brightness(0.85);

}}


/* =========================================================
   INPUT
   ========================================================= */

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{

    border-radius:
        12px !important;

    background:
        rgba(18,18,22,0.94)
        !important;

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
   LOG
   ========================================================= */

div[data-testid="stVerticalBlockBorderWrapper"] {{

    background:
        rgba(20,20,24,0.82);

    border-radius:
        14px;

}}


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
        "Додай GEMINI_API_KEY "
        "у Streamlit Secrets."
    )

    st.stop()


client = genai.Client(
    api_key=api_key
)


# ============================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# ============================================================

def clean_number(
    value
):

    try:

        number = float(
            value
        )

        if pd.isna(
            number
        ):

            return 0.0

        return number

    except Exception:

        return 0.0


def clean_text(
    value
):

    if value is None:

        return ""


    try:

        if pd.isna(
            value
        ):

            return ""

    except Exception:

        pass


    text = str(
        value
    ).strip()


    if text.lower() == "nan":

        return ""


    return text


def empty_dataframe():

    return pd.DataFrame(
        columns=COLUMNS
    )


# ============================================================
# ЗАВАНТАЖЕННЯ ДАНИХ
# ============================================================

try:

    df = google_sheet_to_dataframe()

except Exception as error:

    st.error(
        "❌ Не вдалося підключитися "
        "до Google Sheets."
    )

    st.code(
        str(error)
    )

    st.info(
        "Перевір назву таблиці, "
        "service account і доступ "
        "Editor для service account."
    )

    st.stop()


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
    ).strftime(
        "%Y-%m-%d"
    )


    now = datetime.now(
        LOCAL_TZ
    )


    total_deficit = 0.0


    for date_value in (
        work["Дата"].unique()
    ):

        day = work[
            work["Дата"]
            ==
            date_value
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


        total_deficit += (
            burned
            -
            eaten
        )


    weight_change = (
        total_deficit
        /
        7700
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
    f"""
### ⚖️ Поточна вага:
~{current_weight:.1f} кг
"""
)


# ============================================================
# ВВЕДЕННЯ
# ============================================================

user_input = st.text_input(
    "📥 Що з'їв / тренування",
    placeholder=(
        "Наприклад: куряча грудка 200 г "
        "або тренування 45 хв"
    ),
    key="food_input"
)


# ============================================================
# ДОДАТИ ЗАПИС
# ============================================================

if st.button(
    "✅ Додати запис",
    type="primary",
    use_container_width=True
):

    if not user_input.strip():

        st.warning(
            "Введи продукт або тренування."
        )

    else:

        try:

            prompt = """

Ти аналізуєш запис для фітнес-трекера.

Потрібно визначити:

1. їжа це чи тренування;
2. приблизні калорії;
3. білки;
4. жири;
5. вуглеводи;
6. якщо це тренування —
   спалені калорії.

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

Якщо даних немає — став 0.

Не додавай markdown.

Поверни тільки JSON.
"""


            text_prompt = (
                prompt
                +
                "\n\nЗапис користувача:\n"
                +
                user_input.strip()
            )


            response = (
                client.models.generate_content(

                    model="gemini-2.5-flash",

                    contents=text_prompt,

                    config=(
                        types.GenerateContentConfig(
                            response_mime_type=(
                                "application/json"
                            )
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


            description = clean_text(
                result.get(
                    "description",
                    user_input
                )
            )


            if not description:

                description = (
                    user_input.strip()
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


            # ==================================================
            # ЗАПИС У GOOGLE SHEETS
            # ==================================================

            append_google_row(
                new_row
            )


            st.success(
                "✅ Запис успішно додано в Google Sheets!"
            )


            # Очищення поля
            st.session_state[
                "food_input"
            ] = ""


            # Оновити дані
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
                "❌ Помилка запису:"
            )

            st.code(
                str(error)
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


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

if settings_button:

    st.session_state[
        "settings_open"
    ] = (
        not st.session_state[
            "settings_open"
        ]
    )

    st.rerun()


# ============================================================
# ВИДАЛЕННЯ ОСТАННЬОГО
# ============================================================

if delete_button:

    if df.empty:

        st.warning(
            "Лог порожній."
        )

    else:

        try:

            success = (
                delete_last_google_row()
            )


            if success:

                st.success(
                    "🗑️ Останній запис "
                    "видалено з Google Sheets."
                )

                st.rerun()

            else:

                st.info(
                    "Немає записів для видалення."
                )


        except Exception as error:

            st.error(
                "❌ Не вдалося видалити запис "
                "з Google Sheets."
            )

            st.code(
                str(error)
            )


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


    protein_target = st.number_input(
        "🥩 Білки, г",
        min_value=0,
        value=int(
            settings["protein"]
        ),
        step=5
    )


    fat_target = st.number_input(
        "🥑 Жири, г",
        min_value=0,
        value=int(
            settings["fat"]
        ),
        step=5
    )


    carbs_target = st.number_input(
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
                protein_target,

            "fat":
                fat_target,

            "carbs":
                carbs_target,

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
# СТАТИСТИКА
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

    status_value = (
        "0 ккал"
    )


# ============================================================
# ВАГА
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

    background:
        transparent;

    overflow:
        hidden;

}}


body {{

    display:
        flex;

    justify-content:
        center;

    align-items:
        center;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

}}


.wrapper {{

    width:
        260px;

    height:
        285px;

    display:
        flex;

    flex-direction:
        column;

    align-items:
        center;

    justify-content:
        center;

}}


.donut {{

    width:
        210px;

    height:
        210px;

    border-radius:
        50%;

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

    display:
        flex;

    justify-content:
        center;

    align-items:
        center;

    box-shadow:
        0 0 30px
        rgba(0,0,0,0.65);

}}


.hole {{

    width:
        150px;

    height:
        150px;

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
    color:
        #36A2EB;
}}


.fat {{
    color:
        #FFCE56;
}}


.carbs {{
    color:
        #FF6384;
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


components.html(
    donut_html,
    height=300,
    scrolling=False
)


# ============================================================
# СТАТИСТИКА
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
# ПРОГРЕС
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

    reversed_day = (
        day_df.iloc[::-1]
    )


    for _, row in (
        reversed_day.iterrows()
    ):

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
        "⚖️ Сьогодні баланс "
        "калорій приблизно нульовий."
    )


# ============================================================
# ІНФОРМАЦІЯ
# ============================================================

st.caption(
    "⚖️ Розрахункова вага змінюється "
    "приблизно на 1 кг за кожні 7700 ккал "
    "накопиченого дефіциту."
        )
