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
    page_icon="⚖️",
    layout="centered",
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

profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"],
)

profile_id = "user1" if profile == "Я" else "user2"
sheet_tab = "Я" if profile == "Я" else "Дружина"


# ============================================================
# GOOGLE SHEETS
# ============================================================

SPREADSHEET_ID = "1Blo5R_ZDOeAgVkRwXDfY1Wpw12QVrZMVUEfmY_Jlk_U"

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


@st.cache_resource(show_spinner=False)
def get_gspread_client():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    if "gcp_service_account" in st.secrets:

        info = dict(
            st.secrets["gcp_service_account"]
        )

        credentials = Credentials.from_service_account_info(
            info,
            scopes=scopes,
        )

    elif os.path.exists("service_account.json"):

        credentials = Credentials.from_service_account_file(
            "service_account.json",
            scopes=scopes,
        )

    else:

        raise RuntimeError(
            "Не знайдено gcp_service_account у Streamlit Secrets "
            "і немає service_account.json."
        )

    return gspread.authorize(credentials)


@st.cache_resource(show_spinner=False)
def get_worksheet(tab_name):

    client = get_gspread_client()

    spreadsheet = client.open_by_key(
        SPREADSHEET_ID
    )

    try:

        ws = spreadsheet.worksheet(
            tab_name
        )

    except gspread.exceptions.WorksheetNotFound:

        ws = spreadsheet.add_worksheet(
            title=tab_name,
            rows=1000,
            cols=len(COLUMNS),
        )

    values = ws.get_all_values()

    if not values:

        ws.append_row(
            COLUMNS,
            value_input_option="USER_ENTERED",
        )

    elif values[0][:len(COLUMNS)] != COLUMNS:

        if len(values[0]) < len(COLUMNS):

            ws.update(
                "A1:I1",
                [COLUMNS],
                value_input_option="USER_ENTERED",
            )

    return ws


# ============================================================
# ФОН + CSS
# ============================================================

