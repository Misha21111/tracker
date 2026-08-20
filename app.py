import os
import json
import html
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# НАЛАШТУВАННЯ
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
# ПРОФІЛЬ
# ============================================================

user_profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"]
)

profile_prefix = (
    "user1"
    if user_profile == "Я"
    else "user2"
)

EXCEL_FILE = (
    f"fitness_entries_{profile_prefix}.xlsx"
)

SETTINGS_FILE = (
    f"user_settings_{profile_prefix}.json"
)

HISTORY_FILE = (
    f"fitness_history_{profile_prefix}.json"
)


# ============================================================
# GEMINI
# ============================================================

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


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

.stApp {{
    background-image:
        linear-gradient(
            rgba(0,0,0,.78),
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
    max-width: 760px;
    padding-top: 1.2rem;
    padding-bottom: 4rem;
}}


/* ==========================================================
   КАРТКИ
   ========================================================== */

.card {{
    background: rgba(15,17,22,.88);
    border: 1px solid rgba(255,255,255,.13);
    border-radius: 20px;
    padding: 18px;
    margin: 12px 0;
    box-shadow: 0 10px 30px rgba(0,0,0,.28);
}}

.section-title {{
    font-size: 1.15rem;
    font-weight: 800;
    margin-bottom: 12px;
}}


/* ==========================================================
   КНОПКИ
   ========================================================== */

div[data-testid="stButton"] > button {{
    border-radius: 14px;
    min-height: 46px;

    font-weight: 700;

    border: 1px solid rgba(255,255,255,.16);

    background: rgba(35,37,48,.94);
    color: white;

    transition:
        transform .10s ease,
        filter .10s ease,
        background .10s ease;
}}

div[data-testid="stButton"] > button:hover {{
    border-color: rgba(255,255,255,.38);
    transform: translateY(-1px);
}}

div[data-testid="stButton"] > button:active {{
    transform: translateY(2px) scale(.97);
    filter: brightness(.70);
}}

div[data-testid="stButton"]
button[kind="primary"] {{
    background:
        linear-gradient(
            135deg,
            #36A2EB,
            #5b6cff
        );

    border-color: rgba(255,255,255,.22);
}}

div[data-testid="stButton"]
button[kind="primary"]:active {{
    background:
        linear-gradient(
            135deg,
            #267fb9,
            #4650c7
        );
}}


/* ==========================================================
   INPUT
   ========================================================== */

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-baseweb="select"] > div {{
    border-radius: 14px;
}}


/* ==========================================================
   КРУЖОК
   ========================================================== */

.donut-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    margin: 18px 0;
}}

.donut {{
    width: 220px;
    height: 220px;

    border-radius: 50%;

    display: flex;
    align-items: center;
    justify-content: center;

    box-shadow:
        0 0 25px rgba(0,0,0,.50),
        inset 0 0 12px rgba(255,255,255,.08);
}}

.donut-hole {{
    width: 150px;
    height: 150px;

    border-radius: 50%;

    background: #111319;

    display: flex;
    flex-direction: column;

    align-items: center;
    justify-content: center;

    text-align: center;

    color: white;

    padding: 12px;

    box-shadow:
        inset 0 0 20px rgba(0,0,0,.55);
}}

.donut-main {{
    font-size: 28px;
    font-weight: 900;
    line-height: 1.1;
}}

.donut-sub {{
    font-size: 12px;
    color: #aeb4c0;
    margin-top: 5px;
}}

.balance-deficit {{
    color: #57e389;
    font-weight: 900;
    font-size: 15px;
}}

.balance-surplus {{
    color: #ff6b6b;
    font-weight: 900;
    font-size: 15px;
}}


/* ==========================================================
   БЖВ
   ========================================================== */

.macro-grid {{
    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 8px;

    margin-top: 14px;
}}

.macro {{
    background: rgba(25,27,34,.94);

    border:
        1px solid rgba(255,255,255,.10);

    border-radius: 12px;

    padding: 10px 6px;

    text-align: center;

    font-size: 12px;
}}

