import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


# =========================================================
# ЧАСОВИЙ ПОЯС
# =========================================================

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


# =========================================================
# НАЛАШТУВАННЯ STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="⚖️",
    layout="centered"
)


# =========================================================
# ПРОФІЛЬ
# =========================================================

user_profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"]
)

profile_prefix = "user1" if user_profile == "Я" else "user2"


EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"


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
]


# =========================================================
# GEMINI
# =========================================================

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            linear-gradient(
                rgba(0,0,0,.74),
                rgba(0,0,0,.88)
            ),
            url("https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg");

        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    #MainMenu,
    footer,
    header {
        visibility: hidden;
    }


    .block-container {
        max-width: 760px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }


    h1,
    h2,
    h3,
    p,
    label,
    .stMarkdown {
        color: white !important;
    }


    /* =====================================================
       КНОПКИ
       ===================================================== */

    div.stButton > button {

        min-height: 48px;

        border-radius: 16px;

        border: 1px solid rgba(255,255,255,.18);

        background:
            linear-gradient(
                145deg,
                rgba(40,42,52,.98),
                rgba(25,27,34,.98)
            );

        color: white;

        font-weight: 700;

        transition:
            transform .10s ease,
            box-shadow .10s ease,
            background .10s ease;

        box-shadow:
            0 5px 18px rgba(0,0,0,.28);
    }


    div.stButton > button:hover {

        border-color:
            rgba(255,255,255,.42);

        background:
            linear-gradient(
                145deg,
                rgba(55,57,70,1),
                rgba(30,32,41,1)
            );

        transform: translateY(-1px);
    }


    div.stButton > button:active {

        transform:
            translateY(3px)
            scale(.975);

        background:
            linear-gradient(
                145deg,
                rgba(80,82,98,1),
                rgba(48,50,62,1)
            );

        box-shadow:
            inset 0 4px 10px rgba(0,0,0,.42);
    }


    div.stButton > button[kind="primary"] {

        background:
            linear-gradient(
                135deg,
                #246BFD,
                #6C4DFF
            );

        border: none;

        box-shadow:
            0 7px 22px rgba(54,91,255,.32);
    }


    div.stButton > button[kind="primary"]:active {

        background:
            linear-gradient(
                135deg,
                #1d55d2,
                #5638d7
            );
    }


    /* =====================================================
       БЛОКИ
       ===================================================== */

    .section {

        background:
            rgba(14,16,22,.76);

        border:
            1px solid rgba(255,255,255,.14);

        border-radius:
            22px;

        padding:
            18px;

        margin:
            14px 0;

        box-shadow:
            0 12px 35px rgba(0,0,0,.20);

        backdrop-filter:
            blur(8px);
    }


    .small-muted {

        color:
            rgba(255,255,255,.62);

        font-size:
            13px;
    }


    /* =====================================================
       ЛОГ
       ===================================================== */

    .log-card {

        background:
            rgba(12,14,19,.80);

        border:
            1px solid rgba(255,255,255,.14);

        border-radius:
            20px;

        padding:
            16px;

        margin:
            12px 0;

        box-shadow:
            0 8px 24px rgba(0,0,0,.16);
    }


    .log-head {

        display:
            flex;

        gap:
            10px;

        justify-content:
            space-between;

        align-items:
            flex-start;
    }


    .log-title {

        font-size:
            17px;

        font-weight:
            750;

        line-height:
            1.35;

        color:
            #fff;
    }


    .log-kcal {

        white-space:
            nowrap;

        font-size:
            18px;

        font-weight:
            800;

        color:
            #72a8ff;
    }


    .badge {

        display:
            inline-block;

        padding:
            4px 9px;

        border-radius:
            999px;

        background:
            rgba(255,255,255,.10);

        color:
            rgba(255,255,255,.75);

        font-size:
            12px;

        margin-top:
            8px;
    }


    /* =====================================================
       INPUT
       ===================================================== */

    div[data-baseweb="input"],
    div[data-baseweb="select"] {

        border-radius:
            15px !important;
    }


    input,
    textarea {

        color:
            white !important;
    }


    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {

    "edit_mode": False,

    "input_text": "",

    "editing_index": None,

    "undo_stack": [],

}


for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


# =========================================================
# ФУНКЦІЇ
# =========================================================

def default_settings():

    return {

        "calories": 2000,

        "bmr_daily": 1850,

        "initial_weight": 89.0,

        # Значення годинника зберігаються окремо
        # для кожного дня.
        "watch_burned": {},

    }


