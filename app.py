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

profile_id = (
    "user1"
    if profile == "Я"
    else "user2"
)


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

    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()

    try:

        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

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
    ) as f:

        json.dump(
            settings,
            f,
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
# БЕЗПЕЧНІ ЗНАЧЕННЯ
# ============================================================

def clean_number(value):

    try:

        value = float(value)

        if pd.isna(value):
            return 0.0

        return value

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

    value = str(value)

    if value.lower() == "nan":
        return ""

    return value


# ============================================================
# ЗАВАНТАЖЕННЯ ЛОГУ
# ============================================================

def load_data():

    if not os.path.exists(EXCEL_FILE):
        return empty_dataframe()

    try:

        df = pd.read_excel(EXCEL_FILE)

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


df = load_data()


# ============================================================
# UNDO — ІСТОРІЯ ДО 10 ЗМІН
# ============================================================

def load_undo_history():

    if not os.path.exists(UNDO_FILE):
        return []

    try:

        with open(
            UNDO_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return []


def save_undo_history(history):

    history = history[-10:]

    with open(
        UNDO_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


def dataframe_to_history(df):

    records = df.to_dict(
        orient="records"
    )

    return records


def history_to_dataframe(records):

    if not records:
        return empty_dataframe()

    result = pd.DataFrame(records)

    for column in COLUMNS:

        if column not in result.columns:

            result[column] = 0

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

    for column in [
        "Дата",
        "Час",
        "Опис",
        "Тип"
    ]:

        result[column] = (
            result[column]
            .apply(clean_text)
        )

    return result


def add_undo_snapshot(df):

    history = load_undo_history()

    history.append(
        dataframe_to_history(df)
    )

    history = history[-10:]

    save_undo_history(history)


def undo_last():

    history = load_undo_history()

    if not history:
        return None

    previous_state = history.pop()

    save_undo_history(history)

    return history_to_dataframe(
        previous_state
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

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    now = datetime.now(
        LOCAL_TZ
    )

    total_deficit = 0.0

    for date_value in (
        dataframe["Дата"]
        .unique()
    ):

        date_value = clean_text(
            date_value
        )

        day = dataframe[
            dataframe["Дата"]
            .apply(clean_text)
            == date_value
        ]

        eaten = float(
            day["Спожито"]
            .apply(clean_number)
            .sum()
        )

        exercise = float(
            day["Спалено"]
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
            burned - eaten
        )

    weight_change = (
        total_deficit / 7700
    )

    return max(
        0.0,
        initial_weight - weight_change
    )


current_weight = calculate_current_weight(
    df,
    settings
)


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    f"🏋️ Мій Фітнес — {profile}"
)

st.markdown(
    f"### ⚖️ Поточна вага: ~{current_weight:.1f} кг"
)


# ============================================================
# ДОДАТИ В ЛОГ
# ============================================================

st.subheader("📝 Додати в лог")

user_input = st.text_input(
    "Запис",
    placeholder=(
        "Напиши: "
        "«курка, рис і салат» "
        "або "
        "«тренування 45 хв»"
    ),
    label_visibility="collapsed"
)


photo = st.camera_input(
    "📷 Фото їжі / тренування"
)


if st.button(
    "➕ Додати в лог",
    type="primary",
    use_container_width=True
):

    if not user_input and not photo:

        st.warning(
            "Введи щось у лог або додай фото."
        )

    else:

        try:

            prompt = """
Ти фітнес-трекер.

Проаналізуй запис користувача.

Потрібно повернути ТІЛЬКИ JSON:

{
    "description": "опис",
    "type": "Їжа",
    "consumed_kcal": 0,
    "burned_kcal": 0,
    "protein": 0,
    "fat": 0,
    "carbs": 0
}

Якщо це їжа:
type = "Їжа"
consumed_kcal = калорії їжі
burned_kcal = 0

Якщо це тренування:
type = "Тренування"
consumed_kcal = 0
burned_kcal = спалені калорії

Білки, жири та вуглеводи визначай
для їжі.

Усі числа повинні бути числами.

Не використовуй markdown.

Поверни тільки JSON.
"""

            if photo:

                image_bytes = photo.getvalue()

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

            else:

                response = (
                    client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=(
                            prompt
                            +
                            "\n\nЗапис:\n"
                            +
                            user_input
                        ),
                        config=types.GenerateContentConfig(
                            response_mime_type=(
                                "application/json"
                            )
                        )
                    )
                )

            raw = (
                response.text or ""
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

            result = json.loads(raw)

            description = clean_text(
                result.get(
                    "description",
                    user_input or "Запис"
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

            if entry_type == "Тренування":

                consumed_kcal = 0

            else:

                burned_kcal = 0

            # перед зміною створюємо Undo
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

            st.success(
                "✅ Запис додано!"
            )

            st.rerun()

        except Exception as error:

            st.error(
                f"❌ Помилка: {error}"
            )


# ============================================================
# КНОПКА ВІДМІНИТИ
# ============================================================

history = load_undo_history()

undo_col1, undo_col2 = st.columns(
    [3, 1]
)

with undo_col1:

    st.caption(
        f"↩️ Доступно скасувань: "
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

with st.expander(
    "⚙️ Налаштування"
):

    calories_target = st.number_input(
        "🎯 Добова калорійність",
        min_value=0,
        value=int(
            settings["calories"]
        ),
        step=50
    )

    protein_target = st.number_input(
        "🥩 Добова потреба білків, г",
        min_value=0,
        value=int(
            settings["protein"]
        ),
        step=5
    )

    fat_target = st.number_input(
        "🥑 Добова потреба жирів, г",
        min_value=0,
        value=int(
            settings["fat"]
        ),
        step=5
    )

    carbs_target = st.number_input(
        "🍞 Добова потреба вуглеводів, г",
        min_value=0,
        value=int(
            settings["carbs"]
        ),
        step=5
    )

    bmr_target = st.number_input(
        "🔥 Добова базова витрата, ккал",
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

        save_settings(
            settings
        )

        st.success(
            "✅ Збережено."
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
# ДАНІ ДНЯ
# ============================================================

day_df = df[
    df["Дата"]
    .apply(clean_text)
    ==
    selected_date
].copy()


consumed = float(
    day_df["Спожито"]
    .apply(clean_number)
    .sum()
) if not day_df.empty else 0


burned_exercise = float(
    day_df["Спалено"]
    .apply(clean_number)
    .sum()
) if not day_df.empty else 0


protein = float(
    day_df["Білки"]
    .apply(clean_number)
    .sum()
) if not day_df.empty else 0


fat = float(
    day_df["Жири"]
    .apply(clean_number)
    .sum()
) if not day_df.empty else 0


carbs = float(
    day_df["Вуглеводи"]
    .apply(clean_number)
    .sum()
) if not day_df.empty else 0


# ============================================================
# БАЗОВА ВИТРАТА
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
        burned_exercise
    )

else:

    total_burned = bmr_elapsed


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
# ПОТОЧНА ВАГА
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
        / total_macros
        * 360
    )

    fat_degrees = (
        protein_degrees
        +
        fat
        / total_macros
        * 360
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

    font-size: 22px;
    font-weight: 900;

    margin-top: 3px;
}}

.small {{
    color: #bbbbbb;

    font-size: 10px;

    margin-top: 5px;
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
    height=300,
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
# ЗАГАЛЬНА СТАТИСТИКА
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
# ПРОГРЕС
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
        # РЯДОК ЛОГУ
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
                            "🗑️ Запис видалено. "
                            "Його можна повернути "
                            "кнопкою «Відмінити»."
                        )

                        st.rerun()


# ============================================================
# НИЖНІЙ ПІДСУМОК
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
    "⚖️ Розрахункова вага змінюється "
    "приблизно на 1 кг за 7700 ккал "
    "накопиченого дефіциту."
)