.macro b {{
    display: block;

    font-size: 15px;

    margin-top: 3px;
}}


/* ==========================================================
   ВЛОГ
   ========================================================== */

.entry {{
    background: rgba(18,20,26,.94);

    border:
        1px solid rgba(255,255,255,.11);

    border-radius: 18px;

    padding: 15px;

    margin: 10px 0;

    width: 100%;

    box-sizing: border-box;
}}

.entry-head {{
    display: flex;

    justify-content: space-between;

    gap: 12px;

    align-items: flex-start;

    width: 100%;
}}

.entry-left {{
    flex: 1;
    min-width: 0;
}}

.entry-time {{
    font-weight: 900;
    font-size: 17px;
}}

.entry-desc {{
    font-size: 15px;

    font-weight: 700;

    margin-top: 7px;

    line-height: 1.55;

    white-space: pre-wrap;

    overflow: visible;

    text-overflow: clip;

    word-break: normal;

    overflow-wrap: anywhere;

    max-height: none;

    height: auto;

    display: block;

    width: 100%;
}}

.entry-kcal {{
    white-space: nowrap;

    font-weight: 900;

    font-size: 17px;

    flex-shrink: 0;
}}

.food-kcal {{
    color: #36A2EB;
}}

.burn-kcal {{
    color: #ff9f43;
}}

.bju {{
    display: flex;

    flex-wrap: wrap;

    gap: 7px;

    margin-top: 10px;
}}

.bju span {{
    background: rgba(255,255,255,.07);

    border-radius: 999px;

    padding: 5px 8px;

    font-size: 11px;
}}


/* ==========================================================
   ГОДИННИК
   ========================================================== */

.watch-card {{
    background: rgba(18,20,26,.92);

    border:
        1px solid rgba(255,255,255,.12);

    border-radius: 18px;

    padding: 15px;
}}

.small-muted {{
    color: #aeb4c0;
    font-size: 12px;
}}


/* ==========================================================
   FORM
   ========================================================== */

div[data-testid="stForm"] {{
    border:
        1px solid rgba(255,255,255,.12);

    border-radius: 18px;

    padding: 16px;

    background:
        rgba(18,20,26,.74);
}}


/* ==========================================================
   РОЗДІЛЮВАЧ
   ========================================================== */

.log-divider {{
    height: 1px;

    background:
        rgba(255,255,255,.08);

    margin: 12px 0;
}}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "watch_burned" not in st.session_state:
    st.session_state.watch_burned = 0.0

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False


# ============================================================
# КОЛОНКИ
# ============================================================

COLUMNS = [
    "ID",
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


# ============================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# ============================================================

def num(value):

    try:
        return float(value)
    except Exception:
        return 0.0


def safe_text(value):

    if value is None:
        return ""

    if isinstance(value, float):
        if pd.isna(value):
            return ""

    return str(value)


def new_id():

    return (
        datetime.now(
            LOCAL_TZ
        ).strftime(
            "%Y%m%d%H%M%S%f"
        )
    )


# ============================================================
# SETTINGS
# ============================================================

def load_settings():

    default = {
        "calories": 2000,
        "protein": 160,
        "fat": 70,
        "carbs": 180,

        "bmr_daily": 1850,

        "initial_weight": 89.0,
    }

    if not os.path.exists(
        SETTINGS_FILE
    ):
        return default

    try:

        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            saved = json.load(file)

        return {
            **default,
            **saved
        }

    except Exception:

        return default


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


# ============================================================
# DATA
# ============================================================

def load_data():

    empty = pd.DataFrame(
        columns=COLUMNS
    )

    if not os.path.exists(
        EXCEL_FILE
    ):
        return empty

    try:

        df = pd.read_excel(
            EXCEL_FILE
        )

    except Exception:

        return empty

    for column in COLUMNS:

        if column not in df.columns:

            if column in (
                "ID",
                "Дата",
                "Час",
                "Опис",
                "Тип"
            ):

                df[column] = ""

            else:

                df[column] = 0.0

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
        ).fillna(0.0)

    df["ID"] = (
        df["ID"]
        .astype(str)
    )

    df["Дата"] = (
        df["Дата"]
        .astype(str)
    )

    df["Час"] = (
        df["Час"]
        .astype(str)
        .str[:5]
    )

    df["Опис"] = (
        df["Опис"]
        .fillna("")
        .astype(str)
    )

    df["Тип"] = (
        df["Тип"]
        .fillna("")
        .astype(str)
    )

    # Якщо старий файл не мав ID
    for index in df.index:

        if (
            not df.loc[
                index,
                "ID"
            ]
            or df.loc[
                index,
                "ID"
            ] == "nan"
        ):

            df.loc[
                index,
                "ID"
            ] = new_id()

    return df


