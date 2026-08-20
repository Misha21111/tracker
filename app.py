import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# ЧАСОВИЙ ПОЯС
# ============================================================

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


# ============================================================
# НАЛАШТУВАННЯ STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="⚖️",
    layout="centered"
)


# ============================================================
# ПРОФІЛЬ
# ============================================================

user_profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"]
)

profile_prefix = "user1" if user_profile == "Я" else "user2"


# ============================================================
# ФАЙЛИ
# ============================================================

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"
WATCH_FILE = f"watch_burned_{profile_prefix}.json"


# ============================================================
# ФОНОВЕ ЗОБРАЖЕННЯ
# ============================================================

IMAGE_URL = (
    "https://i.postimg.cc/kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    f"""
    <style>

    /* ---------- ОСНОВНИЙ ФОН ---------- */

    .stApp {{
        background:
            linear-gradient(
                rgba(0,0,0,.72),
                rgba(0,0,0,.88)
            ),
            url("{IMAGE_URL}") center / cover fixed;
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


    /* ---------- КНОПКИ ---------- */

    div.stButton > button {{
        border-radius: 16px !important;
        min-height: 48px !important;

        border: 1px solid
            rgba(255,255,255,.18) !important;

        background:
            rgba(30,32,40,.94) !important;

        color: white !important;

        font-weight: 700 !important;

        transition:
            transform .10s ease,
            background .10s ease,
            box-shadow .10s ease !important;
    }}

    div.stButton > button:hover {{
        border-color:
            rgba(255,255,255,.42) !important;

        background:
            rgba(45,48,59,.98) !important;

        transform: translateY(-1px);
    }}

    div.stButton > button:active {{
        transform: scale(.96) !important;

        background:
            rgba(70,73,88,1) !important;

        box-shadow:
            inset 0 3px 10px
            rgba(0,0,0,.55) !important;
    }}


    /* ---------- INPUT ---------- */

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {{
        background:
            rgba(32,33,43,.96) !important;

        border-radius: 15px !important;

        border-color:
            rgba(255,255,255,.10) !important;
    }}

    input {{
        color: white !important;
    }}


    /* ---------- СЕКЦІЇ ---------- */

    .section {{
        background:
            rgba(10,12,17,.68);

        border:
            1px solid rgba(255,255,255,.14);

        border-radius: 22px;

        padding: 18px;

        margin: 12px 0;

        backdrop-filter: blur(8px);
    }}


    /* ========================================================
       КРУЖОК
       ======================================================== */

    .donut-wrap {{
        display: flex;

        flex-direction: column;

        align-items: center;

        justify-content: center;

        margin: 12px 0 18px;
    }}

    .donut {{
        width: 220px;

        height: 220px;

        border-radius: 50%;

        display: flex;

        align-items: center;

        justify-content: center;

        box-shadow:
            0 8px 30px
            rgba(0,0,0,.45);
    }}

    .donut-hole {{
        width: 154px;

        height: 154px;

        border-radius: 50%;

        background: #11131a;

        display: flex;

        flex-direction: column;

        align-items: center;

        justify-content: center;

        text-align: center;

        color: white;

        border:
            1px solid
            rgba(255,255,255,.08);
    }}

    .balance {{
        font-size: 14px;

        font-weight: 800;

        margin-bottom: 5px;
    }}

    .kcal-main {{
        font-size: 25px;

        font-weight: 900;

        line-height: 1.05;
    }}

    .kcal-sub {{
        color: #aeb3c2;

        font-size: 11px;

        margin-top: 5px;
    }}


    /* ---------- БЖВ ---------- */

    .macros {{
        display: flex;

        justify-content: center;

        gap: 8px;

        flex-wrap: wrap;

        margin-top: 12px;
    }}

    .macro {{
        border-radius: 14px;

        padding: 8px 11px;

        background:
            rgba(20,22,29,.92);

        border:
            1px solid
            rgba(255,255,255,.10);

        font-size: 12px;

        font-weight: 700;
    }}

    .macro.p {{
        color: #36A2EB;
    }}

    .macro.f {{
        color: #FFCE56;
    }}

    .macro.c {{
        color: #FF6384;
    }}


    /* ========================================================
       ГОДИННИК
       ======================================================== */

    .watch-card {{
        background:
            rgba(18,20,27,.86);

        border:
            1px solid
            rgba(255,255,255,.12);

        border-radius: 18px;

        padding: 14px;
    }}

    .watch-title {{
        font-size: 20px;

        font-weight: 900;

        margin-bottom: 10px;
    }}


    /* ========================================================
       ЛОГ
       ======================================================== */

    .log-card {{
        background:
            rgba(13,15,21,.80);

        border:
            1px solid
            rgba(255,255,255,.13);

        border-radius: 18px;

        padding: 14px;

        margin: 12px 0;
    }}

    .log-head {{
        display: flex;

        justify-content: space-between;

        gap: 12px;

        align-items: flex-start;
    }}

    .log-title {{
        font-size: 16px;

        font-weight: 800;

        line-height: 1.35;
    }}

    .log-kcal {{
        white-space: nowrap;

        font-size: 17px;

        font-weight: 900;
    }}


    /* ---------- ПРОДУКТИ ---------- */

    .food-list {{
        margin-top: 10px;

        border-top:
            1px solid
            rgba(255,255,255,.08);

        padding-top: 8px;
    }}

    .food-line {{
        display: flex;

        justify-content: space-between;

        gap: 10px;

        padding: 5px 0;

        font-size: 13px;
    }}

    .food-name {{
        color: #e9ebf2;
    }}

    .food-cal {{
        color: #8fd7ff;

        font-weight: 800;

        white-space: nowrap;
    }}


    /* ---------- БЖВ В ЛОГУ ---------- */

    .bju {{
        margin-top: 9px;

        display: flex;

        gap: 8px;

        flex-wrap: wrap;

        font-size: 12px;

        font-weight: 700;
    }}

    .bju span {{
        background:
            rgba(255,255,255,.06);

        border-radius: 10px;

        padding: 5px 8px;
    }}


    /* ---------- ДЕФІЦИТ / ПРОФІЦИТ ---------- */

    .status {{
        text-align: center;

        font-weight: 900;

        font-size: 20px;

        padding: 15px;

        border-radius: 17px;

        margin: 15px 0;
    }}

    .deficit {{
        color: #5ee89a;

        background:
            rgba(20,120,65,.30);

        border:
            1px solid
            rgba(94,232,154,.25);
    }}

    .surplus {{
        color: #ff7373;

        background:
            rgba(140,30,35,.30);

        border:
            1px solid
            rgba(255,115,115,.25);
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "edit_mode" not in st.session_state:
    st.session_state["edit_mode"] = False

if "selected_edit" not in st.session_state:
    st.session_state["selected_edit"] = None


# ============================================================
# GEMINI
# ============================================================

api_key = (
    st.secrets.get("GEMINI_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
)

if not api_key:
    st.error("⚠️ Не знайдено GEMINI_API_KEY.")
    st.stop()


client = genai.Client(api_key=api_key)

# Як ти просив
GEMINI_MODEL = "gemini-3.6-flash"


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
    "Вуглеводи",
    "Продукти"
]


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

def load_settings():

    default = {
        "calories": 2000,
        "protein": 160,
        "fat": 70,
        "carbs": 180,
        "bmr_daily": 1850,
        "initial_weight": 89.0
    }

    if os.path.exists(SETTINGS_FILE):

        try:

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                saved = json.load(f)

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
    ) as f:

        json.dump(
            settings,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# ДАНІ
# ============================================================

def load_data():

    empty = pd.DataFrame(
        columns=COLUMNS
    )

    if not os.path.exists(EXCEL_FILE):
        return empty

    try:

        df = pd.read_excel(EXCEL_FILE)

        for col in COLUMNS:

            if col not in df.columns:

                if col in [
                    "Опис",
                    "Тип",
                    "Продукти"
                ]:

                    df[col] = ""

                else:

                    df[col] = 0

        df = df[COLUMNS]

        for col in [
            "Спожито",
            "Спалено",
            "Білки",
            "Жири",
            "Вуглеводи"
        ]:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0.0)

        df["Дата"] = df["Дата"].astype(str)

        df["Час"] = (
            df["Час"]
            .astype(str)
            .str[:5]
        )

        df["Продукти"] = (
            df["Продукти"]
            .fillna("")
            .astype(str)
        )

        return df

    except Exception:

        return empty


def save_data(df):

    df.to_excel(
        EXCEL_FILE,
        index=False
    )


# ============================================================
# ГОДИННИК
# ============================================================

def load_watch():

    if not os.path.exists(WATCH_FILE):
        return {}

    try:

        with open(
            WATCH_FILE,
            "r",
            encoding="utf-8"
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
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# ПРОДУКТИ
# ============================================================

def parse_products(value):

    if not value:
        return []

    try:

        data = json.loads(value)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def normalize_products(products):

    result = []

    if not isinstance(
        products,
        list
    ):

        return result

    for product in products:

        if not isinstance(
            product,
            dict
        ):

            continue

        name = str(
            product.get(
                "name",
                ""
            )
        ).strip()

        kcal = float(
            product.get(
                "kcal",
                0
            ) or 0
        )

        protein = float(
            product.get(
                "protein",
                0
            ) or 0
        )

        fat = float(
            product.get(
                "fat",
                0
            ) or 0
        )

        carbs = float(
            product.get(
                "carbs",
                0
            ) or 0
        )

        if name:

            result.append(
                {
                    "name": name,
                    "kcal": kcal,
                    "protein": protein,
                    "fat": fat,
                    "carbs": carbs
                }
            )

    return result


def row_products(row):

    products = parse_products(
        row.get(
            "Продукти",
            ""
        )
    )

    if products:

        return normalize_products(
            products
        )

    if (
        str(row.get("Тип", ""))
        == "Їжа"
    ):

        return [
            {
                "name": str(
                    row.get(
                        "Опис",
                        "Їжа"
                    )
                ),

                "kcal": float(
                    row.get(
                        "Спожито",
                        0
                    ) or 0
                ),

                "protein": float(
                    row.get(
                        "Білки",
                        0
                    ) or 0
                ),

                "fat": float(
                    row.get(
                        "Жири",
                        0
                    ) or 0
                ),

                "carbs": float(
                    row.get(
                        "Вуглеводи",
                        0
                    ) or 0
                )
            }
        ]

    return []


# ============================================================
# BMR
# ============================================================

def today_bmr(
    settings,
    date_str
):

    daily = float(
        settings.get(
            "bmr_daily",
            1850
        )
    )

    today = datetime.now(
        LOCAL_TZ
    ).strftime(
        "%Y-%m-%d"
    )

    if str(date_str) == today:

        now = datetime.now(
            LOCAL_TZ
        )

        hours = (
            now.hour
            + now.minute / 60
        )

        return daily * min(
            hours / 24,
            1
        )

    return daily


# ============================================================
# РОЗРАХУНОК ДНЯ
# ============================================================

def calculate_day(
    df,
    date_str,
    settings,
    watch_burned=0
):

    day = df[
        df["Дата"].astype(str)
        == str(date_str)
    ].copy()

    food = day[
        day["Тип"].astype(str)
        == "Їжа"
    ]

    consumed = float(
        food["Спожито"].sum()
    )

    protein = float(
        food["Білки"].sum()
    )

    fat = float(
        food["Жири"].sum()
    )

    carbs = float(
        food["Вуглеводи"].sum()
    )

    exercise = float(
        day[
            day["Тип"].astype(str)
            == "Тренування"
        ]["Спалено"].sum()
    )

    watch = float(
        watch_burned or 0
    )

    burned = (
        today_bmr(
            settings,
            date_str
        )
        + exercise
        + watch
    )

    balance = (
        burned
        - consumed
    )

    return (
        consumed,
        burned,
        balance,
        protein,
        fat,
        carbs,
        exercise,
        watch
    )


# ============================================================
# ВАГА
# ============================================================

def calculate_weight(
    df,
    settings,
    watch_by_date=None
):

    initial = float(
        settings.get(
            "initial_weight",
            89.0
        )
    )

    if df.empty and not watch_by_date:
        return initial

    watch_by_date = (
        watch_by_date
        or {}
    )

    dates = set(
        df["Дата"]
        .astype(str)
        .unique()
        if not df.empty
        else []
    )

    dates.update(
        watch_by_date.keys()
    )

    total_balance = 0.0

    for date_str in sorted(
        dates
    ):

        (
            consumed,
            burned,
            balance,
            _p,
            _f,
            _c,
            _exercise,
            _watch
        ) = calculate_day(
            df,
            date_str,
            settings,
            watch_by_date.get(
                date_str,
                0
            )
        )

        total_balance += balance

    return max(
        0.0,
        initial
        - total_balance / 7700.0
    )


# ============================================================
# ЗАВАНТАЖЕННЯ
# ============================================================

settings = load_settings()

df = load_data()

watch_by_date = load_watch()


# ============================================================
# ЗАГОЛОВОК
# ============================================================

current_weight = calculate_weight(
    df,
    settings,
    watch_by_date
)

st.title(
    "⚖️ Мій Фітнес"
)

st.caption(
    f"Профіль: {user_profile} "
    f"• Поточна вага: "
    f"~{current_weight:.1f} кг"
)


# ============================================================
# ДОДАВАННЯ ЇЖІ
# ============================================================

st.markdown(
    "### 🍽️ Додати запис"
)

user_input = st.text_input(
    "Що з'їв / яке тренування?",
    placeholder=(
        "Наприклад: "
        "плов з куркою 350 г, "
        "2 яйця і хліб 60 г"
    ),
    key="food_input"
)


col1, col2 = st.columns(2)

with col1:

    add_btn = st.button(
        "✅ Додати в лог",
        use_container_width=True
    )

with col2:

    undo_btn = st.button(
        "↩️ Відмінити останні 10",
        use_container_width=True
    )


# ============================================================
# ВІДМІНА ОСТАННЬОГО
# ============================================================

if (
    undo_btn
    and not df.empty
):

    n_undo = min(10, len(df))

    trash_rows = (
        df.tail(n_undo)
        .to_dict(
            orient="records"
        )
    )

    with open(
        TRASH_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            trash_rows,
            f,
            ensure_ascii=False,
            indent=2,
            default=str
        )

    df = df.iloc[:-n_undo].copy()

    save_data(df)

    st.rerun()


# ============================================================
# GEMINI АНАЛІЗ
# ============================================================

if add_btn:

    text = (
        user_input
        or ""
    ).strip()

    if not text:

        st.warning(
            "Введи продукт "
            "або тренування."
        )

    else:

        prompt = f"""
Ти харчовий трекер.

Проаналізуй цей запис:

"{text}"

Поверни ТІЛЬКИ валідний JSON.
Без markdown.
Без ```.

Формат:

{{
  "type": "Їжа" або "Тренування",

  "description": "короткий опис",

  "total_kcal": число,

  "burned_kcal": число,

  "protein": число,

  "fat": число,

  "carbs": число,

  "products": [
    {{
      "name": "назва продукту",
      "kcal": число,
      "protein": число,
      "fat": число,
      "carbs": число
    }}
  ]
}}

ПРАВИЛА:

1. Якщо це Їжа:
   - total_kcal = сума калорій
     усіх продуктів.
   - products обов'язково має
     містити кожен продукт окремо.
   - біля кожного продукту
     повинні бути його kcal.
   - protein/fat/carbs =
     загальна кількість БЖВ.

2. Якщо це Тренування:
   - total_kcal = 0.
   - burned_kcal =
     витрачені калорії.
   - products = [].

3. Не змішуй спожиті
   та спалені калорії.

4. Опис зроби коротким.
"""


        try:

            response = (
                client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
            )

            data = json.loads(
                response.text
            )

            entry_type = (
                "Тренування"
                if str(
                    data.get(
                        "type",
                        ""
                    )
                ).lower().startswith(
                    "трен"
                )
                else "Їжа"
            )

            products = normalize_products(
                data.get(
                    "products",
                    []
                )
            )


            # ------------------------
            # ЇЖА
            # ------------------------

            if entry_type == "Їжа":

                total_kcal = (
                    sum(
                        p["kcal"]
                        for p in products
                    )
                    if products
                    else float(
                        data.get(
                            "total_kcal",
                            0
                        )
                        or 0
                    )
                )

                protein = (
                    sum(
                        p["protein"]
                        for p in products
                    )
                    if products
                    else float(
                        data.get(
                            "protein",
                            0
                        )
                        or 0
                    )
                )

                fat = (
                    sum(
                        p["fat"]
                        for p in products
                    )
                    if products
                    else float(
                        data.get(
                            "fat",
                            0
                        )
                        or 0
                    )
                )

                carbs = (
                    sum(
                        p["carbs"]
                        for p in products
                    )
                    if products
                    else float(
                        data.get(
                            "carbs",
                            0
                        )
                        or 0
                    )
                )

                burned = 0.0


            # ------------------------
            # ТРЕНУВАННЯ
            # ------------------------

            else:

                total_kcal = 0.0

                protein = 0.0

                fat = 0.0

                carbs = 0.0

                burned = float(
                    data.get(
                        "burned_kcal",
                        0
                    )
                    or 0
                )


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
                    str(
                        data.get(
                            "description"
                        )
                        or text
                    ),

                "Тип":
                    entry_type,

                "Спожито":
                    total_kcal,

                "Спалено":
                    burned,

                "Білки":
                    protein,

                "Жири":
                    fat,

                "Вуглеводи":
                    carbs,

                "Продукти":
                    json.dumps(
                        products,
                        ensure_ascii=False
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


            save_data(df)


            # ОЧИЩАЄМО ПОЛЕ
            st.session_state[
                "food_input"
            ] = ""


            st.success(
                "✅ Запис додано"
            )

            st.rerun()


        except Exception as e:

            st.error(
                f"Помилка Gemini: {e}"
            )


# ============================================================
# ДНІ
# ============================================================

today = datetime.now(
    LOCAL_TZ
).strftime(
    "%Y-%m-%d"
)


dates = [today]


if not df.empty:

    for d in sorted(
        df["Дата"]
        .astype(str)
        .unique(),
        reverse=True
    ):

        if d not in dates:
            dates.append(d)


selected_date = st.selectbox(
    "📅 День",
    dates
)


# ============================================================
# КАЛОРІЇ З ГОДИННИКА
# ============================================================

st.markdown(
    "### ⌚ Калорії з годинника"
)


watch_key = (
    f"watch_"
    f"{profile_prefix}_"
    f"{selected_date}"
)


if watch_key not in st.session_state:

    st.session_state[
        watch_key
    ] = float(
        watch_by_date.get(
            selected_date,
            0
        )
    )


watch_cols = st.columns(
    [4, 1]
)


with watch_cols[0]:

    watch_value = st.number_input(
        "Спалено сьогодні, ккал",

        min_value=0.0,

        value=float(
            st.session_state[
                watch_key
            ]
        ),

        step=10.0,

        key=(
            f"watch_input_"
            f"{profile_prefix}_"
            f"{selected_date}"
        )
    )


with watch_cols[1]:

    apply_watch = st.button(
        "🔄",
        key=(
            f"watch_apply_"
            f"{profile_prefix}_"
            f"{selected_date}"
        ),
        use_container_width=True
    )


if apply_watch:

    # ВАЖЛИВО:
    # НОВЕ ЗНАЧЕННЯ ЗАМІНЮЄ СТАРЕ.
    # НІЧОГО НЕ ДОДАЄМО.

    st.session_state[
        watch_key
    ] = float(
        watch_value
    )

    watch_by_date[
        selected_date
    ] = float(
        watch_value
    )

    save_watch(
        watch_by_date
    )

    st.rerun()


# ============================================================
# РОЗРАХУНОК
# ============================================================

watch_now = float(
    st.session_state[
        watch_key
    ]
)


(
    consumed,
    burned,
    balance,
    protein,
    fat,
    carbs,
    exercise,
    watch
) = calculate_day(
    df,
    selected_date,
    settings,
    watch_now
)


target = float(
    settings["calories"]
)


# ============================================================
# КРУЖОК БЖВ
# ============================================================

total_macros = (
    protein
    + fat
    + carbs
)


if total_macros > 0:

    p_deg = (
        protein
        / total_macros
        * 360
    )

    f_deg = (
        p_deg
        + fat
        / total_macros
        * 360
    )

    c_deg = (
        f_deg
        + carbs
        / total_macros
        * 360
    )

    gradient = (
        "conic-gradient("
        f"#36A2EB 0deg {p_deg}deg, "
        f"#FFCE56 {p_deg}deg {f_deg}deg, "
        f"#FF6384 {f_deg}deg {c_deg}deg"
        ")"
    )

else:

    gradient = (
        "conic-gradient("
        "rgba(255,255,255,.14) "
        "0deg 360deg)"
    )


# ============================================================
# ДЕФІЦИТ / ПРОФІЦИТ
# ============================================================

if balance >= 0:

    balance_label = (
        f"📉 Дефіцит: "
        f"{abs(balance):.0f} ккал"
    )

    balance_class = "deficit"

else:

    balance_label = (
        f"📈 Профіцит: "
        f"{abs(balance):.0f} ккал"
    )

    balance_class = "surplus"


# ============================================================
# HTML КРУЖКА
# ============================================================

donut_html = f"""
<div class="section">

    <div class="donut-wrap">

        <div
            class="donut"
            style="background:{gradient};"
        >

            <div class="donut-hole">

                <div class="balance">
                    {balance_label}
                </div>

                <div class="kcal-main">
                    {consumed:.0f}
                </div>

                <div class="kcal-sub">
                    з {target:.0f} ккал
                </div>

            </div>

        </div>


        <div class="macros">

            <div class="macro p">
                🥩 Білки
                {protein:.0f}/
                {settings["protein"]} г
            </div>

            <div class="macro f">
                🥑 Жири
                {fat:.0f}/
                {settings["fat"]} г
            </div>

            <div class="macro c">
                🍞 Вуглеводи
                {carbs:.0f}/
                {settings["carbs"]} г
            </div>

        </div>

    </div>

</div>
"""


st.markdown(
    donut_html,
    unsafe_allow_html=True
)


# ============================================================
# СТАТУС
# ============================================================

status_text = (
    f"📉 Дефіцит: "
    f"{abs(balance):.0f} ккал"
    if balance >= 0
    else
    f"📈 Профіцит: "
    f"{abs(balance):.0f} ккал"
)


st.markdown(
    f"""
    <div class="status {balance_class}">
        {status_text}
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# РЕДАКТОР ЦІЛЕЙ
# ============================================================

if st.button(
    "⚙️ Редактор цілей",
    use_container_width=True
):

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


if st.session_state[
    "edit_mode"
]:

    st.markdown(
        "### ✏️ Редактор"
    )


    e_cal = st.number_input(
        "Добова норма калорій",
        value=int(
            settings["calories"]
        ),
        step=10
    )


    e_prot = st.number_input(
        "🥩 Білки, г",
        value=int(
            settings["protein"]
        ),
        step=5
    )


    e_fat = st.number_input(
        "🥑 Жири, г",
        value=int(
            settings["fat"]
        ),
        step=5
    )


    e_carb = st.number_input(
        "🍞 Вуглеводи, г",
        value=int(
            settings["carbs"]
        ),
        step=5
    )


    e_bmr = st.number_input(
        "Базові витрати BMR, ккал/добу",
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
        "💾 Зберегти",
        type="primary",
        use_container_width=True
    ):

        save_settings(
            {
                "calories": e_cal,
                "protein": e_prot,
                "fat": e_fat,
                "carbs": e_carb,
                "bmr_daily": e_bmr,
                "initial_weight": e_weight
            }
        )

        st.session_state[
            "edit_mode"
        ] = False

        st.rerun()


# ============================================================
# ЛОГ
# ============================================================

st.markdown(
    f"### 📝 Влог за {selected_date}"
)


day_df = df[
    df["Дата"].astype(str)
    == str(selected_date)
].copy()


if day_df.empty:

    st.info(
        "За цей день записів ще немає."
    )


else:

    # Нові записи зверху
    for idx, row in day_df.iloc[::-1].iterrows():

        entry_type = str(
            row["Тип"]
        )


        if entry_type == "Їжа":

            icon = "🍽️"

            kcal = float(
                row["Спожито"]
            )

        else:

            icon = "💪"

            kcal = float(
                row["Спалено"]
            )


        products = row_products(
            row
        )


        # ----------------------------------------------------
        # ПРОДУКТИ
        # ----------------------------------------------------

        food_lines = ""


        if (
            entry_type == "Їжа"
            and products
        ):

            food_lines = (
                '<div class="food-list">'
            )


            for product in products:

                food_lines += f"""
                <div class="food-line">

                    <span class="food-name">
                        🍴 {product["name"]}
                    </span>

                    <span class="food-cal">
                        {product["kcal"]:.0f} ккал
                    </span>

                </div>
                """


            food_lines += (
                "</div>"
            )


        # ----------------------------------------------------
        # БЖВ
        # ----------------------------------------------------

        bju = ""


        if entry_type == "Їжа":

            bju = f"""
            <div class="bju">

                <span>
                    🥩
                    {float(row["Білки"]):.0f} г
                </span>

                <span>
                    🥑
                    {float(row["Жири"]):.0f} г
                </span>

                <span>
                    🍞
                    {float(row["Вуглеводи"]):.0f} г
                </span>

            </div>
            """


        # ----------------------------------------------------
        # КАРТКА ЛОГУ
        # ----------------------------------------------------

        html = f"""
        <div class="log-card">

            <div class="log-head">

                <div class="log-title">

                    {str(row["Час"])[:5]}
                    {icon}
                    {str(row["Опис"])}

                </div>


                <div class="log-kcal">

                    {kcal:+.0f} ккал

                </div>

            </div>

            {food_lines}

            {bju}

        </div>
        """


        st.markdown(
            html,
            unsafe_allow_html=True
        )


        # ----------------------------------------------------
        # КНОПКА РЕДАГУВАННЯ
        # ----------------------------------------------------

        if st.button(
            "✏️ Редагувати",
            key=f"edit_{idx}",
            use_container_width=True
        ):

            st.session_state[
                "selected_edit"
            ] = int(idx)

            st.rerun()


        # ----------------------------------------------------
        # РЕДАКТОР ЗАПИСУ
        # ----------------------------------------------------

        if (
            st.session_state[
                "selected_edit"
            ]
            == int(idx)
        ):

            st.markdown(
                "**✏️ Редагування запису**"
            )


            edit_desc = st.text_input(
                "Опис",

                value=str(
                    row["Опис"]
                ),

                key=f"desc_{idx}"
            )


            edit_kcal = st.number_input(
                "Калорії",

                value=float(
                    row["Спожито"]
                    if entry_type == "Їжа"
                    else row["Спалено"]
                ),

                min_value=0.0,

                step=1.0,

                key=f"kcal_{idx}"
            )


            ec1, ec2, ec3 = st.columns(3)


            with ec1:

                edit_p = st.number_input(
                    "🥩 Білки",

                    value=float(
                        row["Білки"]
                    ),

                    min_value=0.0,

                    step=1.0,

                    key=f"p_{idx}"
                )


            with ec2:

                edit_f = st.number_input(
                    "🥑 Жири",

                    value=float(
                        row["Жири"]
                    ),

                    min_value=0.0,

                    step=1.0,

                    key=f"f_{idx}"
                )


            with ec3:

                edit_c = st.number_input(
                    "🍞 Вуглеводи",

                    value=float(
                        row["Вуглеводи"]
                    ),

                    min_value=0.0,

                    step=1.0,

                    key=f"c_{idx}"
                )


            s1, s2 = st.columns(2)


            with s1:

                if st.button(
                    "💾 Застосувати",

                    key=f"save_edit_{idx}",

                    type="primary",

                    use_container_width=True
                ):

                    df.loc[
                        idx,
                        "Опис"
                    ] = edit_desc


                    if entry_type == "Їжа":

                        df.loc[
                            idx,
                            "Спожито"
                        ] = edit_kcal

                        df.loc[
                            idx,
                            "Спалено"
                        ] = 0


                    else:

                        df.loc[
                            idx,
                            "Спожито"
                        ] = 0

                        df.loc[
                            idx,
                            "Спалено"
                        ] = edit_kcal


                    df.loc[
                        idx,
                        "Білки"
                    ] = edit_p


                    df.loc[
                        idx,
                        "Жири"
                    ] = edit_f


                    df.loc[
                        idx,
                        "Вуглеводи"
                    ] = edit_c


                    save_data(df)


                    st.session_state[
                        "selected_edit"
                    ] = None


                    st.rerun()


            with s2:

                if st.button(
                    "✖️ Скасувати",

                    key=f"cancel_edit_{idx}",

                    use_container_width=True
                ):

                    st.session_state[
                        "selected_edit"
                    ] = None

                    st.rerun()


# ============================================================
# ПІДСУМОК
# ============================================================

st.markdown(
    "### 📊 Підсумок"
)


c1, c2, c3 = st.columns(3)


with c1:

    st.metric(
        "🍽️ З'їдено",
        f"{consumed:.0f} ккал"
    )


with c2:

    st.metric(
        "🔥 Витрачено",
        f"{burned:.0f} ккал"
    )


with c3:

    st.metric(
        "⌚ Годинник",
        f"{watch:.0f} ккал"
    )
