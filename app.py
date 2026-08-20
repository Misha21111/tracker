import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


# =========================================================
# НАЛАШТУВАННЯ
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
    "👤 Оберіть профіль:",
    ["Я", "Дружина"]
)

profile_prefix = "user1" if user_profile == "Я" else "user2"


EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"


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
                rgba(0,0,0,0.72),
                rgba(0,0,0,0.88)
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
        padding-bottom: 3rem;
    }}

    .glass {{
        background: rgba(15, 17, 22, 0.78);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 22px;
        padding: 20px;
        margin: 12px 0;
        box-shadow: 0 10px 35px rgba(0,0,0,0.35);
        backdrop-filter: blur(10px);
    }}

    .food-card {{
        background: rgba(18,20,26,0.86);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 18px;
        padding: 18px;
        margin: 12px 0;
    }}

    .food-title {{
        font-size: 18px;
        font-weight: 700;
        line-height: 1.4;
    }}

    .food-kcal {{
        font-size: 20px;
        font-weight: 800;
        color: #36A2EB;
        white-space: nowrap;
    }}

    .food-time {{
        color: #aaa;
        font-size: 14px;
    }}

    .deficit-box {{
        border-radius: 18px;
        padding: 16px;
        margin: 18px 0;
        text-align: center;
        font-size: 20px;
        font-weight: 800;
    }}

    .info-line {{
        font-size: 15px;
        color: #ddd;
        margin: 4px 0;
    }}

    .small-muted {{
        color: #999;
        font-size: 13px;
    }}

    .donut-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 25px 0;
    }}

    .donut-ring {{
        width: 230px;
        height: 230px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow:
            0 0 25px rgba(0,0,0,0.65),
            inset 0 0 10px rgba(255,255,255,0.08);
    }}

    .donut-hole {{
        width: 158px;
        height: 158px;
        background:
            radial-gradient(
                circle,
                #17191f 0%,
                #111318 100%
            );
        border-radius: 50%;

        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;

        text-align: center;
        color: white;

        box-shadow:
            inset 0 0 18px rgba(0,0,0,0.65);
    }}

    .status-deficit {{
        color: #48e28a;
        font-size: 18px;
        font-weight: 800;
    }}

    .status-surplus {{
        color: #ff6384;
        font-size: 18px;
        font-weight: 800;
    }}

    .status-neutral {{
        color: #f5f5f5;
        font-size: 18px;
        font-weight: 800;
    }}

    .kcal-main {{
        font-size: 23px;
        font-weight: 900;
        margin-top: 5px;
    }}

    .log-card {{
        background: rgba(16,18,23,0.82);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 18px;
        padding: 16px;
        margin: 10px 0;
    }}

    .log-header {{
        display: flex;
        justify-content: space-between;
        gap: 10px;
        align-items: flex-start;
    }}

    .log-description {{
        font-size: 17px;
        font-weight: 700;
        line-height: 1.45;
    }}

    .log-kcal {{
        font-size: 18px;
        font-weight: 800;
        color: #36A2EB;
        white-space: nowrap;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "edit_mode": False,
    "editor_row": None,
    "history": [],
    "last_saved_state": None,
    "show_settings": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# API GEMINI
# =========================================================

api_key = (
    st.secrets.get("GEMINI_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
)

if not api_key:
    st.error(
        "⚠️ Не знайдено GEMINI_API_KEY. "
        "Додай ключ у Secrets."
    )
    st.stop()

client = genai.Client(api_key=api_key)


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

def default_settings():
    return {
        "calories": 2000,
        "bmr_daily": 1850,
        "initial_weight": 89.0
    }


def load_settings():
    default = default_settings()

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            return {**default, **data}

        except Exception:
            pass

    return default


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
    "Спалено"
]


def empty_dataframe():
    return pd.DataFrame(columns=COLUMNS)


def load_data():

    if not os.path.exists(EXCEL_FILE):
        return empty_dataframe()

    try:
        df = pd.read_excel(EXCEL_FILE)

        for column in COLUMNS:
            if column not in df.columns:
                df[column] = 0 if column in [
                    "Спожито",
                    "Спалено"
                ] else ""

        df = df[COLUMNS]

        df["Спожито"] = pd.to_numeric(
            df["Спожито"],
            errors="coerce"
        ).fillna(0)

        df["Спалено"] = pd.to_numeric(
            df["Спалено"],
            errors="coerce"
        ).fillna(0)

        return df

    except Exception:
        return empty_dataframe()


def save_data(df):
    df.to_excel(
        EXCEL_FILE,
        index=False
    )


df_data = load_data()


# =========================================================
# ІСТОРІЯ ДЛЯ ВІДМІНИ
# =========================================================

def push_history(df):
    snapshot = df.copy(deep=True)

    st.session_state["history"].append(snapshot)

    # максимум 10 станів
    if len(st.session_state["history"]) > 10:
        st.session_state["history"] = (
            st.session_state["history"][-10:]
        )


def undo_last():

    history = st.session_state["history"]

    if not history:
        st.warning("Немає змін для відміни.")
        return None

    previous = history.pop()

    save_data(previous)

    return previous


# =========================================================
# ВАГА
# =========================================================

def calculate_current_weight(df, settings):

    initial_weight = float(
        settings.get("initial_weight", 89.0)
    )

    bmr_daily = float(
        settings.get("bmr_daily", 1850)
    )

    if df.empty:
        return initial_weight

    work = df.copy()

    work["Дата"] = work["Дата"].astype(str)

    work["Спожито"] = pd.to_numeric(
        work["Спожито"],
        errors="coerce"
    ).fillna(0)

    work["Спалено"] = pd.to_numeric(
        work["Спалено"],
        errors="coerce"
    ).fillna(0)

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    now = datetime.now(LOCAL_TZ)

    total_balance = 0.0

    for date_value in work["Дата"].unique():

        day = work[
            work["Дата"] == date_value
        ]

        eaten = float(
            day["Спожито"].sum()
        )

        watch_burned = float(
            day["Спалено"].sum()
        )

        if date_value == today:
            base_burn = (
                bmr_daily / 24
            ) * (
                now.hour +
                now.minute / 60
            )
        else:
            base_burn = bmr_daily

        total_balance += (
            base_burn +
            watch_burned -
            eaten
        )

    # 7700 ккал ≈ 1 кг
    new_weight = (
        initial_weight -
        total_balance / 7700
    )

    return max(0.0, new_weight)


# =========================================================
# АНАЛІЗ ЇЖІ
# =========================================================

def analyze_text(text):

    prompt = f"""
Ти аналізуєш запис харчування або тренування.

Текст:
{text}

Поверни ТІЛЬКИ JSON такого формату:

{{
  "type": "food",
  "description": "короткий опис",
  "total_kcal": 0,
  "burned_kcal": 0,
  "items": [
    {{
      "name": "продукт",
      "kcal": 0
    }}
  ]
}}

Правила:

1. Якщо це їжа:
   type = "food"
   total_kcal = загальна кількість калорій
   burned_kcal = 0

2. Якщо це тренування:
   type = "training"
   total_kcal = 0
   burned_kcal = кількість спалених калорій

3. Для їжі ОБОВ'ЯЗКОВО розбий продукти.
   Біля кожного продукту в items вкажи його калорії.

4. Якщо точну кількість калорій визначити
   неможливо — зроби адекватну оцінку.

5. Не додавай ніякого тексту поза JSON.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)


# =========================================================
# ЗАГОЛОВОК
# =========================================================

st.title(
    f"⚖️ Фітнес — {user_profile}"
)

current_weight = calculate_current_weight(
    df_data,
    user_settings
)

st.markdown(
    f"""
    <div class="glass">
        <div style="font-size:22px;font-weight:800;">
            ⚖️ Поточна вага:
            ~{current_weight:.1f} кг
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ДОДАВАННЯ ЗАПИСУ
# =========================================================

st.subheader("➕ Додати запис")

user_input = st.text_input(
    "🍽️ Що з'їв / тренування",
    placeholder=(
        "Наприклад: плов з куркою, "
        "2 яйця та чорний хліб"
    )
)

col1, col2 = st.columns(2)

with col1:
    submit_food = st.button(
        "➕ Додати",
        type="primary",
        use_container_width=True
    )

with col2:
    undo_button = st.button(
        "↩️ Відмінити",
        use_container_width=True
    )


# =========================================================
# ВІДМІНА
# =========================================================

if undo_button:

    restored = undo_last()

    if restored is not None:
        df_data = restored

        st.success(
            "Останню зміну відмінено."
        )

        st.rerun()


# =========================================================
# ЗБЕРЕЖЕННЯ НОВОГО ЗАПИСУ
# =========================================================

if submit_food and user_input.strip():

    try:

        push_history(df_data)

        data = analyze_text(
            user_input.strip()
        )

        now = datetime.now(LOCAL_TZ)

        entry_type = (
            "Тренування"
            if data.get("type") == "training"
            else "Їжа"
        )

        description = (
            data.get("description")
            or user_input.strip()
        )

        # Для їжі показуємо продукти
        # з калоріями
        if entry_type == "Їжа":

            items = data.get(
                "items",
                []
            )

            if items:

                parts = []

                for item in items:

                    name = str(
                        item.get(
                            "name",
                            "Продукт"
                        )
                    )

                    kcal = float(
                        item.get(
                            "kcal",
                            0
                        ) or 0
                    )

                    parts.append(
                        f"{name} — {kcal:.0f} ккал"
                    )

                description = (
                    "<br>".join(parts)
                )

            consumed = float(
                data.get(
                    "total_kcal",
                    0
                ) or 0
            )

            burned = 0.0

        else:

            consumed = 0.0

            burned = float(
                data.get(
                    "burned_kcal",
                    0
                ) or 0
            )

        new_row = pd.DataFrame(
            [{
                "Дата": now.strftime(
                    "%Y-%m-%d"
                ),
                "Час": now.strftime(
                    "%H:%M"
                ),
                "Опис": description,
                "Тип": entry_type,
                "Спожито": consumed,
                "Спалено": burned
            }]
        )

        df_data = pd.concat(
            [
                df_data,
                new_row
            ],
            ignore_index=True
        )

        save_data(df_data)

        st.success(
            "✅ Запис додано."
        )

        st.rerun()

    except Exception as e:

        # якщо аналіз не вдався —
        # прибираємо останній history snapshot
        if st.session_state["history"]:
            st.session_state[
                "history"
            ].pop()

        st.error(
            f"❌ Помилка: {e}"
        )


# =========================================================
# ВИБІР ДНЯ
# =========================================================

st.divider()

today_str = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")

available_dates = [today_str]

if not df_data.empty:

    dates = sorted(
        df_data["Дата"]
        .astype(str)
        .unique(),
        reverse=True
    )

    for date_value in dates:

        if date_value not in available_dates:
            available_dates.append(
                date_value
            )


selected_date = st.selectbox(
    "📅 День",
    available_dates
)


# =========================================================
# КНОПКИ КЕРУВАННЯ
# =========================================================

c1, c2 = st.columns(2)

with c1:

    settings_button = st.button(
        "⚙️ Налаштування",
        use_container_width=True
    )

with c2:

    delete_button = st.button(
        "🗑️ Видалити останній",
        use_container_width=True
    )


if settings_button:

    st.session_state[
        "show_settings"
    ] = not st.session_state[
        "show_settings"
    ]

    st.rerun()


# =========================================================
# ВИДАЛЕННЯ ОСТАННЬОГО
# =========================================================

if delete_button and not df_data.empty:

    push_history(df_data)

    df_data = df_data.iloc[:-1].copy()

    save_data(df_data)

    st.success(
        "🗑️ Останній запис видалено."
    )

    st.rerun()


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

if st.session_state["show_settings"]:

    st.markdown(
        '<div class="glass">',
        unsafe_allow_html=True
    )

    st.subheader(
        "⚙️ Налаштування"
    )

    new_calories = st.number_input(
        "Добова потреба, ккал",
        min_value=0,
        value=int(
            user_settings.get(
                "calories",
                2000
            )
        ),
        step=50
    )

    new_bmr = st.number_input(
        "Базове спалювання за добу, ккал",
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
        "💾 Зберегти",
        type="primary",
        use_container_width=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    if save_settings_button:

        user_settings = {
            "calories": new_calories,
            "bmr_daily": new_bmr,
            "initial_weight": new_weight
        }

        save_settings(
            user_settings
        )

        st.session_state[
            "show_settings"
        ] = False

        st.success(
            "Налаштування збережено."
        )

        st.rerun()


# =========================================================
# СТАТИСТИКА ДНЯ
# =========================================================

if not df_data.empty:

    day_df = df_data[
        df_data["Дата"].astype(str)
        == selected_date
    ].copy()

else:

    day_df = empty_dataframe()


# ---------------------------------------------------------
# Навіть якщо записів немає — показуємо статистику
# ---------------------------------------------------------

consumed = float(
    day_df["Спожито"].sum()
) if not day_df.empty else 0.0

watch_burned = float(
    day_df["Спалено"].sum()
) if not day_df.empty else 0.0


bmr_daily = float(
    user_settings.get(
        "bmr_daily",
        1850
    )
)


now = datetime.now(LOCAL_TZ)


if selected_date == today_str:

    base_burned = (
        bmr_daily / 24
    ) * (
        now.hour +
        now.minute / 60
    )

else:

    base_burned = bmr_daily


total_burned = (
    base_burned +
    watch_burned
)


# ---------------------------------------------------------
# ДЕФІЦИТ / ПРОФІЦИТ
# ---------------------------------------------------------

balance = (
    total_burned -
    consumed
)


calorie_target = float(
    user_settings.get(
        "calories",
        2000
    )
)


# =========================================================
# ВАГА
# =========================================================

calculated_weight = calculate_current_weight(
    df_data,
    user_settings
)

st.markdown(
    f"""
    <div class="glass">

        <div style="
            font-size:21px;
            font-weight:800;
            margin-bottom:8px;
        ">
            📅 {selected_date}
        </div>

        <div class="info-line">
            ⚖️ Поточна вага:
            <b>{calculated_weight:.1f} кг</b>
        </div>

        <div class="info-line">
            🎯 Добова потреба:
            <b>{calorie_target:.0f} ккал</b>
        </div>

        <div class="info-line">
            🍽️ З'їдено:
            <b>{consumed:.0f} ккал</b>
        </div>

        <div class="info-line">
            🔥 З годинника:
            <b>{watch_burned:.0f} ккал</b>
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# КРУЖОК
# =========================================================

# Прогрес по з'їдених калоріях
progress = (
    consumed / calorie_target
    if calorie_target > 0
    else 0
)

progress = max(
    0,
    min(progress, 1)
)

progress_deg = (
    progress * 360
)


if balance > 0:

    status_text = (
        f"Дефіцит: {abs(balance):.0f} ккал"
    )

    status_class = (
        "status-deficit"
    )

    ring_color = "#36A2EB"

elif balance < 0:

    status_text = (
        f"Профіцит: {abs(balance):.0f} ккал"
    )

    status_class = (
        "status-surplus"
    )

    ring_color = "#FF6384"

else:

    status_text = "Баланс: 0 ккал"

    status_class = (
        "status-neutral"
    )

    ring_color = "#36A2EB"


st.markdown(
    f"""
    <div class="donut-container">

        <div
            class="donut-ring"
            style="
                background:
                conic-gradient(
                    {ring_color}
                    0deg
                    {progress_deg:.1f}deg,

                    rgba(255,255,255,0.10)
                    {progress_deg:.1f}deg
                    360deg
                );
            "
        >

            <div class="donut-hole">

                <div class="{status_class}">
                    {status_text}
                </div>

                <div class="kcal-main">
                    {consumed:.0f}
                    /
                    {calorie_target:.0f}
                </div>

                <div
                    style="
                        color:#999;
                        font-size:12px;
                        margin-top:3px;
                    "
                >
                    ккал з'їдено
                </div>

            </div>

        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ІНФОРМАЦІЯ ПРО БАЛАНС
# =========================================================

if balance > 0:

    st.markdown(
        f"""
        <div
            class="deficit-box"
            style="
                background:rgba(20,120,70,0.30);
                color:#48e28a;
                border:1px solid
                    rgba(72,226,138,0.25);
            "
        >
            📉 Дефіцит:
            {balance:.0f} ккал
        </div>
        """,
        unsafe_allow_html=True
    )

elif balance < 0:

    st.markdown(
        f"""
        <div
            class="deficit-box"
            style="
                background:rgba(150,30,60,0.30);
                color:#ff6384;
                border:1px solid
                    rgba(255,99,132,0.25);
            "
        >
            📈 Профіцит:
            {abs(balance):.0f} ккал
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# РЕДАКТОР ЗАПИСІВ
# =========================================================

st.divider()

st.subheader("📝 Лог")


if day_df.empty:

    st.info(
        "За цей день записів немає."
    )

else:

    # Показуємо від останнього до першого
    for index in reversed(
        list(day_df.index)
    ):

        row = day_df.loc[index]

        description = str(
            row["Опис"]
        )

        entry_type = str(
            row["Тип"]
        )

        eaten = float(
            row["Спожито"] or 0
        )

        burned = float(
            row["Спалено"] or 0
        )

        time_value = str(
            row["Час"]
        )[:5]

        if entry_type == "Тренування":

            icon = "💪"
            kcal_text = (
                f"-{burned:.0f} ккал"
            )

        else:

            icon = "🍽️"
            kcal_text = (
                f"+{eaten:.0f} ккал"
            )

        st.markdown(
            f"""
            <div class="log-card">

                <div class="log-header">

                    <div>

                        <div class="food-time">
                            {time_value}
                        </div>

                        <div class="log-description">
                            {icon}
                            {description}
                        </div>

                    </div>

                    <div class="log-kcal">
                        {kcal_text}
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        # -------------------------------------------------
        # КНОПКА РЕДАГУВАННЯ
        # -------------------------------------------------

        if st.button(
            "✏️ Редагувати",
            key=f"edit_{index}",
            use_container_width=True
        ):

            st.session_state[
                "editor_row"
            ] = int(index)

            st.rerun()


        # -------------------------------------------------
        # РЕДАКТОР
        # -------------------------------------------------

        if (
            st.session_state[
                "editor_row"
            ] == int(index)
        ):

            st.markdown(
                '<div class="glass">',
                unsafe_allow_html=True
            )

            st.markdown(
                "### ✏️ Редагування запису"
            )

            edit_description = st.text_area(
                "Опис",
                value=description,
                key=f"description_{index}"
            )

            edit_type = st.selectbox(
                "Тип",
                ["Їжа", "Тренування"],
                index=(
                    1
                    if entry_type == "Тренування"
                    else 0
                ),
                key=f"type_{index}"
            )

            if edit_type == "Їжа":

                edit_consumed = st.number_input(
                    "🍽️ Калорії",
                    min_value=0.0,
                    value=eaten,
                    step=1.0,
                    key=f"eaten_{index}"
                )

                edit_burned = 0.0

            else:

                edit_consumed = 0.0

                edit_burned = st.number_input(
                    "🔥 Калорії з годинника",
                    min_value=0.0,
                    value=burned,
                    step=1.0,
                    key=f"burned_{index}"
                )

            st.caption(
                "Зміна калорій замінює старе "
                "значення, а не додає його."
            )

            ec1, ec2 = st.columns(2)

            with ec1:

                save_edit = st.button(
                    "💾 Зберегти",
                    type="primary",
                    use_container_width=True,
                    key=f"save_{index}"
                )

            with ec2:

                cancel_edit = st.button(
                    "❌ Скасувати",
                    use_container_width=True,
                    key=f"cancel_{index}"
                )

            if cancel_edit:

                st.session_state[
                    "editor_row"
                ] = None

                st.rerun()

            if save_edit:

                push_history(df_data)

                real_index = int(index)

                df_data.loc[
                    real_index,
                    "Опис"
                ] = edit_description

                df_data.loc[
                    real_index,
                    "Тип"
                ] = edit_type

                df_data.loc[
                    real_index,
                    "Спожито"
                ] = float(
                    edit_consumed
                )

                df_data.loc[
                    real_index,
                    "Спалено"
                ] = float(
                    edit_burned
                )

                save_data(df_data)

                st.session_state[
                    "editor_row"
                ] = None

                st.success(
                    "✅ Запис оновлено. "
                    "Вся статистика перерахована."
                )

                st.rerun()

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )


# =========================================================
# ПІДСУМОК
# =========================================================

st.divider()

st.markdown(
    f"""
    <div class="glass">

        <div style="
            font-size:18px;
            font-weight:800;
            margin-bottom:10px;
        ">
            📊 Підсумок за {selected_date}
        </div>

        <div class="info-line">
            🍽️ З'їдено:
            <b>{consumed:.0f} ккал</b>
        </div>

        <div class="info-line">
            🎯 Добова потреба:
            <b>{calorie_target:.0f} ккал</b>
        </div>

        <div class="info-line">
            🔥 Калорії з годинника:
            <b>{watch_burned:.0f} ккал</b>
        </div>

        <div class="info-line">
            ⚖️ Поточна вага:
            <b>{calculated_weight:.1f} кг</b>
        </div>

    </div>
    """,
    unsafe_allow_html=True
)