def save_data(df):

    df = df[
        COLUMNS
    ].copy()

    df.to_excel(
        EXCEL_FILE,
        index=False
    )


# ============================================================
# HISTORY
# ============================================================

def load_history():

    if not os.path.exists(
        HISTORY_FILE
    ):
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(
            data,
            list
        ):

            return data

    except Exception:
        pass

    return []


def save_history(history):

    history = history[-10:]

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2
        )


def push_history(action):

    history = load_history()

    history.append(
        action
    )

    save_history(
        history
    )


def undo_last():

    history = load_history()

    if not history:
        return None

    action = history.pop()

    save_history(
        history
    )

    return action


# ============================================================
# GEMINI
# ============================================================

def parse_gemini_response(text):

    text = (
        text or ""
    ).strip()

    if text.startswith(
        "```"
    ):

        text = (
            text
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

    data = json.loads(
        text
    )

    return {
        "food_description":
            safe_text(
                data.get(
                    "food_description",
                    "Запис"
                )
            ),

        "kcal_burned":
            num(
                data.get(
                    "kcal_burned",
                    0
                )
            ),

        "total_consumed_kcal":
            num(
                data.get(
                    "total_consumed_kcal",
                    0
                )
            ),

        "total_protein":
            num(
                data.get(
                    "total_protein",
                    0
                )
            ),

        "total_fat":
            num(
                data.get(
                    "total_fat",
                    0
                )
            ),

        "total_carbs":
            num(
                data.get(
                    "total_carbs",
                    0
                )
            ),
    }


def analyze_text(text):

    api_key = (
        st.secrets.get(
            "GEMINI_API_KEY",
            None
        )
        or os.environ.get(
            "GEMINI_API_KEY"
        )
    )

    if not api_key:

        raise RuntimeError(
            "Не знайдено GEMINI_API_KEY."
        )

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
Ти точний щоденник харчування.

Проаналізуй цей запис:

{text}

Поверни ТІЛЬКИ JSON.

Формат:

{{
  "food_description": "...",
  "kcal_burned": 0,
  "total_consumed_kcal": 0,
  "total_protein": 0,
  "total_fat": 0,
  "total_carbs": 0
}}

ПРАВИЛА:

Якщо це їжа:

- kcal_burned = 0
- total_consumed_kcal = калорії всієї їжі
- порахуй БЖВ

Якщо це тренування:

- total_consumed_kcal = 0
- kcal_burned = спалені калорії

ОСОБЛИВО ВАЖЛИВО:

food_description має містити ПОВНИЙ список
усіх продуктів.

Кожен продукт пиши окремим рядком.

Наприклад:

🍗 Курка 300 г — 495 ккал
🍚 Рис 200 г — 260 ккал
🥗 Салат — 120 ккал
🥚 2 яйця — 140 ккал

Разом — 1015 ккал

Не скорочуй список продуктів.

Не використовуй "..." замість продуктів.

Не пиши довгі пояснення.

Якщо користувач ввів кілька продуктів,
покажи кожен продукт окремо.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return parse_gemini_response(
        response.text
    )


# ============================================================
# ВАГА
# ============================================================

def calculate_weight(
    df,
    settings
):

    initial_weight = num(
        settings.get(
            "initial_weight",
            89.0
        )
    )

    bmr_daily = num(
        settings.get(
            "bmr_daily",
            1850
        )
    )

    if df.empty:

        return initial_weight

    today = datetime.now(
        LOCAL_TZ
    ).strftime(
        "%Y-%m-%d"
    )

    now = datetime.now(
        LOCAL_TZ
    )

    total_balance = 0.0

    for date_value in (
        df["Дата"]
        .astype(str)
        .unique()
    ):

        day = df[
            df["Дата"].astype(str)
            == date_value
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
                + now.minute / 60
            )

            base_burn = (
                bmr_daily / 24
            ) * hours

        else:

            base_burn = bmr_daily

        total_balance += (
            base_burn
            + exercise
            - eaten
        )

    return (
        initial_weight
        - total_balance / 7700
    )


# ============================================================
# ЗАВАНТАЖЕННЯ
# ============================================================

settings = load_settings()

df = load_data()


# ============================================================
# HEADER
# ============================================================

current_weight = calculate_weight(
    df,
    settings
)

st.title(
    f"⚖️ Фітнес — {user_profile}"
)

st.caption(
    f"Поточна вага: "
    f"**{current_weight:.1f} кг**"
)


# ============================================================
# ВВІД
# ============================================================

st.markdown(
    """
<div class="card">
<div class="section-title">
📝 Додати у влог
</div>
""",
    unsafe_allow_html=True
)

with st.form(
    "add_entry_form",
    clear_on_submit=True
):

    user_input = st.text_area(
        "Їжа або тренування",
        placeholder=(
            "Наприклад:\n"
            "300 г курки\n"
            "200 г рису\n"
            "салат"
        ),
        height=110
    )

    submit = st.form_submit_button(
        "✅ Додати у влог",
        type="primary",
        use_container_width=True
    )


if submit:

    if not user_input.strip():

        st.warning(
            "Введи їжу або тренування."
        )

    else:

        try:

            result = analyze_text(
                user_input.strip()
            )

            now = datetime.now(
                LOCAL_TZ
            )

            is_training = (
                result["kcal_burned"]
                > 0
                and
                result[
                    "total_consumed_kcal"
                ]
                <= 0
            )

            new_entry = {
                "ID": new_id(),

                "Дата":
                    now.strftime(
                        "%Y-%m-%d"
                    ),

                "Час":
                    now.strftime(
                        "%H:%M"
                    ),

                "Опис":
                    result[
                        "food_description"
                    ],

                "Тип":
                    (
                        "Тренування"
                        if is_training
                        else "Їжа"
                    ),

                "Спожито":
                    (
                        0
                        if is_training
                        else result[
                            "total_consumed_kcal"
                        ]
                    ),

                "Спалено":
                    (
                        result[
                            "kcal_burned"
                        ]
                        if is_training
                        else 0
                    ),

                "Білки":
                    (
                        0
                        if is_training
                        else result[
                            "total_protein"
                        ]
                    ),

                "Жири":
                    (
                        0
                        if is_training
                        else result[
                            "total_fat"
                        ]
                    ),

                "Вуглеводи":
                    (
                        0
                        if is_training
                        else result[
                            "total_carbs"
                        ]
                    ),
            }

            # Зберігаємо саме цей запис
            # для правильного Undo.
            push_history({
                "action": "add",
                "row": new_entry
            })

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [new_entry]
                    )
                ],
                ignore_index=True
            )

            save_data(df)

            st.rerun()

        except Exception as error:

            st.error(
                f"Помилка: {error}"
            )


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# ГОДИННИК
# ============================================================

