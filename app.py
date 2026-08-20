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
# ЧАС
# ============================================================

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Kyiv")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


# ============================================================
# ПРОФІЛЬ
# ============================================================

profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"]
)

profile_id = "user1" if profile == "Я" else "user2"


# ============================================================
# ФАЙЛИ
# ============================================================

EXCEL_FILE = f"fitness_entries_{profile_id}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_id}.json"
UNDO_FILE = f"fitness_undo_{profile_id}.json"


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

    color: white !important;

    font-weight: 700 !important;

    box-shadow:
        0 7px 20px
        rgba(0,0,0,0.35);
}}

div.stButton > button:hover {{
    transform: translateY(-2px);

    border-color:
        rgba(54,162,235,0.65) !important;
}}

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

div[data-testid="stExpander"] {{
    border-radius: 14px !important;
}}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# GEMINI
# ============================================================

api_key = None

try:
    api_key = st.secrets.get("GEMINI_API_KEY")
except Exception:
    pass

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ Не знайдено GEMINI_API_KEY.")
    st.stop()

client = genai.Client(api_key=api_key)


# ============================================================
# НАЛАШТУВАННЯ ПРОФІЛЮ
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

    if not os.path.exists(SETTINGS_FILE):
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
# КОЛОНКИ EXCEL
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
    return pd.DataFrame(columns=COLUMNS)


# ============================================================
# БЕЗПЕЧНІ ФУНКЦІЇ
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
# ЗАВАНТАЖЕННЯ ЛОГУ
# ============================================================

def load_data():

    if not os.path.exists(EXCEL_FILE):
        return empty_dataframe()

    try:
        data = pd.read_excel(EXCEL_FILE)
    except Exception:
        return empty_dataframe()

    for column in COLUMNS:

        if column not in data.columns:

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

    data = data[COLUMNS].copy()

    for column in [
        "Спожито",
        "Спалено",
        "Білки",
        "Жири",
        "Вуглеводи"
    ]:

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

def load_undo_history():

    if not os.path.exists(UNDO_FILE):
        return []

    try:

        with open(
            UNDO_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:
        return []


def save_undo_history(history):

    history = history[-10:]

    with open(
        UNDO_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2
        )


def add_undo_snapshot(dataframe):

    history = load_undo_history()

    history.append(
        dataframe.to_dict(
            orient="records"
        )
    )

    history = history[-10:]

    save_undo_history(history)


def history_to_dataframe(records):

    if not records:
        return empty_dataframe()

    result = pd.DataFrame(records)

    for column in COLUMNS:

        if column not in result.columns:
            result[column] = ""

    result = result[COLUMNS].copy()

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

    history = load_undo_history()

    if not history:
        return None

    previous = history.pop()

    save_undo_history(history)

    return history_to_dataframe(previous)


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

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    now = datetime.now(
        LOCAL_TZ
    )

    total_balance = 0.0

    for date_value in dataframe["Дата"].unique():

        date_value = clean_text(date_value)

        day = dataframe[
            dataframe["Дата"]
            .apply(clean_text)
            == date_value
        ]

        eaten = (
            day["Спожито"]
            .apply(clean_number)
            .sum()
        )

        exercise = (
            day["Спалено"]
            .apply(clean_number)
            .sum()
        )

        if date_value == today:

            hours_passed = (
                now.hour
                +
                now.minute / 60
            )

            base_burn = (
                bmr_daily / 24
            ) * hours_passed

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

        total_balance += (
            burned - eaten
        )

    weight_change = (
        total_balance / 7700
    )

    return max(
        0.0,
        initial_weight - weight_change
    )


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    f"🏋️ Мій Фітнес — {profile}"
)


# ============================================================
# ДОДАВАННЯ В ЛОГ
# ============================================================

st.subheader("📝 Додати в лог")

user_input = st.text_input(
    "Що з'їв або яке тренування було?",
    placeholder=(
        "Наприклад: "
        "200 г курки, рис і салат"
        " або "
        "тренування 45 хв"
    ),
    label_visibility="collapsed"
)