BACKGROUND_IMAGE = (
    "https://i.postimg.cc/kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)


st.markdown(
    f"""
    <style>

    .stApp {{
        background-image:
            linear-gradient(
                rgba(0,0,0,.72),
                rgba(0,0,0,.90)
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


    /* ========================================================
       КНОПКИ
       ======================================================== */

    div.stButton > button {{

        min-height: 46px !important;

        border-radius: 14px !important;

        border:
            1px solid
            rgba(255,255,255,.14)
            !important;

        background:
            linear-gradient(
                135deg,
                rgba(45,45,53,.98),
                rgba(18,18,23,.98)
            )
            !important;

        color: #fff !important;

        font-weight: 700 !important;

        box-shadow:
            0 7px 20px
            rgba(0,0,0,.35);

        transition:
            transform .10s ease,
            box-shadow .10s ease,
            filter .10s ease;
    }}


    div.stButton > button:hover {{

        border-color:
            rgba(54,162,235,.65)
            !important;

        box-shadow:
            0 10px 28px
            rgba(0,0,0,.45);
    }}


    div.stButton > button:active {{

        transform:
            translateY(2px)
            scale(.985)
            !important;

        box-shadow:
            inset 0 3px 9px
            rgba(0,0,0,.65)
            !important;

        filter: brightness(.82);
    }}


    /* ========================================================
       INPUTS
       ======================================================== */

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{

        border-radius: 12px !important;

        background:
            rgba(18,18,22,.94)
            !important;

        color: #fff !important;
    }}


    div[data-testid="stVerticalBlockBorderWrapper"] {{

        background:
            rgba(15,17,22,.78);

        border-radius: 14px;
    }}


    /* ========================================================
       СТАРІ CSS-КЛАСИ — ЗАЛИШАЄМО ДЛЯ СУМІСНОСТІ
       ======================================================== */

    .log-card {{

        padding: 14px;

        border:
            1px solid
            rgba(255,255,255,.13);

        border-radius: 16px;

        background:
            rgba(10,12,16,.72);

        margin-bottom: 10px;
    }}


    .log-head {{

        display: flex;

        justify-content: space-between;

        gap: 12px;

        align-items: flex-start;
    }}


    .log-title {{

        font-size: 17px;

        font-weight: 800;

        line-height: 1.35;

        word-break: break-word;
    }}


    .log-kcal {{

        white-space: nowrap;

        font-size: 16px;

        font-weight: 900;
    }}


    .log-sub {{

        margin-top: 8px;

        color: #bfc3cc;

        font-size: 12px;
    }}


    .balance-card {{

        margin: 10px 0 16px;

        padding: 16px;

        border-radius: 18px;

        background:
            rgba(15,17,22,.84);

        border:
            1px solid
            rgba(255,255,255,.12);

        text-align: center;
    }}


    .balance-main {{

        font-size: 26px;

        font-weight: 900;
    }}


    .balance-sub {{

        color: #b8bcc5;

        font-size: 13px;

        margin-top: 6px;
    }}


    .deficit {{
        color: #35D07F;
    }}

    .surplus {{
        color: #FF6262;
    }}

    .neutral {{
        color: #FFD166;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

for key, default in {

    "settings_open": False,

    "editor_open": False,

    "undo_stack": [],

    "input_nonce": 0,

}.items():

    if key not in st.session_state:

        st.session_state[key] = default


# ============================================================
# GEMINI
# ============================================================

try:

    api_key = (
        st.secrets.get("GEMINI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )

except Exception:

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


GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

SETTINGS_FILE = (
    f"user_settings_{profile_id}.json"
)

TRASH_FILE = (
    f"fitness_trash_{profile_id}.json"
)


DEFAULT_SETTINGS = {

    "calories": 2000,

    "bmr_daily": 1850,

    "initial_weight": 89.0,

    "include_exercise_in_deficit": True,

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
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        result = DEFAULT_SETTINGS.copy()

        result.update(data)

        return result

    except Exception:

        return DEFAULT_SETTINGS.copy()


def save_settings(data):

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


settings = load_settings()


# ============================================================
# DATA HELPERS
# ============================================================

def empty_dataframe():

    return pd.DataFrame(
        columns=COLUMNS
    )


def clean_number(value):

    try:

        if value is None:

            return 0.0

        if (
            isinstance(value, float)
            and pd.isna(value)
        ):

            return 0.0

        return float(value)

    except Exception:

        try:

            return float(
                str(value)
                .replace(",", ".")
                .strip()
            )

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

    return str(value).strip()


def normalize_dataframe(df):

    if df is None or df.empty:

        return empty_dataframe()

    df = df.copy()

    for col in COLUMNS:

        if col not in df.columns:

            if col in {
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи",
            }:

                df[col] = 0

            elif col == "Тип":

                df[col] = "Їжа"

            else:

                df[col] = ""

    df = df[COLUMNS].copy()

    for col in [
        "Спожито",
        "Спалено",
        "Білки",
        "Жири",
        "Вуглеводи",
    ]:

        df[col] = (
            pd.to_numeric(
                df[col],
                errors="coerce",
            )
            .fillna(0.0)
        )

    for col in [
        "Дата",
        "Час",
        "Опис",
        "Тип",
    ]:

        df[col] = df[col].map(
            clean_text
        )

    return df


# ============================================================
# GOOGLE SHEETS DATA
# ============================================================

def load_data():

    try:

        ws = get_worksheet(
            sheet_tab
        )

        rows = ws.get_all_records()

        if rows:

            return normalize_dataframe(
                pd.DataFrame(rows)
            )

        return empty_dataframe()

    except Exception as e:

        st.error(
            f"❌ Не вдалося прочитати "
            f"Google Sheets: {e}"
        )

        return empty_dataframe()


def sheet_row_values(row):

    return [

        clean_text(
            row.get("Дата", "")
        ),

        clean_text(
            row.get("Час", "")
        ),

        clean_text(
            row.get("Опис", "")
        ),

        clean_text(
            row.get("Тип", "Їжа")
        ) or "Їжа",

        clean_number(
            row.get("Спожито", 0)
        ),

        clean_number(
            row.get("Спалено", 0)
        ),

        clean_number(
            row.get("Білки", 0)
        ),

        clean_number(
            row.get("Жири", 0)
        ),

        clean_number(
            row.get("Вуглеводи", 0)
        ),

    ]


def append_entry(row):

    ws = get_worksheet(
        sheet_tab
    )

    ws.append_row(
        sheet_row_values(row),
        value_input_option="USER_ENTERED",
    )


def delete_last_entry():

    ws = get_worksheet(
        sheet_tab
    )

    values = ws.get_all_values()

    if len(values) <= 1:

        return None

    last = values[-1]

    ws.delete_rows(
        len(values)
    )

    return dict(
        zip(
            COLUMNS,
            (
                last
                + [""] * len(COLUMNS)
            )[:len(COLUMNS)],
        )
    )


def replace_all_data(df):

    ws = get_worksheet(
        sheet_tab
    )

    clean = normalize_dataframe(
        df
    )

    ws.clear()

    ws.update(
        "A1:I1",
        [COLUMNS],
        value_input_option="USER_ENTERED",
    )

    if not clean.empty:

        values = [
            sheet_row_values(row)
            for _, row
            in clean.iterrows()
        ]

        ws.update(
            f"A2:I{len(values)+1}",
            values,
            value_input_option="USER_ENTERED",
        )


# ============================================================
# ВАГА
# ============================================================

def calculate_current_weight(
    dataframe,
    profile_settings,
):

    initial_weight = clean_number(
        profile_settings.get(
            "initial_weight",
            89.0,
        )
    )

    bmr_daily = clean_number(
        profile_settings.get(
            "bmr_daily",
            1850,
        )
    )

    if dataframe.empty:

        return initial_weight

    work = normalize_dataframe(
        dataframe
    )

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    now = datetime.now(
        LOCAL_TZ
    )

    total_balance = 0.0

    for date_value in work[
        "Дата"
    ].unique():

        day = work[
            work["Дата"]
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

            bmr = (
                bmr_daily / 24
            ) * hours

        else:

            bmr = bmr_daily

        burned = (
            bmr + exercise
            if profile_settings.get(
                "include_exercise_in_deficit",
                True,
            )
            else bmr
        )

        total_balance += (
            burned - eaten
        )

    return max(
        0.0,
        initial_weight
        - total_balance / 7700.0,
    )


# ============================================================
# GEMINI JSON
# ============================================================

def parse_json_response(text):

    raw = (
        text or ""
    ).strip()

    if raw.startswith("```"):

        raw = (
            raw
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    return json.loads(raw)


def analyze_entry(user_text):

    prompt = """

Ти фітнес-трекер.

Проаналізуй один запис користувача.

Визнач, це Їжа або Тренування.

Для Їжа:
- оцінюй спожиті ккал;
- оцінюй білки;
- оцінюй жири;
- оцінюй вуглеводи.

Для Тренування:
- оцінюй спалені ккал;
- спожиті ккал = 0;
- БЖВ = 0.

Не вигадуй складні назви.
Опис має бути коротким і зрозумілим.

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

Усі числа — числа, не рядки.

"""

    response = client.models.generate_content(

        model=GEMINI_MODEL,

        contents=(
            prompt
            + "\n\nЗапис користувача:\n"
            + user_text.strip()
        ),

        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )

    result = parse_json_response(
        response.text
    )

    entry_type = clean_text(
        result.get(
            "type",
            "Їжа",
        )
    )

    if entry_type not in {
        "Їжа",
        "Тренування",
    }:

        entry_type = "Їжа"

    consumed = max(
        0.0,
        clean_number(
            result.get(
                "consumed_kcal",
                0,
            )
        ),
    )

    burned = max(
        0.0,
        clean_number(
            result.get(
                "burned_kcal",
                0,
            )
        ),
    )

    protein = max(
        0.0,
        clean_number(
            result.get(
                "protein",
                0,
            )
        ),
    )

    fat = max(
        0.0,
        clean_number(
            result.get(
                "fat",
                0,
            )
        ),
    )

    carbs = max(
        0.0,
        clean_number(
            result.get(
                "carbs",
                0,
            )
        ),
    )

    if entry_type == "Тренування":

        consumed = 0.0

        protein = 0.0
        fat = 0.0
        carbs = 0.0

    else:

        burned = 0.0

    return {

        "description": (
            clean_text(
                result.get(
                    "description",
                    "",
                )
            )
            or user_text.strip()
        ),

        "type": entry_type,

        "consumed_kcal": consumed,

        "burned_kcal": burned,

        "protein": protein,

        "fat": fat,

        "carbs": carbs,
    }


# ============================================================
# ЗАГОЛОВОК
# ============================================================

df = load_data()

current_weight = calculate_current_weight(
    df,
    settings,
)


st.title(
    f"⚖️ Калорійний трекер — {profile}"
)


st.markdown(
    f"""
### 📅 {datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')}
### ⚖️ Поточна вага: ~{current_weight:.1f} кг
"""
)


# ============================================================
# ВВІД ЇЖІ / ТРЕНУВАННЯ
# ============================================================

input_key = (
    f"food_input_"
    f"{st.session_state.input_nonce}"
)


user_input = st.text_input(

    "🍽️ Влог",

    placeholder=(
        "Наприклад: "
        "плов з куркою 350 г, "
        "чорний хліб 2 шматки"
    ),

    key=input_key,
)


if st.button(
    "✅ ОК",
    type="primary",
    use_container_width=True,
):

    if not user_input.strip():

        st.warning(
            "Введи продукт або тренування."
        )

    else:

        try:

            result = analyze_entry(
                user_input
            )

            now = datetime.now(
                LOCAL_TZ
            )

            row = {

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
                        "description"
                    ],

                "Тип":
                    result[
                        "type"
                    ],

                "Спожито":
                    result[
                        "consumed_kcal"
                    ],

                "Спалено":
                    result[
                        "burned_kcal"
                    ],

                "Білки":
                    result[
                        "protein"
                    ],

                "Жири":
                    result[
                        "fat"
                    ],

                "Вуглеводи":
                    result[
                        "carbs"
                    ],
            }

            append_entry(row)

            st.session_state.undo_stack.append(
                {
                    "action": "add",
                    "row": row,
                }
            )

            st.session_state.undo_stack = (
                st.session_state.undo_stack[
                    -10:
                ]
            )

            # Очищаємо поле після успішного запису.
            st.session_state.input_nonce += 1

            st.success(
                "✅ Запис збережено "
                "в Google Sheets."
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"❌ Не вдалося додати запис: {e}"
            )


# ============================================================
# ДЕНЬ
# ============================================================

today = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")


dates = [today]


if not df.empty:

    for d in sorted(
        df["Дата"].unique(),
        reverse=True,
    ):

        d = clean_text(d)

        if d and d not in dates:

            dates.append(d)


selected_date = st.selectbox(
    "📅 День",
    dates,
)


# ============================================================
# КНОПКИ КЕРУВАННЯ
# ============================================================

col1, col2, col3 = st.columns(3)


with col1:

    undo_clicked = st.button(
        "↩️ Відмінити",
        use_container_width=True,
    )


with col2:

    delete_clicked = st.button(
        "🗑️ Видалити останній",
        use_container_width=True,
    )


with col3:

    settings_clicked = st.button(
        "✏️ Редактор",
        use_container_width=True,
    )


# ============================================================
# UNDO
# ============================================================

def remove_matching_last_row(row):

    ws = get_worksheet(
        sheet_tab
    )

    values = ws.get_all_values()

    if len(values) <= 1:

        return False

    last = values[-1]

    last_row = dict(
        zip(
            COLUMNS,
            (
                last
                + [""] * len(COLUMNS)
            )[:len(COLUMNS)],
        )
    )

    same = (

        clean_text(
            last_row.get("Дата")
        )
        ==
        clean_text(
            row.get("Дата")
        )

        and

        clean_text(
            last_row.get("Час")
        )
        ==
        clean_text(
            row.get("Час")
        )

        and

        clean_text(
            last_row.get("Опис")
        )
        ==
        clean_text(
            row.get("Опис")
        )

        and

        clean_text(
            last_row.get("Тип")
        )
        ==
        clean_text(
            row.get("Тип")
        )
    )

    if same:

        ws.delete_rows(
            len(values)
        )

        return True

    return False


if undo_clicked:

    try:

        if not st.session_state.undo_stack:

            st.warning(
                "Немає дій для відміни. "
                "Максимум зберігається "
                "10 останніх дій."
            )

        else:

            action = (
                st.session_state.undo_stack.pop()
            )

            if action["action"] == "add":

                if not remove_matching_last_row(
                    action["row"]
                ):

                    st.warning(
                        "Не вдалося знайти "
                        "запис для відміни."
                    )

                else:

                    st.success(
                        "↩️ Додавання відмінено."
                    )

            elif action["action"] == "delete":

                append_entry(
                    action["row"]
                )

                st.success(
                    "↩️ Видалення відмінено — "
                    "запис повернуто."
                )

            st.rerun()

    except Exception as e:

        st.error(
            f"❌ Помилка відміни: {e}"
        )


# ============================================================
# DELETE
# ============================================================

if delete_clicked:

    try:

        deleted = delete_last_entry()

        if deleted is None:

            st.warning(
                "Немає записів для видалення."
            )

        else:

            with open(
                TRASH_FILE,
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    deleted,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            st.session_state.undo_stack.append(
                {
                    "action": "delete",
                    "row": deleted,
                }
            )

            st.session_state.undo_stack = (
                st.session_state.undo_stack[
                    -10:
                ]
            )

            st.success(
                "🗑️ Останній запис видалено."
            )

            st.rerun()

    except Exception as e:

        st.error(
            f"❌ Помилка видалення: {e}"
        )


# ============================================================
# РЕДАКТОР
# ============================================================

if settings_clicked:

    st.session_state.settings_open = (
        not st.session_state.settings_open
    )

    st.rerun()


if st.session_state.settings_open:

    st.subheader(
        "✏️ Редактор"
    )

    new_calories = st.number_input(

        "🎯 Добова норма калорій",

        min_value=0,

        value=int(
            settings.get(
                "calories",
                2000,
            )
        ),

        step=50,
    )


    new_bmr = st.number_input(

        "🔥 БМР / добова базова витрата",

        min_value=0,

        value=int(
            settings.get(
                "bmr_daily",
                1850,
            )
        ),

        step=50,
    )


    new_weight = st.number_input(

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


    new_exercise = st.checkbox(

        "💪 Враховувати тренування "
        "у дефіциті",

        value=bool(
            settings.get(
                "include_exercise_in_deficit",
                True,
            )
        ),
    )


    if st.button(
        "💾 Зберегти",
        type="primary",
        use_container_width=True,
    ):

        save_settings({

            "calories":
                new_calories,

            "bmr_daily":
                new_bmr,

            "initial_weight":
                new_weight,

            "include_exercise_in_deficit":
                new_exercise,
        })

        st.session_state.settings_open = False

        st.success(
            "✅ Налаштування збережено."
        )

        st.rerun()


# ============================================================
# ОНОВЛЮЄМО ДАНІ
# ============================================================

df = load_data()

current_weight = calculate_current_weight(
    df,
    settings,
)


if not df.empty:

    day_df = df[
        df["Дата"]
        == selected_date
    ].copy()

else:

    day_df = empty_dataframe()


if not day_df.empty:

    consumed = float(
        day_df[
            "Спожито"
        ].sum()
    )

    exercise_burned = float(
        day_df[
            "Спалено"
        ].sum()
    )

else:

    consumed = 0.0

    exercise_burned = 0.0


# ============================================================
# БМР
# ============================================================

bmr_daily = clean_number(
    settings.get(
        "bmr_daily",
        1850,
    )
)


now = datetime.now(
    LOCAL_TZ
)


if selected_date == today:

    hours_passed = (
        now.hour
        + now.minute / 60
    )

    bmr_elapsed = (
        bmr_daily / 24
    ) * hours_passed

else:

    bmr_elapsed = bmr_daily


# ============================================================
# ВИТРАТИ
# ============================================================

if settings.get(
    "include_exercise_in_deficit",
    True,
):

    total_burned = (
        bmr_elapsed
        + exercise_burned
    )

else:

    total_burned = bmr_elapsed


balance = (
    total_burned
    - consumed
)


# ============================================================
# СТАТУС
# ============================================================

if balance > 0:

    status_label = "ДЕФІЦИТ"

    status_icon = "📉"

    status_color = "#35D07F"

    balance_text = (
        f"{balance:.0f} ккал"
    )

    status_class = "deficit"


elif balance < 0:

    status_label = "ПРОФІЦИТ"

    status_icon = "📈"

    status_color = "#FF6262"

    balance_text = (
        f"+{abs(balance):.0f} ккал"
    )

    status_class = "surplus"


else:

    status_label = "БАЛАНС"

    status_icon = "⚖️"

    status_color = "#FFD166"

    balance_text = "0 ккал"

    status_class = "neutral"


# ============================================================
# КРУЖОК КАЛОРІЙ
# ============================================================

target = max(
    0.0,
    clean_number(
        settings.get(
            "calories",
            2000,
        )
    ),
)


if target > 0:

    eaten_share = min(
        max(
            consumed / target,
            0.0,
        ),
        1.0,
    )

else:

    eaten_share = 0.0


eaten_deg = (
    eaten_share * 360
)


if consumed <= target and target > 0:

    ring_background = (

        "conic-gradient("
        f"#36A2EB 0deg "
        f"{eaten_deg:.2f}deg, "
        f"#2b2e36 "
        f"{eaten_deg:.2f}deg "
        "360deg)"
    )

else:

    ring_background = (
        "conic-gradient("
        "#36A2EB 0deg 360deg)"
    )


# ============================================================
# КРУЖОК — РЕНДЕРИМО ЯК СПРАВЖНІЙ HTML
# ============================================================

donut_html = f"""

<!doctype html>

<html lang="uk">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,
             initial-scale=1"
>

<style>

* {{
    box-sizing: border-box;
}}

html,
body {{

    margin: 0;

    padding: 0;

    background: transparent;
}}


body {{

    min-height: 300px;

    display: flex;

    align-items: center;

    justify-content: center;

    font-family:
        Arial,
        sans-serif;

    color: #fff;
}}


.wrap {{

    width: 280px;

    height: 290px;

    display: flex;

    align-items: center;

    justify-content: center;
}}


.donut {{

    width: 230px;

    height: 230px;

    border-radius: 50%;

    background:
        {ring_background};

    display: flex;

    align-items: center;

    justify-content: center;

    box-shadow:
        0 0 30px
        rgba(0,0,0,.55);
}}


.hole {{

    width: 164px;

    height: 164px;

    border-radius: 50%;

    background: #15171c;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    text-align: center;

    padding: 10px;

    box-shadow:
        inset 0 0 22px
        rgba(0,0,0,.9);
}}


.status {{

    color:
        {status_color};

    font-size: 13px;

    font-weight: 900;
}}


.main {{

    color: #fff;

    font-size: 25px;

    font-weight: 900;

    margin-top: 4px;
}}


.sub {{

    color: #c7c7c7;

    font-size: 11px;

    margin-top: 7px;
}}

</style>

</head>

<body>

<div class="wrap">

    <div class="donut">

        <div class="hole">

            <div class="status">
                {status_icon}
                {status_label}
            </div>

            <div class="main">
                {consumed:.0f}
            </div>

            <div class="sub">
                🍽️ З'їдено /
                {target:.0f} ккал
            </div>

            <div class="sub">
                🔥 БМР:
                {bmr_daily:.0f}
                ккал/добу
            </div>

            <div class="sub">
                ⚖️
                {current_weight:.1f}
                кг
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
    scrolling=False,
)


# ============================================================
# ОСНОВНІ ЦИФРИ
# ============================================================

st.subheader(
    "📊 Сьогодні"
)


s1, s2, s3 = st.columns(3)


with s1:

    st.metric(
        "🍽️ З'їдено",
        f"{consumed:.0f} ккал",
    )


with s2:

    st.metric(
        "🎯 Добова норма",
        f"{target:.0f} ккал",
    )


with s3:

    st.metric(
        "🔥 Витрачено",
        f"{total_burned:.0f} ккал",
    )


if target > 0:

    progress_value = min(
        max(
            consumed / target,
            0.0,
        ),
        1.0,
    )

else:

    progress_value = 0.0


st.progress(
    progress_value
)


st.caption(
    f"🍽️ {consumed:.0f} "
    f"із {target:.0f} ккал"
)


# ============================================================
# ВЛОГ
# ============================================================

st.subheader(
    f"📋 Влог за {selected_date}"
)


if day_df.empty:

    st.info(
        "Записів ще немає. "
        "Додай їжу або тренування вище."
    )

else:

    for _, row in (
        day_df
        .iloc[::-1]
        .iterrows()
    ):

        time_value = clean_text(
            row.get(
                "Час",
                "",
            )
        )[:5]

        description = clean_text(
            row.get(
                "Опис",
                "",
            )
        )

        row_type = clean_text(
            row.get(
                "Тип",
                "Їжа",
            )
        ) or "Їжа"


        if row_type == "Тренування":

            icon = "💪"

            kcal = clean_number(
                row.get(
                    "Спалено",
                    0,
                )
            )

            kcal_text = (
                f"-{kcal:.0f} ккал"
            )

            kcal_color = "#FF6262"

        else:

            icon = "🍽️"

            kcal = clean_number(
                row.get(
                    "Спожито",
                    0,
                )
            )

            kcal_text = (
                f"+{kcal:.0f} ккал"
            )

            kcal_color = "#36A2EB"


        protein = clean_number(
            row.get(
                "Білки",
                0,
            )
        )

        fat = clean_number(
            row.get(
                "Жири",
                0,
            )
        )

        carbs = clean_number(
            row.get(
                "Вуглеводи",
                0,
            )
        )


        # ====================================================
        # ВАЖЛИВО:
        # БІЛЬШЕ НЕ ВИКОРИСТОВУЄМО HTML ДЛЯ ВЛОГУ
        # ====================================================

        with st.container(
            border=True
        ):

            left, right = st.columns(
                [4, 1]
            )


            with left:

                st.markdown(
                    f"**{time_value} "
                    f"{icon} "
                    f"{description}**"
                )


            with right:

                st.markdown(
                    f"**{kcal_text}**"
                )


            st.caption(

                f"Білки: "
                f"{protein:.1f} г "
                f"• Жири: "
                f"{fat:.1f} г "
                f"• Вуглеводи: "
                f"{carbs:.1f} г"
            )


# ============================================================
# ПІДСУМОК
# ============================================================

st.divider()


with st.container(
    border=True
):

    st.markdown(
        f"### "
        f"{status_icon} "
        f"{status_label}: "
        f"{balance_text}"
    )

    st.caption(
        f"З'їдено: "
        f"{consumed:.0f} ккал "
        f"• Витрачено: "
        f"{total_burned:.0f} ккал"
    )


st.caption(
    "⚖️ Орієнтир: приблизно "
    "7700 ккал накопиченого "
    "дефіциту ≈ 1 кг зміни ваги."
)


# ============================================================
# ДІАГНОСТИКА GOOGLE SHEETS
# ============================================================

with st.expander(
    "🔧 Перевірка Google Sheets"
):

    try:

        ws = get_worksheet(
            sheet_tab
        )

        st.success(
            "Google Sheets підключено: "
            f"вкладка «{ws.title}»"
        )

        st.caption(
            f"ID таблиці: "
            f"{SPREADSHEET_ID}"
        )

    except Exception as e:

        st.error(
            f"Google Sheets недоступний: {e}"
        )

        st.info(

            "Service Account має бути "
            "Editor саме для цієї таблиці. "

            "Також у Google Cloud мають "
            "бути увімкнені Google Sheets API "
            "та Google Drive API."
)