st.markdown(
    """
<div class="card">
<div class="section-title">
⌚ Калорії з годинника
</div>
""",
    unsafe_allow_html=True
)

watch_value = st.number_input(
    "Спалено сьогодні, ккал",
    min_value=0.0,
    value=float(
        st.session_state.watch_burned
    ),
    step=10.0,
    key="watch_input"
)

if st.button(
    "⌚ Оновити",
    type="primary",
    use_container_width=True
):

    # НЕ додаємо старе значення.
    # Повністю ЗАМІНЮЄМО його.
    st.session_state.watch_burned = (
        float(watch_value)
    )

    st.rerun()


st.markdown(
    f"""
<div class="small-muted">
З годинника зараз:
<b>{st.session_state.watch_burned:.0f} ккал</b>
<br>
Нове значення повністю замінює попереднє.
</div>
""",
    unsafe_allow_html=True
)

st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# ДАТИ
# ============================================================

today = datetime.now(
    LOCAL_TZ
).strftime(
    "%Y-%m-%d"
)

dates = [today]

if not df.empty:

    for date_value in sorted(
        df["Дата"]
        .astype(str)
        .unique(),
        reverse=True
    ):

        if date_value not in dates:

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

button_col1, button_col2 = (
    st.columns(2)
)


with button_col1:

    if st.button(
        "⚙️ Редактор",
        use_container_width=True
    ):

        st.session_state.edit_mode = (
            not st.session_state.edit_mode
        )

        st.rerun()