def load_settings():

    defaults_local = default_settings()

    if os.path.exists(SETTINGS_FILE):

        try:

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                saved = json.load(f)

            defaults_local.update(saved)

        except Exception:

            pass

    return defaults_local


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


def empty_df():

    return pd.DataFrame(
        columns=COLUMNS
    )


def load_data():

    if not os.path.exists(EXCEL_FILE):

        return empty_df()

    try:

        df = pd.read_excel(EXCEL_FILE)

    except Exception:

        return empty_df()


    for col in COLUMNS:

        if col not in df.columns:

            if col in {
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи"
            }:

                df[col] = 0

            else:

                df[col] = ""


    df = df[COLUMNS].copy()


    df["Дата"] = (
        df["Дата"]
        .astype(str)
    )


    df["Час"] = (
        df["Час"]
        .astype(str)
        .str[:5]
    )


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


    return df


def save_data(df):

    out = df.copy()

    for col in [
        "Спожито",
        "Спалено",
        "Білки",
        "Жири",
        "Вуглеводи"
    ]:

        out[col] = pd.to_numeric(
            out[col],
            errors="coerce"
        ).fillna(0.0)


    out.to_excel(
        EXCEL_FILE,
        index=False
    )


def push_undo(df):

    snapshot = df.to_dict(
        orient="records"
    )

    st.session_state["undo_stack"].append(
        snapshot
    )

    # максимум 10 змін
    st.session_state["undo_stack"] = (
        st.session_state["undo_stack"][-10:]
    )


def undo_last():

    stack = st.session_state["undo_stack"]

    if not stack:

        return None

    previous = stack.pop()

    restored = pd.DataFrame(
        previous,
        columns=COLUMNS
    )

    if restored.empty:

        restored = empty_df()

    return restored


def esc(value):

    text = str(value)

    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\n", "<br>")
    )


def today_str():

    return datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")


def now_time():

    return datetime.now(
        LOCAL_TZ
    ).strftime("%H:%M")


# =========================================================
# РОЗРАХУНОК ДНЯ
# =========================================================

def day_totals(
    df,
    selected_date,
    settings
):

    if df.empty:

        day = empty_df()

    else:

        day = df[
            df["Дата"].astype(str)
            == str(selected_date)
        ].copy()


    consumed = (
        float(day["Спожито"].sum())
        if not day.empty
        else 0.0
    )


    # -----------------------------------------------------
    # ГОДИННИК
    #
    # ВАЖЛИВО:
    # це НЕ додається кожного разу.
    # Нове значення просто замінює старе.
    # -----------------------------------------------------

    watch_map = settings.get(
        "watch_burned",
        {}
    )

    watch_value = float(
        watch_map.get(
            str(selected_date),
            0
        ) or 0
    )


    bmr_daily = float(
        settings.get(
            "bmr_daily",
            1850
        )
    )


    # Для сьогоднішнього дня BMR
    # рахується пропорційно часу.
    if str(selected_date) == today_str():

        now = datetime.now(
            LOCAL_TZ
        )

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


    # Витрати = BMR + поточне значення годинника
    burned = bmr + watch_value


    # Позитивне = дефіцит
    # Негативне = профіцит
    balance = burned - consumed


    return (
        day,
        consumed,
        bmr,
        watch_value,
        burned,
        balance
    )


# =========================================================
# РОЗРАХУНОК ВАГИ
# =========================================================

def calculate_weight(
    df,
    settings
):

    initial = float(
        settings.get(
            "initial_weight",
            89.0
        )
    )


    bmr_daily = float(
        settings.get(
            "bmr_daily",
            1850
        )
    )


    if df.empty:

        return initial


    work = df.copy()


    work["Дата"] = (
        work["Дата"]
        .astype(str)
    )


    work["Спожито"] = pd.to_numeric(
        work["Спожито"],
        errors="coerce"
    ).fillna(0)


    today = today_str()

    now = datetime.now(
        LOCAL_TZ
    )


    accumulated_balance = 0.0


    for date_str in sorted(
        work["Дата"].unique()
    ):

        day = work[
            work["Дата"] == date_str
        ]


        eaten = float(
            day["Спожито"].sum()
        )


        # Годинник для конкретного дня
        watch_burned = float(
            settings
            .get("watch_burned", {})
            .get(
                str(date_str),
                0
            )
            or 0
        )


        if date_str == today:

            elapsed_hours = (
                now.hour
                +
                now.minute / 60.0
            )

            bmr = (
                bmr_daily
                *
                elapsed_hours
                /
                24.0
            )

        else:

            bmr = bmr_daily


        total_burned = (
            bmr
            +
            watch_burned
        )


        accumulated_balance += (
            total_burned
            -
            eaten
        )


    # 7700 ккал ≈ 1 кг
    return max(
        0.0,
        initial
        -
        accumulated_balance / 7700.0
    )


