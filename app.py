import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Мій фітнес",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


# =========================================================
# PROFILE / FILES
# =========================================================
user_profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"],
)

profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
WATCH_FILE = f"watch_activity_{profile_prefix}.json"
UNDO_FILE = f"fitness_undo_{profile_prefix}.json"

IMAGE_URL = "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"


# =========================================================
# CSS
# =========================================================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image:
            linear-gradient(
                rgba(0,0,0,.74),
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

    div[data-testid="stButton"] > button,
    div[data-testid="stFormSubmitButton"] > button {{
        min-height: 48px;
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,.16);
        background: rgba(25,27,35,.95);
        color: #fff;
        font-weight: 800;
        transition:
            transform .08s ease,
            background .1s ease,
            box-shadow .1s ease;
    }}

    div[data-testid="stButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {{
        background: rgba(48,51,64,.98);
        border-color: rgba(255,255,255,.35);
    }}

    div[data-testid="stButton"] > button:active,
    div[data-testid="stFormSubmitButton"] > button:active {{
        transform: scale(.96);
        background: rgba(70,73,88,1);
        box-shadow: inset 0 3px 9px rgba(0,0,0,.45);
    }}

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{
        border-radius: 14px !important;
        background: rgba(28,30,40,.96) !important;
        color: #fff !important;
    }}

    div[data-testid="stSelectbox"] > div > div {{
        border-radius: 14px !important;
        background: rgba(28,30,40,.96) !important;
    }}

    .panel {{
        background: rgba(12,14,20,.80);
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 20px;
        padding: 18px;
        margin: 12px 0;
        backdrop-filter: blur(6px);
    }}

    .donut-wrap {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 12px auto;
    }}

    .donut {{
        width: 230px;
        height: 230px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 30px rgba(0,0,0,.58);
    }}

    .donut-hole {{
        width: 158px;
        height: 158px;
        border-radius: 50%;
        background: rgba(13,15,20,.98);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        border: 1px solid rgba(255,255,255,.08);
    }}

    .balance {{
        font-size: 16px;
        font-weight: 900;
        margin-bottom: 5px;
    }}

    .deficit {{
        color: #4ade80;
    }}

    .surplus {{
        color: #ff6b6b;
    }}

    .kcal-main {{
        font-size: 25px;
        line-height: 1;
        font-weight: 900;
    }}

    .kcal-sub {{
        color: #a9acb5;
        font-size: 11px;
        margin-top: 5px;
    }}

    .stats-row {{
        display: flex;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 12px;
    }}

    .stat {{
        background: rgba(20,22,29,.92);
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 12px;
        padding: 8px 12px;
        font-size: 12px;
    }}

    .log-card {{
        background: rgba(12,14,20,.82);
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 18px;
        padding: 15px;
        margin: 10px 0;
    }}

    .log-head {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
    }}

    .log-title {{
        font-weight: 800;
        line-height: 1.4;
        word-break: break-word;
    }}

    .log-time {{
        color: #aaa;
        font-weight: 700;
        white-space: nowrap;
    }}

    .log-kcal {{
        color: #5eead4;
        font-weight: 900;
        white-space: nowrap;
        font-size: 17px;
    }}

    .product-line {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255,255,255,.08);
    }}

    .product-line:last-child {{
        border-bottom: 0;
    }}

    .product-name {{
        color: #fff;
    }}

    .product-kcal {{
        color: #5eead4;
        font-weight: 900;
        white-space: nowrap;
    }}

    .muted {{
        color: #a7aab3;
        font-size: 12px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DEFAULT SETTINGS
# =========================================================
def default_settings():
    return {
        "calories": 2000,
        "bmr_daily": 1850,
        "initial_weight": 89.0,
    }


def load_settings():
    defaults = default_settings()

    if not os.path.exists(SETTINGS_FILE):
        return defaults

    try:
        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            saved = json.load(f)

        result = defaults.copy()
        result.update(saved)

        return result

    except Exception:
        return defaults


def save_settings(settings):
    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            settings,
            f,
            ensure_ascii=False,
            indent=2,
        )


# =========================================================
# DATA
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
    "Продукти",
]