with button_col2:

    if st.button(
        "↩️ Відмінити",
        use_container_width=True
    ):

        action = undo_last()

        if action is None:

            st.info(
                "Немає дій для відміни."
            )

        else:

            action_type = action.get(
                "action"
            )

            # ------------------------------------------------
            # UNDO ADD
            # ------------------------------------------------

            if action_type == "add":

                row = action.get(
                    "row"
                )

                if row:

                    row_id = str(
                        row.get(
                            "ID",
                            ""
                        )
                    )

                    df = df[
                        df["ID"].astype(str)
                        != row_id
                    ].copy()

                    save_data(df)

            # ------------------------------------------------
            # UNDO DELETE
            # ------------------------------------------------

            elif action_type == "delete":

                rows = action.get(
                    "rows",
                    []
                )

                if rows:

                    restore_df = (
                        pd.DataFrame(rows)
                    )

                    df = pd.concat(
                        [
                            df,
                            restore_df
                        ],
                        ignore_index=True
                    )

                    save_data(df)

            # ------------------------------------------------
            # UNDO EDIT
            # ------------------------------------------------

            elif action_type == "edit":

                row_id = str(
                    action.get(
                        "row_id",
                        ""
                    )
                )

                old_row = action.get(
                    "old_row"
                )

                if (
                    row_id
                    and old_row
                ):

                    mask = (
                        df["ID"].astype(str)
                        == row_id
                    )

                    if mask.any():

                        index = df[
                            mask
                        ].index[0]

                        for column in COLUMNS:

                            if column in old_row:

                                df.loc[
                                    index,
                                    column
                                ] = old_row[
                                    column
                                ]

                        save_data(df)

        st.rerun()


# ============================================================
# РЕДАКТОР НАЛАШТУВАНЬ
# ============================================================

if st.session_state.edit_mode:

    st.markdown(
        """
<div class="card">
<div class="section-title">
⚙️ Редактор
</div>
""",
        unsafe_allow_html=True
    )

    calories_target = st.number_input(
        "Добова кількість калорій",
        min_value=0,
        value=int(
            settings["calories"]
        ),
        step=10
    )

    protein_target = st.number_input(
        "Білки, г",
        min_value=0,
        value=int(
            settings["protein"]
        ),
        step=5
    )

    fat_target = st.number_input(
        "Жири, г",
        min_value=0,
        value=int(
            settings["fat"]
        ),
        step=5
    )

    carbs_target = st.number_input(
        "Вуглеводи, г",
        min_value=0,
        value=int(
            settings["carbs"]
        ),
        step=5
    )

    bmr_target = st.number_input(
        "Базова добова витрата, ккал",
        min_value=0,
        value=int(
            settings["bmr_daily"]
        ),
        step=10
    )

    initial_weight = st.number_input(
        "Початкова вага, кг",
        min_value=0.0,
        value=float(
            settings["initial_weight"]
        ),
        step=0.1
    )

    if st.button(
        "💾 Зберегти",
        type="primary",
        use_container_width=True
    ):

        settings["calories"] = int(
            calories_target
        )

        settings["protein"] = int(
            protein_target
        )

        settings["fat"] = int(
            fat_target
        )

        settings["carbs"] = int(
            carbs_target
        )

        settings["bmr_daily"] = int(
            bmr_target
        )

        settings["initial_weight"] = (
            float(initial_weight)
        )

        save_settings(
            settings
        )

        st.session_state.edit_mode = (
            False
        )

        st.rerun()

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# ============================================================
# ДАНІ ДНЯ
# ============================================================