if st.button(
    "➕ Додати в лог",
    type="primary",
    use_container_width=True
):

    if not user_input.strip():

        st.warning(
            "Напиши запис у поле."
        )

    else:

        try:

            prompt = """
Ти фітнес-трекер.

Проаналізуй запис користувача.

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

Правила:

1. Якщо користувач описує їжу:
type = "Їжа"

consumed_kcal =
орієнтовні спожиті калорії.

burned_kcal = 0.

protein =
орієнтовні білки в грамах.

fat =
орієнтовні жири в грамах.

carbs =
орієнтовні вуглеводи в грамах.

2. Якщо користувач описує тренування:
type = "Тренування"

consumed_kcal = 0.

burned_kcal =
орієнтовні спалені калорії.

protein = 0.
fat = 0.
carbs = 0.

3. Якщо кількість не вказана,
зроби розумну оцінку.

4. Усі числові значення повинні
бути числами.

5. Не використовуй markdown.

6. Поверни тільки JSON.
"""

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    prompt,
                    "\nЗапис користувача:\n",
                    user_input
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            raw = (
                response.text or ""
            ).strip()

            if raw.startswith("```"):

                raw = (
                    raw
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            result = json.loads(raw)

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

            # Зберігаємо стан ДО зміни
            add_undo_snapshot(df)

            now = datetime.now(
                LOCAL_TZ
            )

            new_row = {
                "Дата": now.strftime(
                    "%Y-%m-%d"
                ),
                "Час": now.strftime(
                    "%H:%M"
                ),
                "Опис": description,
                "Тип": entry_type,
                "Спожито": consumed_kcal,
                "Спалено": burned_kcal,
                "Білки": protein,
                "Жири": fat,
                "Вуглеводи": carbs
            }

            df = pd.concat(
                [
                    df,
                    pd.DataFrame([new_row])
                ],
                ignore_index=True
            )

            df.to_excel(
                EXCEL_FILE,
                index=False
            )

            st.success(
                "✅ Запис додано!"
            )

            st.rerun()

        except json.JSONDecodeError:

            st.error(
                "❌ Gemini повернув "
                "неправильний формат даних."
            )

        except Exception as error:

            st.error(
                f"❌ Помилка: {error}"
            )


# ============================================================
# ВІДМІНИТИ
# ============================================================

history = load_undo_history()

undo_col1, undo_col2 = st.columns(
    [3, 1]
)

with undo_col1:

    st.caption(
        f"↩️ Історія змін: "
        f"{len(history)} / 10"
    )

with undo_col2:

    if st.button(
        "↩️ Відмінити",
        use_container_width=True,
        disabled=len(history) == 0
    ):

        restored = undo_last()

        if restored is not None:

            df = restored

            df.to_excel(
                EXCEL_FILE,
                index=False
            )

            st.success(
                "↩️ Останню зміну скасовано."
            )

            st.rerun()


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

with st.expander("⚙️ Налаштування"):

    calories_target = st.number_input(
        "🎯 Добова калорійність",
        min_value=0,
        value=int(settings["calories"]),
        step=50
    )

    protein_target = st.number_input(
        "🥩 Добова потреба білків, г",
        min_value=0,
        value=int(settings["protein"]),
        step=5
    )

    fat_target = st.number_input(
        "🥑 Добова потреба жирів, г",
        min_value=0,
        value=int(settings["fat"]),
        step=5
    )

    carbs_target = st.number_input(
        "🍞 Добова потреба вуглеводів, г",
        min_value=0,
        value=int(settings["carbs"]),
        step=5
    )

    bmr_target = st.number_input(
        "🔥 Базова витрата за добу, ккал",
        min_value=0,
        value=int(settings["bmr_daily"]),
        step=50
    )

    initial_weight = st.number_input(
        "⚖️ Початкова вага, кг",
        min_value=0.0,
        value=float(settings["initial_weight"]),
        step=0.1
    )

    include_exercise = st.checkbox(
        "💪 Враховувати тренування "
        "у дефіциті",
        value=settings.get(
            "include_exercise_in_deficit",
            True
        )
    )

    if st.button(
        "💾 Зберегти налаштування",
        use_container_width=True
    ):

        settings = {
            "calories": calories_target,
            "protein": protein_target,
            "fat": fat_target,
            "carbs": carbs_target,
            "bmr_daily": bmr_target,
            "initial_weight": initial_weight,
            "include_exercise_in_deficit":
                include_exercise
        }

        save_settings(settings)

        st.success(
            "✅ Налаштування збережено."
        )

        st.rerun()


# ============================================================
# ДАТА
# ============================================================

today = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")

dates = [today]

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

        dates.append(date_value)


selected_date = st.selectbox(
    "📅 День",
    dates
)


# ============================================================
# ДАНІ ЗА ДЕНЬ
# ============================================================

day_df = df[
    df["Дата"]
    .apply(clean_text)
    ==
    selected_date
].copy()


if day_df.empty:

    consumed = 0.0
    burned_exercise = 0.0
    protein = 0.0
    fat = 0.0
    carbs = 0.0

else:

    consumed = (
        day_df["Спожито"]
        .apply(clean_number)
        .sum()
    )

    burned_exercise = (
        day_df["Спалено"]
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
# БАЗОВЕ СПАЛЮВАННЯ
# ============================================================

bmr_daily = clean_number(
    settings["bmr_daily"]
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

    base_burn = (
        bmr_daily / 24
    ) * hours_passed

else:

    base_burn = bmr_daily


if settings.get(
    "include_exercise_in_deficit",
    True
):

    total_burned = (
        base_burn
        +
        burned_exercise
    )

else:

    total_burned = base_burn


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
    status_value = f"−{balance:.0f} ккал"

elif balance < 0:

    status = "ПРОФІЦИТ"
    status_icon = "📈"
    status_color = "#FF6262"
    status_value = f"+{abs(balance):.0f} ккал"

else:

    status = "БАЛАНС"
    status_icon = "⚖️"
    status_color = "#FFD166"
    status_value = "0 ккал"


# ============================================================
# ВАГА
# ============================================================

current_weight = calculate_current_weight(
    df,
    settings
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

    align-items: center;
    justify-content: center;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;
}}

.wrapper {{
    width: 270px;
    height: 300px;

    display: flex;

    align-items: center;
    justify-content: center;
}}

.donut {{
    width: 220px;
    height: 220px;

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

    align-items: center;
    justify-content: center;

    box-shadow:
        0 0 35px
        rgba(0,0,0,0.70);
}}

.hole {{
    width: 158px;
    height: 158px;

    border-radius: 50%;

    background: #15171c;

    display: flex;

    flex-direction: column;

    align-items: center;
    justify-content: center;

    text-align: center;
}}

.status {{
    color: {status_color};

    font-size: 13px;
    font-weight: 900;
}}

.balance {{
    color: {status_color};

    font-size: 23px;
    font-weight: 900;

    margin-top: 3px;
}}

.info {{
    color: #c5c5c5;

    font-size: 10px;

    margin-top: 4px;
}}

.weight {{
    color: white;

    font-size: 11px;
    font-weight: 800;

    margin-top: 4px;
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

<div class="info">
🍽️ {consumed:.0f} ккал
</div>

<div class="info">
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
    height=310,
    scrolling=False
)


# ============================================================
# БМЖ
# ============================================================

st.subheader(
    "🥗 БМЖ — добова потреба / з'їдено"
)


b1, b2, b3 = st.columns(3)


with b1:

    st.metric(
        "🥩 Білки",
        f"{protein:.0f} / "
        f"{clean_number(settings['protein']):.0f} г"
    )


with b2:

    st.metric(
        "🥑 Жири",
        f"{fat:.0f} / "
        f"{clean_number(settings['fat']):.0f} г"
    )


with b3:

    st.metric(
        "🍞 Вуглеводи",
        f"{carbs:.0f} / "
        f"{clean_number(settings['carbs']):.0f} г"
    )


# ============================================================
# СТАТИСТИКА
# ============================================================

st.subheader("📊 Статистика")


s1, s2, s3 = st.columns(3)


with s1:

    st.metric(
        "🍽️ З'їдено",
        f"{consumed:.0f} ккал"
    )


with s2:

    st.metric(
        "🔥 Спалено",
        f"{total_burned:.0f} ккал"
    )


with s3:

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


# ============================================================
# ПРОГРЕС КАЛОРІЙ
# ============================================================

target = clean_number(
    settings["calories"]
)

if target > 0:

    progress = min(
        max(
            consumed / target,
            0
        ),
        1
    )

else:

    progress = 0


st.progress(progress)

st.caption(
    f"🍽️ {consumed:.0f} / "
    f"{target:.0f} ккал"
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

        if row_type == "Тренування":

            icon = "💪"

            kcal = clean_number(
                row["Спалено"]
            )

            kcal_text = (
                f"-{kcal:.0f} ккал"
            )

        else:

            icon = "🍽️"

            kcal = clean_number(
                row["Спожито"]
            )

            kcal_text = (
                f"+{kcal:.0f} ккал"
            )


        # ====================================================
        # ЗАПИС
        # ====================================================

        with st.container(
            border=True
        ):

            left, right = st.columns(
                [4, 1]
            )

            with left:

                st.write(
                    f"**{time_value}** "
                    f"{icon} "
                    f"**{description}**"
                )

            with right:

                st.write(
                    f"**{kcal_text}**"
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
                    key=f"description_{index}"
                )

                edit_type = st.selectbox(
                    "Тип",
                    [
                        "Їжа",
                        "Тренування"
                    ],
                    index=(
                        1
                        if row_type == "Тренування"
                        else 0
                    ),
                    key=f"type_{index}"
                )


                e1, e2 = st.columns(2)


                with e1:

                    edit_consumed = st.number_input(
                        "🍽️ Спожито, ккал",
                        min_value=0.0,
                        value=clean_number(
                            row["Спожито"]
                        ),
                        step=1.0,
                        key=f"consumed_{index}"
                    )


                with e2:

                    edit_burned = st.number_input(
                        "🔥 Спалено, ккал",
                        min_value=0.0,
                        value=clean_number(
                            row["Спалено"]
                        ),
                        step=1.0,
                        key=f"burned_{index}"
                    )


                e3, e4, e5 = st.columns(3)


                with e3:

                    edit_protein = st.number_input(
                        "Білки, г",
                        min_value=0.0,
                        value=clean_number(
                            row["Білки"]
                        ),
                        step=1.0,
                        key=f"protein_{index}"
                    )


                with e4:

                    edit_fat = st.number_input(
                        "Жири, г",
                        min_value=0.0,
                        value=clean_number(
                            row["Жири"]
                        ),
                        step=1.0,
                        key=f"fat_{index}"
                    )


                with e5:

                    edit_carbs = st.number_input(
                        "Вуглеводи, г",
                        min_value=0.0,
                        value=clean_number(
                            row["Вуглеводи"]
                        ),
                        step=1.0,
                        key=f"carbs_{index}"
                    )


                save_col, delete_col = (
                    st.columns(2)
                )


                # =================================================
                # ЗБЕРЕГТИ
                # =================================================

                with save_col:

                    if st.button(
                        "💾 Зберегти",
                        key=f"save_{index}",
                        use_container_width=True
                    ):

                        add_undo_snapshot(df)

                        df.at[
                            index,
                            "Опис"
                        ] = edit_description

                        df.at[
                            index,
                            "Тип"
                        ] = edit_type


                        if edit_type == "Їжа":

                            df.at[
                                index,
                                "Спожито"
                            ] = edit_consumed

                            df.at[
                                index,
                                "Спалено"
                            ] = 0

                        else:

                            df.at[
                                index,
                                "Спожито"
                            ] = 0

                            df.at[
                                index,
                                "Спалено"
                            ] = edit_burned


                        df.at[
                            index,
                            "Білки"
                        ] = edit_protein

                        df.at[
                            index,
                            "Жири"
                        ] = edit_fat

                        df.at[
                            index,
                            "Вуглеводи"
                        ] = edit_carbs


                        df.to_excel(
                            EXCEL_FILE,
                            index=False
                        )

                        st.success(
                            "✅ Запис змінено."
                        )

                        st.rerun()


                # =================================================
                # ВИДАЛИТИ
                # =================================================

                with delete_col:

                    if st.button(
                        "🗑️ Видалити",
                        key=f"delete_{index}",
                        use_container_width=True
                    ):

                        add_undo_snapshot(df)

                        df = df.drop(
                            index
                        ).reset_index(
                            drop=True
                        )

                        df.to_excel(
                            EXCEL_FILE,
                            index=False
                        )

                        st.success(
                            "🗑️ Запис видалено."
                        )

                        st.rerun()


# ============================================================
# ФІНАЛЬНИЙ СТАН
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
        "⚖️ Баланс калорій приблизно нульовий."
    )


st.caption(
    "⚖️ Розрахунок ваги: приблизно "
    "7700 ккал накопиченого дефіциту "
    "≈ 1 кг зміни ваги."
)