def empty_df():
    return pd.DataFrame(
        columns=COLUMNS
    )


def load_data():

    if not os.path.exists(EXCEL_FILE):
        return empty_df()

    try:

        df = pd.read_excel(
            EXCEL_FILE
        )

        for col in COLUMNS:

            if col not in df.columns:

                if col in [
                    "Спожито",
                    "Спалено",
                    "Білки",
                    "Жири",
                    "Вуглеводи",
                ]:
                    df[col] = 0

                else:
                    df[col] = ""

        return df[COLUMNS].copy()

    except Exception:
        return empty_df()


def save_data(df):
    df.to_excel(
        EXCEL_FILE,
        index=False,
    )


# =========================================================
# WATCH CALORIES
# =========================================================
def load_watch():

    if not os.path.exists(
        WATCH_FILE
    ):
        return {}

    try:

        with open(
            WATCH_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        return {
            str(k): float(v)
            for k, v in data.items()
        }

    except Exception:
        return {}


def save_watch(data):

    with open(
        WATCH_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# =========================================================
# UNDO — 10 ОСТАННІХ ДІЙ
# =========================================================
def load_undo():

    if not os.path.exists(
        UNDO_FILE
    ):
        return []

    try:

        with open(
            UNDO_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def save_undo(stack):

    # максимум 10 дій
    stack = stack[-10:]

    with open(
        UNDO_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            stack,
            f,
            ensure_ascii=False,
            indent=2,
        )


def push_undo(
    df_before,
    watch_before,
):

    stack = load_undo()

    stack.append(
        {
            "df":
                df_before.to_dict(
                    orient="records"
                ),

            "watch":
                watch_before,
        }
    )

    save_undo(stack)


def undo_last(
    df_current,
    watch_current,
):

    stack = load_undo()

    if not stack:
        return (
            df_current,
            watch_current,
            False,
        )

    previous = stack.pop()

    previous_df = pd.DataFrame(
        previous["df"]
    )

    for col in COLUMNS:

        if col not in previous_df.columns:

            if col in [
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи",
            ]:
                previous_df[col] = 0
            else:
                previous_df[col] = ""

    previous_df = previous_df[
        COLUMNS
    ]

    save_undo(stack)

    return (
        previous_df,
        previous.get(
            "watch",
            {},
        ),
        True,
    )


# =========================================================
# HELPERS
# =========================================================
def num_series(
    df,
    column,
):

    if column not in df.columns:

        return pd.Series(
            [0] * len(df),
            index=df.index,
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    ).fillna(0)


def day_totals(
    df,
    date_str,
):

    if df.empty:

        return (
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )

    day = df[
        df["Дата"].astype(str)
        ==
        str(date_str)
    ]

    return (
        float(
            num_series(
                day,
                "Спожито",
            ).sum()
        ),

        float(
            num_series(
                day,
                "Спалено",
            ).sum()
        ),

        float(
            num_series(
                day,
                "Білки",
            ).sum()
        ),

        float(
            num_series(
                day,
                "Жири",
            ).sum()
        ),

        float(
            num_series(
                day,
                "Вуглеводи",
            ).sum()
        ),
    )


def safe_json(text):

    text = (
        text or ""
    ).strip()

    if text.startswith(
        "```"
    ):

        text = text.replace(
            "```json",
            "",
            1,
        )

        text = text.replace(
            "```",
            "",
            1,
        )

    return json.loads(
        text.strip()
    )


def clean_products(
    products,
):

    result = []

    if not isinstance(
        products,
        list,
    ):
        return result

    for item in products:

        if not isinstance(
            item,
            dict,
        ):
            continue

        name = str(
            item.get(
                "name",
                "",
            )
        ).strip()

        try:
            kcal = float(
                item.get(
                    "kcal",
                    0,
                )
                or 0
            )
        except Exception:
            kcal = 0.0

        if name:

            result.append(
                {
                    "name":
                        name,

                    "kcal":
                        max(
                            kcal,
                            0,
                        ),
                }
            )

    return result


# =========================================================
# WEIGHT
# =========================================================
def calculate_weight(
    df,
    settings,
    watch,
):

    initial = float(
        settings.get(
            "initial_weight",
            89.0,
        )
    )

    bmr_daily = float(
        settings.get(
            "bmr_daily",
            1850,
        )
    )

    if (
        df.empty
        and not watch
    ):
        return initial

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

    today = datetime.now(
        LOCAL_TZ
    ).strftime(
        "%Y-%m-%d"
    )

    now = datetime.now(
        LOCAL_TZ
    )

    cumulative_balance = 0.0

    for date_str in dates:

        consumed, _, _, _, _ = (
            day_totals(
                df,
                date_str,
            )
        )

        watch_burned = float(
            watch.get(
                date_str,
                0,
            )
        )

        if date_str == today:

            hours = (
                now.hour
                +
                now.minute / 60.0
            )

            bmr = (
                bmr_daily
                *
                hours
                /
                24.0
            )

        else:

            bmr = bmr_daily

        cumulative_balance += (
            bmr
            +
            watch_burned
            -
            consumed
        )

    return (
        initial
        -
        cumulative_balance / 7700.0
    )


# =========================================================
# GEMINI 3.6 FLASH
# =========================================================
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
        "⚠️ Не знайдено GEMINI_API_KEY. "
        "Додай ключ у Secrets."
    )

    st.stop()


client = genai.Client(
    api_key=api_key
)


# =========================================================
# LOAD
# =========================================================
settings = load_settings()

df_data = load_data()

watch_activity = load_watch()


if "edit_row" not in st.session_state:

    st.session_state.edit_row = None


# =========================================================
# HEADER
# =========================================================
current_weight = calculate_weight(
    df_data,
    settings,
    watch_activity,
)

st.title(
    "⚖️ Мій фітнес"
)

st.markdown(
    f"""
    ### Поточна вага:
    **~{current_weight:.1f} кг**
    """
)


# =========================================================
# INPUT FOOD
# =========================================================
st.markdown(
    "### 🍽️ Що сьогодні з'їв?"
)

with st.form(
    "food_form",
    clear_on_submit=True,
):

    food_input = st.text_input(
        "Продукти",
        placeholder=(
            "Наприклад: "
            "плов з куркою 350 г, "
            "2 яйця, чорний хліб 60 г"
        ),
    )

    add_food = st.form_submit_button(
        "✅ Додати в лог",
        use_container_width=True,
    )


# =========================================================
# ADD FOOD
# =========================================================
if add_food:

    if not food_input.strip():

        st.warning(
            "Введи продукти."
        )

    else:

        now = datetime.now(
            LOCAL_TZ
        )

        prompt = f"""
Ти точний харчовий калькулятор.

Користувач ввів:

{food_input}

Поверни ТІЛЬКИ валідний JSON:

{{
  "description": "короткий опис усіх продуктів",
  "total_kcal": 0,
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

- Це їжа, не тренування.
- total_kcal — сума калорій усіх продуктів.
- items — КОЖЕН продукт окремим рядком.
- kcal кожного item — калорії саме цього продукту.
- Сума kcal items повинна дорівнювати total_kcal.
- protein, fat, carbs — загальні значення за весь запис.
- Якщо вагу продукту не вказано, зроби розумну оцінку порції.
- Не додавай markdown.
- Не додавай пояснення.
"""

        try:

            response = (
                client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
            )

            result = safe_json(
                response.text
            )

            products = clean_products(
                result.get(
                    "items",
                    [],
                )
            )

            total_kcal = float(
                result.get(
                    "total_kcal",
                    0,
                )
                or 0
            )

            if products:

                item_sum = sum(
                    x["kcal"]
                    for x in products
                )

                if item_sum > 0:

                    total_kcal = item_sum

            description = str(
                result.get(
                    "description",
                    food_input.strip(),
                )
            ).strip()

            # зберігаємо стан ДО зміни
            df_before = df_data.copy()

            watch_before = dict(
                watch_activity
            )

            push_undo(
                df_before,
                watch_before,
            )

            products_json = json.dumps(
                products,
                ensure_ascii=False,
            )

            new_row = pd.DataFrame(
                [
                    {
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
                            "Їжа",

                        "Спожито":
                            total_kcal,

                        "Спалено":
                            0.0,

                        "Білки":
                            float(
                                result.get(
                                    "protein",
                                    0,
                                )
                                or 0
                            ),

                        "Жири":
                            float(
                                result.get(
                                    "fat",
                                    0,
                                )
                                or 0
                            ),

                        "Вуглеводи":
                            float(
                                result.get(
                                    "carbs",
                                    0,
                                )
                                or 0
                            ),

                        "Продукти":
                            products_json,
                    }
                ]
            )

            df_data = pd.concat(
                [
                    df_data,
                    new_row,
                ],
                ignore_index=True,
            )

            save_data(
                df_data
            )

            st.success(
                "✅ Додано в лог."
            )

            # clear_on_submit=True
            # очистить поле після submit
            st.rerun()

        except Exception as e:

            st.error(
                f"❌ Помилка Gemini: {e}"
            )


# =========================================================
# WATCH
# =========================================================
today_str = datetime.now(
    LOCAL_TZ
).strftime(
    "%Y-%m-%d"
)

current_watch = float(
    watch_activity.get(
        today_str,
        0,
    )
)

st.markdown(
    "### ⌚ Калорії з годинника"
)

with st.form(
    "watch_form"
):

    watch_value = st.number_input(
        "Спалено сьогодні, ккал",
        min_value=0.0,
        value=current_watch,
        step=10.0,
    )

    update_watch = (
        st.form_submit_button(
            "⌚ Оновити",
            use_container_width=True,
        )
    )


if update_watch:

    df_before = df_data.copy()

    watch_before = dict(
        watch_activity
    )

    push_undo(
        df_before,
        watch_before,
    )

    # ВАЖЛИВО:
    # ЗАМІНА старого значення.
    # Тут НЕ +=.
    watch_activity[
        today_str
    ] = float(
        watch_value
    )

    save_watch(
        watch_activity
    )

    st.success(
        f"⌚ Встановлено "
        f"{watch_value:.0f} ккал."
    )

    st.rerun()


# =========================================================
# DATE
# =========================================================
dates = [
    today_str
]

if not df_data.empty:

    for value in sorted(
        df_data["Дата"]
        .astype(str)
        .unique(),
        reverse=True,
    ):

        if value not in dates:

            dates.append(value)


selected_date = st.selectbox(
    "📅 День",
    dates,
)


# =========================================================
# DAILY TOTALS
# =========================================================
(
    consumed,
    logged_burned,
    protein,
    fat,
    carbs,
) = day_totals(
    df_data,
    selected_date,
)


watch_burned = float(
    watch_activity.get(
        str(selected_date),
        0,
    )
)


bmr_daily = float(
    settings.get(
        "bmr_daily",
        1850,
    )
)


if selected_date == today_str:

    now = datetime.now(
        LOCAL_TZ
    )

    hours_passed = (
        now.hour
        +
        now.minute / 60.0
    )

    bmr_used = (
        bmr_daily
        *
        hours_passed
        /
        24.0
    )

else:

    bmr_used = bmr_daily


# =========================================================
# BALANCE
# =========================================================
total_burned = (
    bmr_used
    +
    watch_burned
)

balance = (
    total_burned
    -
    consumed
)


if balance >= 0:

    balance_text = (
        f"Дефіцит: "
        f"{balance:.0f} ккал"
    )

    balance_class = "deficit"

else:

    balance_text = (
        f"Профіцит: "
        f"{abs(balance):.0f} ккал"
    )

    balance_class = "surplus"


# =========================================================
# DONUT
# =========================================================
target = max(
    float(
        settings.get(
            "calories",
            2000,
        )
    ),
    1.0,
)


progress = min(
    max(
        consumed / target,
        0.0,
    ),
    1.0,
)


angle = (
    progress
    *
    360.0
)


if progress <= 0:

    ring = (
        "conic-gradient("
        "#30333d 0deg 360deg)"
    )

elif progress < 1:

    ring = (
        "conic-gradient("
        f"#36A2EB 0deg "
        f"{angle:.2f}deg, "
        f"#30333d "
        f"{angle:.2f}deg "
        f"360deg)"
    )

else:

    ring = (
        "conic-gradient("
        "#FF6384 0deg 360deg)"
    )


# =========================================================
# DONUT HTML
# =========================================================
st.markdown(
    f"""
    <div class="panel">

        <div class="donut-wrap">

            <div
                class="donut"
                style="background:{ring};"
            >

                <div class="donut-hole">

                    <div
                        class="balance
                        {balance_class}"
                    >
                        {balance_text}
                    </div>

                    <div class="kcal-main">
                        {consumed:.0f}
                    </div>

                    <div class="kcal-sub">
                        з'їдено з
                        {target:.0f}
                        ккал
                    </div>

                </div>

            </div>

            <div class="stats-row">

                <div class="stat">
                    🔥 Годинник:
                    <b>
                        {watch_burned:.0f}
                    </b>
                    ккал
                </div>

                <div class="stat">
                    🫀 Добова витрата:
                    <b>
                        {bmr_daily:.0f}
                    </b>
                    ккал
                </div>

                <div class="stat">
                    🍽️ З'їдено:
                    <b>
                        {consumed:.0f}
                    </b>
                    ккал
                </div>

            </div>

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# UNDO
# =========================================================
undo_stack = load_undo()

if undo_stack:

    if st.button(
        "↩️ Відмінити останню дію",
        use_container_width=True,
    ):

        (
            df_data,
            watch_activity,
            ok,
        ) = undo_last(
            df_data,
            watch_activity,
        )

        if ok:

            save_data(
                df_data
            )

            save_watch(
                watch_activity
            )

            st.success(
                "↩️ Останню дію скасовано."
            )

            st.rerun()


# =========================================================
# LOG
# =========================================================
st.markdown(
    "### 📝 Лог"
)

day_df = df_data[
    df_data["Дата"].astype(str)
    ==
    str(selected_date)
].copy()


if day_df.empty:

    st.info(
        "За цей день записів ще немає."
    )

else:

    for idx, row in day_df.iterrows():

        typ = str(
            row.get(
                "Тип",
                "Їжа",
            )
        )

        description = str(
            row.get(
                "Опис",
                "Запис",
            )
        )

        time_text = str(
            row.get(
                "Час",
                "",
            )
        )[:5]

        if typ == "Тренування":

            kcal = float(
                row.get(
                    "Спалено",
                    0,
                )
                or 0
            )

            icon = "💪"

        else:

            kcal = float(
                row.get(
                    "Спожито",
                    0,
                )
                or 0
            )

            icon = "🍽️"


        # -------------------------------------------------
        # КАРТКА
        # -------------------------------------------------
        st.markdown(
            f"""
            <div class="log-card">

                <div class="log-head">

                    <div class="log-title">

                        <span class="log-time">
                            {time_text}
                        </span>

                        &nbsp;

                        {icon}

                        {description}

                    </div>

                    <div class="log-kcal">
                        {kcal:.0f} ккал
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


        # -------------------------------------------------
        # КАЛОРІЇ КОЖНОГО ПРОДУКТУ
        # -------------------------------------------------
        products_raw = row.get(
            "Продукти",
            "",
        )

        if products_raw:

            try:

                products = json.loads(
                    products_raw
                )

                if (
                    isinstance(
                        products,
                        list,
                    )
                    and products
                ):

                    for product in products:

                        pname = str(
                            product.get(
                                "name",
                                "",
                            )
                        )

                        pkcal = float(
                            product.get(
                                "kcal",
                                0,
                            )
                            or 0
                        )

                        st.markdown(
                            f"""
                            <div
                                class="product-line"
                            >

                                <span
                                    class="product-name"
                                >
                                    {pname}
                                </span>

                                <span
                                    class="product-kcal"
                                >
                                    {pkcal:.0f}
                                    ккал
                                </span>

                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            except Exception:
                pass


        # -------------------------------------------------
        # EDIT
        # -------------------------------------------------
        if st.button(
            "✏️ Редагувати",
            key=f"edit_{idx}",
            use_container_width=True,
        ):

            st.session_state.edit_row = int(
                idx
            )

            st.rerun()


        # -------------------------------------------------
        # EDITOR
        # -------------------------------------------------
        if (
            st.session_state.edit_row
            ==
            int(idx)
        ):

            with st.form(
                f"edit_form_{idx}"
            ):

                edit_description = (
                    st.text_input(
                        "Опис",
                        value=description,
                    )
                )

                edit_kcal = (
                    st.number_input(
                        "Калорії",
                        min_value=0.0,
                        value=kcal,
                        step=1.0,
                    )
                )

                edit_type = (
                    st.selectbox(
                        "Тип",
                        [
                            "Їжа",
                            "Тренування",
                        ],
                        index=(
                            1
                            if typ
                            == "Тренування"
                            else 0
                        ),
                    )
                )

                save_edit = (
                    st.form_submit_button(
                        "💾 Зберегти",
                        use_container_width=True,
                    )
                )


            if save_edit:

                df_before = (
                    df_data.copy()
                )

                watch_before = dict(
                    watch_activity
                )

                push_undo(
                    df_before,
                    watch_before,
                )

                real_idx = int(
                    idx
                )

                df_data.loc[
                    real_idx,
                    "Опис"
                ] = edit_description

                df_data.loc[
                    real_idx,
                    "Тип"
                ] = edit_type


                if edit_type == "Їжа":

                    df_data.loc[
                        real_idx,
                        "Спожито"
                    ] = float(
                        edit_kcal
                    )

                    df_data.loc[
                        real_idx,
                        "Спалено"
                    ] = 0.0

                else:

                    df_data.loc[
                        real_idx,
                        "Спожито"
                    ] = 0.0

                    df_data.loc[
                        real_idx,
                        "Спалено"
                    ] = float(
                        edit_kcal
                    )


                save_data(
                    df_data
                )

                st.session_state.edit_row = (
                    None
                )

                st.rerun()


# =========================================================
# SETTINGS
# =========================================================
with st.expander(
    "⚙️ Редактор налаштувань"
):

    with st.form(
        "settings_form"
    ):

        new_target = (
            st.number_input(
                "🎯 Добова ціль калорій",
                min_value=0.0,
                value=float(
                    settings.get(
                        "calories",
                        2000,
                    )
                ),
                step=50.0,
            )
        )

        new_bmr = (
            st.number_input(
                "🫀 Добова базова витрата, ккал",
                min_value=0.0,
                value=float(
                    settings.get(
                        "bmr_daily",
                        1850,
                    )
                ),
                step=50.0,
            )
        )

        new_weight = (
            st.number_input(
                "⚖️ Початкова вага, кг",
                min_value=0.0,
                value=float(
                    settings.get(
                        "initial_weight",
                        89.0,
                    )
                ),
                step=0.1,
            )
        )

        save_settings_button = (
            st.form_submit_button(
                "💾 Зберегти налаштування",
                use_container_width=True,
            )
        )


    if save_settings_button:

        settings["calories"] = float(
            new_target
        )

        settings["bmr_daily"] = float(
            new_bmr
        )

        settings["initial_weight"] = float(
            new_weight
        )

        save_settings(
            settings
        )

        st.success(
            "⚙️ Налаштування збережено."
        )

        st.rerun()


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    """
    <div
        class="muted"
        style="
            text-align:center;
            margin-top:25px;
        "
    >
        ⚖️ 7700 ккал
        накопиченого дефіциту
        ≈ 1 кг
    </div>
    """,
    unsafe_allow_html=True,
)