day_df = df[
    df["Дата"].astype(str)
    == selected_date
].copy()


# ============================================================
# СТАТИСТИКА
# ============================================================

if day_df.empty:

    eaten = 0.0
    exercise_burned = 0.0
    protein = 0.0
    fat = 0.0
    carbs = 0.0

else:

    eaten = float(
        day_df["Спожито"].sum()
    )

    exercise_burned = float(
        day_df["Спалено"].sum()
    )

    protein = float(
        day_df["Білки"].sum()
    )

    fat = float(
        day_df["Жири"].sum()
    )

    carbs = float(
        day_df["Вуглеводи"].sum()
    )


# ============================================================
# БАЗОВА ВИТРАТА
# ============================================================

if selected_date == today:

    now = datetime.now(
        LOCAL_TZ
    )

    hours_passed = (
        now.hour
        + now.minute / 60
    )

    base_burn = (
        settings["bmr_daily"]
        / 24
    ) * hours_passed

else:

    base_burn = (
        settings["bmr_daily"]
    )


# ============================================================
# ГОДИННИК
# ============================================================

if selected_date == today:

    watch_burned = float(
        st.session_state.watch_burned
    )

else:

    watch_burned = 0.0


# ============================================================
# ЗАГАЛЬНО СПАЛЕНО
# ============================================================

total_burned = (
    base_burn
    + watch_burned
    + exercise_burned
)


# ============================================================
# ДЕФІЦИТ / ПРОФІЦИТ
# ============================================================

balance = (
    total_burned
    - eaten
)


if balance >= 0:

    balance_text = (
        f"Дефіцит {abs(balance):.0f} ккал"
    )

    balance_class = (
        "balance-deficit"
    )

else:

    balance_text = (
        f"Профіцит {abs(balance):.0f} ккал"
    )

    balance_class = (
        "balance-surplus"
    )


# ============================================================
# БЖВ КРУЖОК
# ============================================================

macro_total = (
    protein
    + fat
    + carbs
)


if macro_total > 0:

    protein_angle = (
        protein
        / macro_total
        * 360
    )

    fat_angle = (
        protein_angle
        + fat
        / macro_total
        * 360
    )

    carbs_angle = (
        fat_angle
        + carbs
        / macro_total
        * 360
    )

    donut_gradient = (
        "conic-gradient("
        "#36A2EB 0deg "
        f"{protein_angle:.2f}deg, "

        "#FFCE56 "
        f"{protein_angle:.2f}deg "
        f"{fat_angle:.2f}deg, "

        "#FF6384 "
        f"{fat_angle:.2f}deg "
        f"{carbs_angle:.2f}deg, "

        "rgba(255,255,255,.08) "
        f"{carbs_angle:.2f}deg "
        "360deg"
        ")"
    )

else:

    donut_gradient = (
        "conic-gradient("
        "rgba(255,255,255,.10) "
        "0deg 360deg"
        ")"
    )


# ============================================================
# ГОЛОВНИЙ КРУЖОК
# ============================================================