# =========================================================
# GEMINI
# =========================================================

api_key = (
    st.secrets.get("GEMINI_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
)


client = (
    genai.Client(api_key=api_key)
    if api_key
    else None
)


def analyse_text(text):

    if client is None:

        raise RuntimeError(
            "Не знайдено GEMINI_API_KEY "
            "у Secrets або змінних середовища."
        )


    prompt = f"""

Ти аналізуєш запис харчування або тренування
для фітнес-трекера.

Запис користувача:

"{text}"

Поверни СУВОРО JSON без markdown.

Ключі:

food_description
kcal_burned
total_consumed_kcal
total_protein
total_fat
total_carbs

Правила:

1. Якщо це їжа:
   total_consumed_kcal > 0
   kcal_burned = 0

2. Якщо це тренування:
   kcal_burned > 0
   total_consumed_kcal = 0

3. Не вигадуй тренування,
   якщо користувач описав їжу.

4. Калорії мають бути числовими.

5. Макроси можуть бути 0,
   якщо їх неможливо визначити.

6. food_description —
   коротка назва всього запису.

"""


    response = client.models.generate_content(

        model=GEMINI_MODEL,

        contents=prompt,

        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )


    return json.loads(
        response.text
    )


def add_entry_from_text(
    text,
    df
):

    data = analyse_text(
        text
    )


    eaten = float(
        data.get(
            "total_consumed_kcal",
            0
        ) or 0
    )


    burned = float(
        data.get(
            "kcal_burned",
            0
        ) or 0
    )


    if burned > 0 and eaten <= 0:

        entry_type = "Тренування"

    else:

        entry_type = "Їжа"

        burned = 0.0


    description = (
        data.get(
            "food_description"
        )
        or text.strip()
        or "Запис"
    )


    new_row = {

        "Дата":
            today_str(),

        "Час":
            now_time(),

        "Опис":
            description,

        "Тип":
            entry_type,

        "Спожито":
            eaten,

        "Спалено":
            burned,

        "Білки":
            float(
                data.get(
                    "total_protein",
                    0
                ) or 0
            ),

        "Жири":
            float(
                data.get(
                    "total_fat",
                    0
                ) or 0
            ),

        "Вуглеводи":
            float(
                data.get(
                    "total_carbs",
                    0
                ) or 0
            ),
    }


    return pd.concat(
        [
            df,
            pd.DataFrame(
                [new_row]
            )
        ],
        ignore_index=True
    )


# =========================================================
# ЗАВАНТАЖЕННЯ
# =========================================================

settings = load_settings()

df_data = load_data()

weight = calculate_weight(
    df_data,
    settings
)


# =========================================================
# ЗАГОЛОВОК
# =========================================================

st.title(
    f"⚖️ Поточна вага: ~{weight:.1f} кг"
)


# =========================================================
# ДОДАВАННЯ ЇЖІ
# =========================================================

st.markdown(
    '<div class="section">',
    unsafe_allow_html=True
)


st.subheader(
    "🍽️ Додати запис"
)


st.text_input(
    "Їжа / тренування",

    key="input_text",

    placeholder=
        "Наприклад: 250 г плову з куркою",

    label_visibility="collapsed"
)


col_add, col_undo = st.columns(2)


with col_add:

    add_pressed = st.button(
        "✅ Додати в лог",
        type="primary",
        use_container_width=True
    )


with col_undo:

    undo_pressed = st.button(

        f"↩️ Відмінити "
        f"({len(st.session_state['undo_stack'])}/10)",

        use_container_width=True,

        disabled=
            not st.session_state[
                "undo_stack"
            ],
    )


# ---------------------------------------------------------
# ДОДАТИ
# ---------------------------------------------------------

if add_pressed:

    text = (
        st.session_state
        .get("input_text", "")
        .strip()
    )


    if not text:

        st.warning(
            "Введи їжу або тренування."
        )

    else:

        try:

            push_undo(
                df_data
            )


            df_data = add_entry_from_text(
                text,
                df_data
            )


            save_data(
                df_data
            )


            # ---------------------------------------------
            # ОЧИЩЕННЯ ПОЛЯ
            # ---------------------------------------------

            st.session_state[
                "input_text"
            ] = ""


            st.rerun()


        except Exception as e:

            if st.session_state[
                "undo_stack"
            ]:

                st.session_state[
                    "undo_stack"
                ].pop()


            st.error(
                f"Помилка обробки: {e}"
            )


# ---------------------------------------------------------
# ВІДМІНИТИ
# ---------------------------------------------------------

if undo_pressed:

    restored = undo_last()

    if restored is not None:

        save_data(
            restored
        )

        st.rerun()


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# =========================================================
# ДНІ
# =========================================================

all_dates = [
    today_str()
]


if not df_data.empty:

    for date_value in sorted(
        df_data["Дата"]
        .astype(str)
        .unique(),
        reverse=True
    ):

        if date_value not in all_dates:

            all_dates.append(
                date_value
            )


selected_date = st.selectbox(
    "📅 День",
    all_dates
)


# =========================================================
# КАЛОРІЇ З ГОДИННИКА
# =========================================================

current_watch = float(

    settings
    .get(
        "watch_burned",
        {}
    )
    .get(
        str(selected_date),
        0
    )
    or 0
)


st.markdown(
    '<div class="section">',
    unsafe_allow_html=True
)


st.subheader(
    "⌚ Калорії з годинника"
)


watch_value = st.number_input(

    "Спалено за даними годинника, ккал",

    min_value=0.0,

    value=current_watch,

    step=10.0,

    key=f"watch_input_{selected_date}",
)


if st.button(
    "⌚ Зберегти калорії з годинника",
    use_container_width=True
):

    settings.setdefault(
        "watch_burned",
        {}
    )


    # =====================================================
    # ГОЛОВНЕ:
    # ЗАМІНА, А НЕ ДОДАВАННЯ
    # =====================================================

    settings[
        "watch_burned"
    ][str(selected_date)] = float(
        watch_value
    )


    save_settings(
        settings
    )


    st.rerun()


st.markdown(

    '<div class="small-muted">'
    'Нове число замінює попереднє, '
    'воно не додається.'
    '</div>',

    unsafe_allow_html=True
)


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# =========================================================
# НАЛАШТУВАННЯ / ВИДАЛЕННЯ
# =========================================================

col_settings, col_delete = st.columns(2)


with col_settings:

    settings_pressed = st.button(

        (
            "⚙️ Налаштування"
            if not st.session_state["edit_mode"]
            else
            "✕ Закрити налаштування"
        ),

        use_container_width=True
    )


with col_delete:

    delete_pressed = st.button(

        "🗑️ Видалити останній",

        use_container_width=True,

        disabled=df_data.empty
    )


if settings_pressed:

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


if delete_pressed and not df_data.empty:

    push_undo(
        df_data
    )


    df_data = (
        df_data
        .iloc[:-1]
        .copy()
    )


    save_data(
        df_data
    )


    st.rerun()


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

if st.session_state["edit_mode"]:

    st.markdown(
        '<div class="section">',
        unsafe_allow_html=True
    )


    st.subheader(
        "⚙️ Налаштування"
    )


    new_calories = st.number_input(

        "Добова ціль калорій",

        min_value=0,

        value=int(
            settings.get(
                "calories",
                2000
            )
        ),

        step=50
    )


    new_bmr = st.number_input(

        "Добова витрата / BMR, ккал",

        min_value=0,

        value=int(
            settings.get(
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
            settings.get(
                "initial_weight",
                89.0
            )
        ),

        step=0.1
    )


    if st.button(
        "💾 Зберегти",
        type="primary",
        use_container_width=True
    ):

        settings[
            "calories"
        ] = int(
            new_calories
        )


        settings[
            "bmr_daily"
        ] = int(
            new_bmr
        )


        settings[
            "initial_weight"
        ] = float(
            new_weight
        )


        save_settings(
            settings
        )


        st.session_state[
            "edit_mode"
        ] = False


        st.rerun()


    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# =========================================================
# СТАТИСТИКА
# =========================================================

(
    day_df,
    consumed,
    bmr,
    watch_burned,
    burned,
    balance
) = day_totals(

    df_data,

    selected_date,

    settings
)


target = max(
    float(
        settings.get(
            "calories",
            2000
        )
    ),
    1.0
)


progress = min(
    consumed / target,
    1.0
)


# =========================================================
# ДЕФІЦИТ / ПРОФІЦИТ
# =========================================================

if balance >= 0:

    balance_label = "Дефіцит"

    balance_color = "#35D07F"

else:

    balance_label = "Профіцит"

    balance_color = "#FF5C6C"


# =========================================================
# КРУЖОК
#
# ВАЖЛИВО:
# НЕ st.markdown()
# НЕ HTML ТЕКСТОМ.
#
# components.html -> справжній HTML/CSS.
# =========================================================

donut_html = f"""
<!doctype html>

<html>

<head>

<meta charset="utf-8">

<style>

html,
body {{

    margin: 0;

    padding: 0;

    background: transparent;

    font-family:
        Arial,
        sans-serif;
}}


.wrap {{

    display: flex;

    flex-direction: column;

    align-items: center;

    padding: 8px 0 2px;
}}


.ring {{

    width: 210px;

    height: 210px;

    border-radius: 50%;

    background:

        conic-gradient(

            #36A2EB

            0deg

            {progress * 360:.2f}deg,

            rgba(255,255,255,.10)

            {progress * 360:.2f}deg

            360deg
        );

    display: flex;

    align-items: center;

    justify-content: center;

    box-shadow:
        0 0 30px
        rgba(0,0,0,.45);
}}


.hole {{

    width: 154px;

    height: 154px;

    border-radius: 50%;

    background:
        #15171e;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    text-align: center;

    color: white;
}}


.balance {{

    font-size: 16px;

    font-weight: 800;

    color: {balance_color};

    margin-bottom: 7px;
}}


.main {{

    font-size: 28px;

    font-weight: 900;
}}


.sub {{

    font-size: 12px;

    color:
        rgba(255,255,255,.62);

    margin-top: 4px;
}}


.stats {{

    width:
        min(390px, 92vw);

    display: flex;

    gap: 8px;

    margin-top: 13px;
}}


.stat {{

    flex: 1;

    background:
        rgba(20,22,28,.88);

    border:
        1px solid
        rgba(255,255,255,.12);

    border-radius: 13px;

    padding: 10px 5px;

    text-align: center;

    color: white;
}}


.n {{

    font-size: 17px;

    font-weight: 800;
}}


.l {{

    color:
        rgba(255,255,255,.60);

    font-size: 11px;

    margin-top: 3px;
}}

</style>

</head>


<body>

<div class="wrap">


    <div class="ring">

        <div class="hole">

            <div class="balance">

                {balance_label}:
                {abs(balance):.0f} ккал

            </div>


            <div class="main">

                {consumed:.0f}

            </div>


            <div class="sub">

                з'їдено з
                {target:.0f}
                ккал

            </div>

        </div>

    </div>


    <div class="stats">


        <div class="stat">

            <div class="n">

                {bmr:.0f}

            </div>

            <div class="l">

                Добова витрата

            </div>

        </div>


        <div class="stat">

            <div class="n">

                {consumed:.0f}

            </div>

            <div class="l">

                З'їдено

            </div>

        </div>


        <div class="stat">

            <div class="n">

                {watch_burned:.0f}

            </div>

            <div class="l">

                Годинник

            </div>

        </div>


    </div>


</div>

</body>

</html>
"""


st.components.v1.html(

    donut_html,

    height=290,

    scrolling=False
)


# =========================================================
# ЛОГ
# =========================================================

st.subheader(
    f"📝 Лог за {selected_date}"
)


if day_df.empty:

    st.info(
        "За цей день записів ще немає."
    )


else:

    display_df = day_df.copy()


    display_df["_order"] = range(
        len(display_df)
    )


    display_df = (
        display_df
        .sort_values(
            [
                "Час",
                "_order"
            ],
            ascending=[
                False,
                False
            ]
        )
    )


    for row_index, (_, row) in enumerate(
        display_df.iterrows()
    ):

        row_id = (
            f"{selected_date}_{row_index}"
        )


        is_training = (
            str(row["Тип"])
            ==
            "Тренування"
        )


        icon = (
            "💪"
            if is_training
            else
            "🍽️"
        )


        if is_training:

            kcal_text = (
                f"-"
                f"{float(row['Спалено']):.0f}"
                f" ккал"
            )

        else:

            kcal_text = (
                f"+"
                f"{float(row['Спожито']):.0f}"
                f" ккал"
            )


        # -------------------------------------------------
        # КАРТКА ЗАПИСУ
        # -------------------------------------------------

        st.markdown(

            f"""
            <div class="log-card">

                <div class="log-head">

                    <div>

                        <div class="log-title">

                            {esc(
                                str(row["Час"])[:5]
                            )}

                            {icon}

                            {esc(
                                row["Опис"]
                            )}

                        </div>


                        <div class="badge">

                            {esc(
                                str(row["Тип"])
                            )}

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
        # РЕДАГУВАННЯ
        # -------------------------------------------------

        edit_key = (
            f"edit_{row_id}"
        )


        if st.button(

            "✏️ Редагувати",

            key=edit_key,

            use_container_width=True
        ):


            matches = df_data[

                (
                    df_data["Дата"]
                    .astype(str)
                    ==
                    str(row["Дата"])
                )

                &

                (
                    df_data["Час"]
                    .astype(str)
                    .str[:5]
                    ==
                    str(row["Час"])[:5]
                )

                &

                (
                    df_data["Опис"]
                    .astype(str)
                    ==
                    str(row["Опис"])
                )

            ].index.tolist()


            if matches:

                st.session_state[
                    "editing_index"
                ] = matches[-1]


                st.rerun()


        # -------------------------------------------------
        # ФОРМА РЕДАГУВАННЯ
        # -------------------------------------------------

        if (
            st.session_state.get(
                "editing_index"
            )
            is not None
        ):

            edit_idx = (
                st.session_state[
                    "editing_index"
                ]
            )


            if (
                edit_idx in df_data.index
                and
                str(
                    df_data.loc[
                        edit_idx,
                        "Дата"
                    ]
                )
                ==
                str(selected_date)
            ):


                st.markdown(
                    '<div class="section">',
                    unsafe_allow_html=True
                )


                st.markdown(
                    "### ✏️ Редагування запису"
                )


                edit_description = st.text_input(

                    "Опис",

                    value=str(
                        df_data.loc[
                            edit_idx,
                            "Опис"
                        ]
                    ),

                    key=
                        f"desc_{edit_idx}"
                )


                # Для їжі редагуємо спожиті ккал.
                # Для тренування — спалені.
                if (
                    str(
                        df_data.loc[
                            edit_idx,
                            "Тип"
                        ]
                    )
                    ==
                    "Тренування"
                ):

                    initial_kcal = float(
                        df_data.loc[
                            edit_idx,
                            "Спалено"
                        ]
                    )

                else:

                    initial_kcal = float(
                        df_data.loc[
                            edit_idx,
                            "Спожито"
                        ]
                    )


                edit_kcal = st.number_input(

                    "Калорії",

                    min_value=0.0,

                    value=initial_kcal,

                    step=1.0,

                    key=
                        f"kcal_{edit_idx}"
                )


                c1, c2 = st.columns(2)


                with c1:

                    if st.button(

                        "💾 Зберегти зміни",

                        key=
                            f"save_edit_{edit_idx}",

                        type="primary",

                        use_container_width=True
                    ):

                        push_undo(
                            df_data
                        )


                        df_data.loc[
                            edit_idx,
                            "Опис"
                        ] = (
                            edit_description
                        )


                        if (
                            str(
                                df_data.loc[
                                    edit_idx,
                                    "Тип"
                                ]
                            )
                            ==
                            "Тренування"
                        ):

                            df_data.loc[
                                edit_idx,
                                "Спалено"
                            ] = (
                                edit_kcal
                            )

                        else:

                            df_data.loc[
                                edit_idx,
                                "Спожито"
                            ] = (
                                edit_kcal
                            )


                        # ---------------------------------
                        # Після зміни все автоматично
                        # перераховується при rerun.
                        # ---------------------------------

                        save_data(
                            df_data
                        )


                        st.session_state[
                            "editing_index"
                        ] = None


                        st.rerun()


                with c2:

                    if st.button(

                        "✕ Скасувати",

                        key=
                            f"cancel_edit_{edit_idx}",

                        use_container_width=True
                    ):

                        st.session_state[
                            "editing_index"
                        ] = None


                        st.rerun()


                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )


# =========================================================
# ПІДСУМОК
# =========================================================

st.divider()


if balance >= 0:

    st.success(
        f"📉 Дефіцит: {balance:.0f} ккал"
    )

else:

    st.error(
        f"📈 Профіцит: {abs(balance):.0f} ккал"
    )


st.caption(

    f"⚖️ Орієнтир: "
    f"7700 ккал накопиченого дефіциту "
    f"≈ 1 кг. "
    f"Поточна розрахункова вага: "
    f"~{weight:.1f} кг."
)