st.markdown(
    f"""
<div class="card">

<div class="section-title">
📊 {html.escape(selected_date)}
&nbsp;·&nbsp;
⚖️ {current_weight:.1f} кг
</div>

<div class="donut-wrap">

<div
    class="donut"
    style="background:{donut_gradient};"
>

<div class="donut-hole">

<div class="{balance_class}">
{balance_text}
</div>

<div class="donut-main">
{eaten:.0f}
</div>

<div class="donut-sub">
з {settings["calories"]:.0f} ккал
</div>

</div>

</div>


<div class="macro-grid">

<div class="macro">
🥩 Білки
<b>
{protein:.0f}
/
{settings["protein"]:.0f}
г
</b>
</div>

<div class="macro">
🥑 Жири
<b>
{fat:.0f}
/
{settings["fat"]:.0f}
г
</b>
</div>

<div class="macro">
🍞 Вуглеводи
<b>
{carbs:.0f}
/
{settings["carbs"]:.0f}
г
</b>
</div>

</div>

</div>

</div>
""",
    unsafe_allow_html=True
)


# ============================================================
# ВЛОГ
# ============================================================

st.markdown(
    """
<div class="card">
<div class="section-title">
📝 Влог
</div>
""",
    unsafe_allow_html=True
)


if day_df.empty:

    st.info(
        "За цей день записів немає."
    )

else:

    # Найновіші зверху
    for row_index in reversed(
        list(day_df.index)
    ):

        row = day_df.loc[
            row_index
        ]

        entry_id = str(
            row["ID"]
        )

        entry_type = str(
            row["Тип"]
        )

        is_training = (
            entry_type
            == "Тренування"
        )

        icon = (
            "💪"
            if is_training
            else "🍽️"
        )

        description = safe_text(
            row["Опис"]
        )

        # ----------------------------------------------------
        # ВАЖЛИВО:
        # HTML ESCAPE НЕ ДАЄ ЗЛАМАТИ КАРТКУ.
        # ПЕРЕНОСИ РЯДКІВ ЗБЕРІГАЮТЬСЯ.
        # ----------------------------------------------------

        safe_description = html.escape(
            description,
            quote=False
        )

        safe_description = (
            safe_description
            .replace(
                "\r\n",
                "\n"
            )
            .replace(
                "\r",
                "\n"
            )
            .replace(
                "\n",
                "<br>"
            )
        )

        if is_training:

            kcal = float(
                row["Спалено"]
            )

            kcal_class = (
                "burn-kcal"
            )

        else:

            kcal = float(
                row["Спожито"]
            )

            kcal_class = (
                "food-kcal"
            )


        # ----------------------------------------------------
        # БЖВ
        # ----------------------------------------------------

        if is_training:

            bju_html = ""

        else:

            bju_html = f"""
<div class="bju">

<span>
🔥 {float(row["Спожито"]):.0f} ккал
</span>

<span>
🥩 {float(row["Білки"]):.1f} г
</span>

<span>
🥑 {float(row["Жири"]):.1f} г
</span>

<span>
🍞 {float(row["Вуглеводи"]):.1f} г
</span>

</div>
"""


        # ----------------------------------------------------
        # КАРТКА ЗАПИСУ
        # ----------------------------------------------------

        st.markdown(
            f"""
<div class="entry">

<div class="entry-head">

<div class="entry-left">

<div class="entry-time">
{html.escape(str(row["Час"])[:5])}
&nbsp;{icon}
</div>

<div class="entry-desc">
{safe_description}
</div>

</div>

<div class="entry-kcal {kcal_class}">
{kcal:.0f} ккал
</div>

</div>

{bju_html}

</div>
""",
            unsafe_allow_html=True
        )


        # ----------------------------------------------------
        # КНОПКИ
        # ----------------------------------------------------

        edit_col, delete_col = (
            st.columns(2)
        )


        with edit_col:

            if st.button(
                "✏️ Редагувати",
                key=f"edit_{entry_id}",
                use_container_width=True
            ):

                st.session_state[
                    f"editing_{entry_id}"
                ] = True

                st.rerun()


        with delete_col:

            if st.button(
                "🗑️ Видалити",
                key=f"delete_{entry_id}",
                use_container_width=True
            ):

                # Повний старий рядок
                old_row = (
                    row.to_dict()
                )

                push_history({
                    "action": "delete",
                    "rows": [
                        old_row
                    ]
                })

                df = df[
                    df["ID"].astype(str)
                    != entry_id
                ].copy()

                save_data(df)

                st.rerun()


        # ----------------------------------------------------
        # РЕДАГУВАННЯ
        # ----------------------------------------------------

        if st.session_state.get(
            f"editing_{entry_id}",
            False
        ):

            st.markdown(
                "<div class='log-divider'></div>",
                unsafe_allow_html=True
            )

            with st.form(
                f"edit_form_{entry_id}"
            ):

                st.markdown(
                    "### ✏️ Редагування запису"
                )

                edited_description = (
                    st.text_area(
                        "Опис",
                        value=description,
                        height=150
                    )
                )

                edited_consumed = (
                    st.number_input(
                        "З'їдено, ккал",
                        min_value=0.0,
                        value=float(
                            row["Спожито"]
                        ),
                        step=1.0
                    )
                )

                edited_burned = (
                    st.number_input(
                        "Спалено, ккал",
                        min_value=0.0,
                        value=float(
                            row["Спалено"]
                        ),
                        step=1.0
                    )
                )

                edited_protein = (
                    st.number_input(
                        "Білки, г",
                        min_value=0.0,
                        value=float(
                            row["Білки"]
                        ),
                        step=0.1
                    )
                )

                edited_fat = (
                    st.number_input(
                        "Жири, г",
                        min_value=0.0,
                        value=float(
                            row["Жири"]
                        ),
                        step=0.1
                    )

                edited_carbs = (
                    st.number_input(
                        "Вуглеводи, г",
                        min_value=0.0,
                        value=float(
                            row["Вуглеводи"]
                        ),
                        step=0.1
                    )
                )

                save_edit = (
                    st.form_submit_button(
                        "💾 Зберегти зміни",
                        type="primary",
                        use_container_width=True
                    )
                )


                if save_edit:

                    # Старий рядок для Undo
                    push_history({
                        "action": "edit",
                        "row_id": entry_id,
                        "old_row":
                            row.to_dict()
                    })


                    index = df[
                        df["ID"].astype(str)
                        == entry_id
                    ].index[0]


                    df.loc[
                        index,
                        "Опис"
                    ] = edited_description


                    if is_training:

                        df.loc[
                            index,
                            "Спожито"
                        ] = 0.0

                        df.loc[
                            index,
                            "Спалено"
                        ] = edited_burned

                        df.loc[
                            index,
                            "Білки"
                        ] = 0.0

                        df.loc[
                            index,
                            "Жири"
                        ] = 0.0

                        df.loc[
                            index,
                            "Вуглеводи"
                        ] = 0.0

                    else:

                        df.loc[
                            index,
                            "Спожито"
                        ] = edited_consumed

                        df.loc[
                            index,
                            "Спалено"
                        ] = 0.0

                        df.loc[
                            index,
                            "Білки"
                        ] = edited_protein

                        df.loc[
                            index,
                            "Жири"
                        ] = edited_fat

                        df.loc[
                            index,
                            "Вуглеводи"
                        ] = edited_carbs


                    save_data(df)

                    st.session_state[
                        f"editing_{entry_id}"
                    ] = False

                    st.rerun()


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# ПІДСУМОК
# ============================================================

st.markdown(
    f"""
<div class="card">

<div class="small-muted">

🔥 З'їдено:
<b>{eaten:.0f} ккал</b>

&nbsp;&nbsp;·&nbsp;&nbsp;

⌚ Годинник:
<b>{watch_burned:.0f} ккал</b>

&nbsp;&nbsp;·&nbsp;&nbsp;

💪 Тренування:
<b>{exercise_burned:.0f} ккал</b>

<br><br>

⚡ Базова витрата:
<b>{base_burn:.0f} ккал</b>

&nbsp;&nbsp;·&nbsp;&nbsp;

🔥 Загальна витрата:
<b>{total_burned:.0f} ккал</b>

<br><br>

⚖️ Розрахункова вага:
<b>{current_weight:.1f} кг</b>

</div>

</div>
""",
    unsafe_allow_html=True
)
