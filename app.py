import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
from google import genai
from google.genai import types

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except ImportError:
    LOCAL_TZ = timezone(timedelta(hours=2))


# ============================================================
# НАЛАШТУВАННЯ STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Мій Фітнес",
    layout="centered"
)


# ============================================================
# ВИБІР ПРОФІЛЮ
# ============================================================

user_profile = st.sidebar.selectbox(
    "👤 Оберіть профіль:",
    ["Я", "Дружина"]
)

profile_prefix = (
    "user1"
    if user_profile == "Я"
    else "user2"
)

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
WEIGHT_FILE = f"weight_data_{profile_prefix}.json"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"

# Файл тепер використовується як історія Undo до 10 дій
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"

IMAGE_URL = (
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
            rgba(0, 0, 0, 0.75),
            rgba(0, 0, 0, 0.85)
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

    div[data-testid="stMetric"],
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px 14px;
        color: white;
    }}

    .food-box,
    .advice-box {{
        background-color: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px 16px;
        color: #ffffff;
        margin-top: 10px;
    }}

    .advice-box {{
        border-left: 4px solid #36A2EB;
    }}

    .donut-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 15px 0;
    }}

    .donut-ring {{
        width: 190px;
        height: 190px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow: 0 0 15px rgba(0,0,0,0.8);
    }}

    .donut-hole {{
        width: 125px;
        height: 125px;
        background-color: #141414;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: white;
    }}

    .macros-row {{
        display: flex;
        justify-content: space-around;
        width: 100%;
        max-width: 340px;
        margin-top: 12px;
        font-size: 11px;
        background-color: rgba(20, 20, 20, 0.9);
        padding: 8px 6px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    .log-item {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 0;
        font-size: 14px;
    }}

    .log-item:last-child {{
        border-bottom: none;
    }}

    .log-left {{
        word-break: break-word;
        overflow-wrap: break-word;
        margin-right: 10px;
        flex-grow: 1;
    }}

    .log-right {{
        white-space: nowrap;
        font-weight: bold;
        color: #36A2EB;
    }}

    /* ========================================================
       КНОПКИ
       ======================================================== */

    div.stButton > button {{
        min-height: 46px !important;
        height: 46px !important;
        width: 100% !important;
        border-radius: 12px !important;

        border: 1px solid rgba(255,255,255,0.14) !important;

        background:
            linear-gradient(
                180deg,
                rgba(55,55,55,0.95),
                rgba(30,30,30,0.95)
            ) !important;

        color: #ffffff !important;

        font-weight: 600 !important;

        box-shadow:
            0 3px 8px rgba(0,0,0,0.30) !important;

        transition:
            transform 0.10s ease,
            filter 0.10s ease,
            box-shadow 0.10s ease,
            background 0.10s ease !important;
    }}

    div.stButton > button:hover {{
        filter: brightness(1.18) !important;

        box-shadow:
            0 5px 12px rgba(0,0,0,0.40) !important;

        border-color:
            rgba(255,255,255,0.28) !important;
    }}

    div.stButton > button:active {{
        transform: scale(0.965) translateY(2px) !important;

        filter: brightness(0.72) !important;

        box-shadow:
            inset 0 3px 7px rgba(0,0,0,0.55) !important;
    }}

    div.stButton > button p {{
        margin: 0 !important;
        line-height: 1.2 !important;
    }}

    /* Primary */
    div.stButton > button[kind="primary"] {{
        background:
            linear-gradient(
                180deg,
                #2389d7,
                #1767aa
            ) !important;

        border-color:
            rgba(90,180,255,0.65) !important;
    }}

    div.stButton > button[kind="primary"]:hover {{
        filter: brightness(1.12) !important;
    }}

    div.stButton > button[kind="primary"]:active {{
        transform: scale(0.965) translateY(2px) !important;
        filter: brightness(0.72) !important;
    }}

    /* Disabled */
    div.stButton > button:disabled {{
        opacity: 0.38 !important;
        cursor: not-allowed !important;
        box-shadow: none !important;
    }}

    /* Expander */
    div[data-testid="stExpander"] {{
        border-radius: 12px !important;
        border-color: rgba(255,255,255,0.12) !important;
        background-color: rgba(20,20,20,0.55) !important;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "show_advice" not in st.session_state:
    st.session_state["show_advice"] = False

if "edit_mode" not in st.session_state:
    st.session_state["edit_mode"] = False

if "open_camera" not in st.session_state:
    st.session_state["open_camera"] = False

if "edit_log_mode" not in st.session_state:
    st.session_state["edit_log_mode"] = False

if "confirm_clear_day" not in st.session_state:
    st.session_state["confirm_clear_day"] = False


# ============================================================
# GEMINI
# ============================================================

api_key = (
    st.secrets.get("GEMINI_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
)

if not api_key:
    st.error("⚠️ Не знайдено API ключ!")
    st.stop()

client = genai.Client(api_key=api_key)


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
        "include_exercise_in_deficit": True
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
# WEIGHT FILE
# ============================================================

def load_weight():

    if os.path.exists(WEIGHT_FILE):

        try:
            with open(
                WEIGHT_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                return json.load(f)

        except Exception:
            pass

    return {
        "current_weight": 89.0
    }


def save_weight(weight_data):

    with open(
        WEIGHT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            weight_data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# DATA
# ============================================================

def load_data():

    if os.path.exists(EXCEL_FILE):

        try:

            df = pd.read_excel(EXCEL_FILE)

            required_columns = [
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

            for column in required_columns:

                if column not in df.columns:

                    if column in [
                        "Спожито",
                        "Спалено",
                        "Білки",
                        "Жири",
                        "Вуглеводи"
                    ]:
                        df[column] = 0
                    else:
                        df[column] = ""

            if "Час" in df.columns:

                df["Час"] = df["Час"].fillna(
                    datetime.now(
                        LOCAL_TZ
                    ).strftime("%H:%M")
                )

            numeric_columns = [
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи"
            ]

            for column in numeric_columns:

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce"
                ).fillna(0)

            return df

        except Exception:
            pass

    return pd.DataFrame(
        columns=[
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
    )


# ============================================================
# UNDO — ДО 10 ОПЕРАЦІЙ
# ============================================================

def load_undo_stack():

    if not os.path.exists(TRASH_FILE):
        return []

    try:

        with open(
            TRASH_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    return []


def save_undo_stack(stack):

    stack = stack[-10:]

    with open(
        TRASH_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            stack,
            f,
            ensure_ascii=False
        )


def dataframe_to_records(df):

    if df.empty:
        return []

    result = []

    for record in df.to_dict(
        orient="records"
    ):

        clean_record = {}

        for key, value in record.items():

            if pd.isna(value):
                clean_record[key] = ""
            elif isinstance(
                value,
                (int, float)
            ):
                clean_record[key] = float(value)
            else:
                clean_record[key] = str(value)

        result.append(clean_record)

    return result


def records_to_dataframe(records):

    columns = [
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

    if not records:
        return pd.DataFrame(
            columns=columns
        )

    df = pd.DataFrame(records)

    for column in columns:

        if column not in df.columns:

            if column in [
                "Спожито",
                "Спалено",
                "Білки",
                "Жири",
                "Вуглеводи"
            ]:
                df[column] = 0
            else:
                df[column] = ""

    df = df[columns]

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


def push_undo(df):

    stack = load_undo_stack()

    stack.append(
        dataframe_to_records(df)
    )

    stack = stack[-10:]

    save_undo_stack(stack)


def undo_last(df):

    stack = load_undo_stack()

    if not stack:
        return df, False

    previous_records = stack.pop()

    previous_df = records_to_dataframe(
        previous_records
    )

    save_undo_stack(stack)

    previous_df.to_excel(
        EXCEL_FILE,
        index=False
    )

    return previous_df, True


# ============================================================
# РОЗРАХУНОК ДНЯ
# ============================================================

def calculate_day_balance(
    day_df,
    date_str,
    settings,
    current_time=None
):

    if day_df is None or day_df.empty:
        return {
            "consumed": 0.0,
            "active": 0.0,
            "bmr": 0.0,
            "burned": 0.0,
            "balance": 0.0
        }

    bmr_daily = float(
        settings.get(
            "bmr_daily",
            1850
        )
    )

    include_exercise = bool(
        settings.get(
            "include_exercise_in_deficit",
            True
        )
    )

    consumed = float(
        pd.to_numeric(
            day_df["Спожито"],
            errors="coerce"
        ).fillna(0).sum()
    )

    active = float(
        pd.to_numeric(
            day_df["Спалено"],
            errors="coerce"
        ).fillna(0).sum()
    )

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    if date_str == today:

        if current_time is None:
            current_time = datetime.now(
                LOCAL_TZ
            )

        hours_passed = (
            current_time.hour
            + current_time.minute / 60
            + current_time.second / 3600
        )

        bmr = (
            bmr_daily / 24
        ) * hours_passed

    else:

        bmr = bmr_daily

    burned = bmr

    if include_exercise:
        burned += active

    balance = burned - consumed

    return {
        "consumed": consumed,
        "active": active,
        "bmr": bmr,
        "burned": burned,
        "balance": balance
    }


# ============================================================
# ВСЯ ІСТОРІЯ
# ============================================================

def calculate_history(
    df,
    settings
):

    if df.empty:

        return pd.DataFrame(
            columns=[
                "Дата",
                "З'їдено",
                "БМР",
                "Активність",
                "Витрачено",
                "Баланс",
                "Накопичений баланс",
                "Розрахункова вага"
            ]
        )

    work_df = df.copy()

    work_df["Дата"] = (
        work_df["Дата"]
        .astype(str)
    )

    dates = sorted(
        work_df["Дата"].unique()
    )

    initial_weight = float(
        settings.get(
            "initial_weight",
            89.0
        )
    )

    rows = []

    accumulated = 0.0

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    now = datetime.now(
        LOCAL_TZ
    )

    for date_str in dates:

        day_df = work_df[
            work_df["Дата"] == date_str
        ]

        if date_str == today:
            current_time = now
        else:
            current_time = None

        result = calculate_day_balance(
            day_df,
            date_str,
            settings,
            current_time
        )

        accumulated += result["balance"]

        calculated_weight = (
            initial_weight
            - accumulated / 7700
        )

        rows.append({
            "Дата": date_str,
            "З'їдено": result["consumed"],
            "БМР": result["bmr"],
            "Активність": result["active"],
            "Витрачено": result["burned"],
            "Баланс": result["balance"],
            "Накопичений баланс": accumulated,
            "Розрахункова вага": max(
                0,
                calculated_weight
            )
        })

    return pd.DataFrame(rows)


def get_current_calculated_weight(
    df,
    settings
):

    history = calculate_history(
        df,
        settings
    )

    initial_weight = float(
        settings.get(
            "initial_weight",
            89.0
        )
    )

    if history.empty:
        return initial_weight

    return float(
        history.iloc[-1][
            "Розрахункова вага"
        ]
    )


# ============================================================
# LOAD
# ============================================================

user_settings = load_settings()
w_data = load_weight()
df_data = load_data()

current_weight = get_current_calculated_weight(
    df_data,
    user_settings
)


# ============================================================
# TITLE
# ============================================================

st.title(
    f"🏋️ Фітнес: {user_profile}"
)


# ============================================================
# INPUT
# ============================================================

with st.container(border=True):

    user_input = st.text_input(
        "📥 Що з'їв / тренування:",
        placeholder="Наприклад: з'їв 30г хліба"
    )

    if not st.session_state["open_camera"]:

        if st.button(
            "📸 Увімкнути камеру",
            use_container_width=True
        ):

            st.session_state[
                "open_camera"
            ] = True

            st.rerun()

    else:

        if st.button(
            "❌ Вимкнути камеру",
            use_container_width=True
        ):

            st.session_state[
                "open_camera"
            ] = False

            st.rerun()

    submit_btn = st.button(
        "✅ Записати в лог",
        type="primary",
        use_container_width=True
    )

    captured_image = None

    if st.session_state["open_camera"]:

        captured_image = st.camera_input(
            "Зробити фото камерою"
        )


# ============================================================
# ADD ENTRY
# ============================================================

if submit_btn and (
    user_input or captured_image
):

    current_time_str = datetime.now(
        LOCAL_TZ
    ).strftime("%H:%M")

    current_date_str = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    try:

        if captured_image:

            image_bytes = (
                captured_image.getvalue()
            )

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )

            prompt = (
                "Проаналізуй страву на фото. "
                "Поверни суворо JSON з ключами: "
                "food_description, kcal_burned, "
                "total_consumed_kcal, total_protein, "
                "total_fat, total_carbs."
            )

            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[
                    image_part,
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

        else:

            prompt = (
                f'Аналізуй: "{user_input}". '
                "Поверни суворо JSON з ключами: "
                "food_description, kcal_burned, "
                "total_consumed_kcal, total_protein, "
                "total_fat, total_carbs."
            )

            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

        data = json.loads(
            response.text
        )

        f_desc = (
            data.get("food_description")
            or user_input
            or "Фото їжі"
        )

        k_burned = float(
            data.get("kcal_burned") or 0
        )

        c_consumed = float(
            data.get("total_consumed_kcal") or 0
        )

        prot = float(
            data.get("total_protein") or 0
        )

        fat_val = float(
            data.get("total_fat") or 0
        )

        carb = float(
            data.get("total_carbs") or 0
        )

        # Зберігаємо стан ДО зміни
        push_undo(df_data)

        new_entry = pd.DataFrame(
            [{
                "Дата": current_date_str,
                "Час": current_time_str,
                "Опис": f_desc,
                "Тип": (
                    "Тренування"
                    if k_burned > 0
                    else "Їжа"
                ),
                "Спожито": c_consumed,
                "Спалено": k_burned,
                "Білки": prot,
                "Жири": fat_val,
                "Вуглеводи": carb
            }]
        )

        df_data = pd.concat(
            [
                df_data,
                new_entry
            ],
            ignore_index=True
        )

        df_data.to_excel(
            EXCEL_FILE,
            index=False
        )

        st.session_state[
            "open_camera"
        ] = False

        st.rerun()

    except Exception as e:

        st.error(
            f"Помилка: {e}"
        )


# ============================================================
# DATES
# ============================================================

today_str = datetime.now(
    LOCAL_TZ
).strftime("%Y-%m-%d")

available_dates = [
    today_str
]

if not df_data.empty:

    unique_dates = sorted(
        df_data["Дата"]
        .astype(str)
        .unique(),
        reverse=True
    )

    for date_value in unique_dates:

        if date_value not in available_dates:

            available_dates.append(
                date_value
            )


selected_date = st.selectbox(
    "📅 Вибрати день для перегляду:",
    available_dates
)


# ============================================================
# MAIN BUTTONS
# ============================================================

btn_settings = st.button(
    "⚙️ Налаштування",
    use_container_width=True
)

undo_stack = load_undo_stack()

has_undo = len(undo_stack) > 0

btn_del = st.button(
    "🗑️ Видалити останній запис",
    use_container_width=True
)

btn_back = st.button(
    "🔄 Повернути",
    disabled=not has_undo,
    use_container_width=True
)


# ============================================================
# SETTINGS
# ============================================================

if btn_settings:

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


# ============================================================
# DELETE LAST RECORD
# ============================================================

if btn_del:

    if not df_data.empty:

        push_undo(df_data)

        df_data = df_data.iloc[:-1]

        df_data.to_excel(
            EXCEL_FILE,
            index=False
        )

        st.rerun()


# ============================================================
# UNDO
# ============================================================

if btn_back:

    df_data, restored = undo_last(
        df_data
    )

    if restored:

        st.session_state[
            "show_advice"
        ] = False

        st.session_state[
            "edit_log_mode"
        ] = False

        st.rerun()


# ============================================================
# SETTINGS PANEL
# ============================================================

if st.session_state["edit_mode"]:

    with st.container(border=True):

        st.subheader(
            f"Налаштування профілю: {user_profile}"
        )

        e_cal = st.number_input(
            "Ціль калорій",
            value=int(
                user_settings["calories"]
            ),
            step=10
        )

        e_prot = st.number_input(
            "Ціль білків (г)",
            value=int(
                user_settings["protein"]
            ),
            step=5
        )

        e_fat = st.number_input(
            "Ціль жирів (г)",
            value=int(
                user_settings["fat"]
            ),
            step=5
        )

        e_carb = st.number_input(
            "Ціль вуглеводів (г)",
            value=int(
                user_settings["carbs"]
            ),
            step=5
        )

        e_weight = st.number_input(
            "Початкова вага (кг)",
            value=float(
                user_settings.get(
                    "initial_weight",
                    89.0
                )
            ),
            min_value=0.0,
            step=0.1
        )

        e_include_exercise = st.checkbox(
            "Враховувати вправи в дефіцит",
            value=bool(
                user_settings.get(
                    "include_exercise_in_deficit",
                    True
                )
            )
        )

        if st.button(
            "💾 Зберегти зміни",
            type="primary",
            use_container_width=True
        ):

            new_settings = {
                "calories": e_cal,
                "protein": e_prot,
                "fat": e_fat,
                "carbs": e_carb,
                "bmr_daily": user_settings.get(
                    "bmr_daily",
                    1850
                ),
                "initial_weight": e_weight,
                "include_exercise_in_deficit":
                    e_include_exercise
            }

            save_settings(
                new_settings
            )

            save_weight({
                "current_weight": e_weight
            })

            st.session_state[
                "edit_mode"
            ] = False

            st.rerun()


# ============================================================
# DAY DATA
# ============================================================

day_df = (
    df_data[
        df_data["Дата"].astype(str)
        == selected_date
    ]
    if not df_data.empty
    else pd.DataFrame()
)

now = datetime.now(
    LOCAL_TZ
)


# ============================================================
# DAY DISPLAY
# ============================================================

if not day_df.empty:

    day_result = calculate_day_balance(
        day_df,
        selected_date,
        user_settings,
        now
    )

    consumed = day_result[
        "consumed"
    ]

    active_burned = day_result[
        "active"
    ]

    bmr_used = day_result[
        "bmr"
    ]

    total_burned = day_result[
        "burned"
    ]

    balance = day_result[
        "balance"
    ]

    protein = float(
        pd.to_numeric(
            day_df["Білки"],
            errors="coerce"
        ).fillna(0).sum()
    )

    fat = float(
        pd.to_numeric(
            day_df["Жири"],
            errors="coerce"
        ).fillna(0).sum()
    )

    carbs = float(
        pd.to_numeric(
            day_df["Вуглеводи"],
            errors="coerce"
        ).fillna(0).sum()
    )

    target_cal = user_settings[
        "calories"
    ]

    target_p = user_settings[
        "protein"
    ]

    target_f = user_settings[
        "fat"
    ]

    target_c = user_settings[
        "carbs"
    ]


    # ========================================================
    # BALANCE
    # ========================================================

    if balance >= 0:

        balance_label = "Дефіцит"

        balance_text = (
            f"−{abs(int(balance))} ккал"
        )

        balance_color = "#36A2EB"

    else:

        balance_label = "Профіцит"

        balance_text = (
            f"+{abs(int(balance))} ккал"
        )

        balance_color = "#FF6384"


    # ========================================================
    # CURRENT WEIGHT
    # ========================================================

    current_weight = get_current_calculated_weight(
        df_data,
        user_settings
    )

    initial_weight = float(
        user_settings.get(
            "initial_weight",
            89.0
        )
    )

    weight_change = (
        current_weight
        - initial_weight
    )


    if weight_change <= 0:

        weight_change_text = (
            f"−{abs(weight_change):.2f} кг"
        )

    else:

        weight_change_text = (
            f"+{weight_change:.2f} кг"
        )


    # ========================================================
    # DATE / WEIGHT
    # ========================================================

    st.markdown(
        f"**📅 {selected_date}**\n\n"
        f"⚖️ **Вага (розрахункова): {current_weight:.1f} кг** ({weight_change_text} від початкової)"
    )


    # ========================================================
    # DONUT
    # ========================================================

    total_macros = (
        protein
        + fat
        + carbs
    )

    if total_macros > 0:

        p_deg = (
            protein
            / total_macros
        ) * 360

        f_deg = (
            p_deg
            + (
                fat
                / total_macros
            ) * 360
        )

        c_deg = (
            f_deg
            + (
                carbs
                / total_macros
            ) * 360
        )

    else:

        p_deg = 0
        f_deg = 0
        c_deg = 0


    st.markdown(
        f"""
        <div class="donut-container">

            <div
                class="donut-ring"
                style="
                    background:
                    conic-gradient(
                        #36A2EB 0deg {p_deg}deg,
                        #FFCE56 {p_deg}deg {f_deg}deg,
                        #FF6384 {f_deg}deg {c_deg}deg
                    );
                "
            >

                <div class="donut-hole">

                    <span
                        style="
                            font-size: 10px;
                            color: {balance_color};
                        "
                    >
                        {balance_label}:
                        {balance_text}
                    </span>

                    <b
                        style="
                            font-size: 14px;
                        "
                    >
                        {int(consumed)} / {target_cal}
                    </b>

                    <span
                        style="
                            font-size: 9px;
                            color: #888;
                        "
                    >
                        ккал
                    </span>

                </div>

            </div>

            <div class="macros-row">

                <span style="color: #36A2EB;">
                    🥩 Білки:
                    {protein:.0f} / {target_p}г
                </span>

                <span style="color: #FFCE56;">
                    🥑 Жири:
                    {fat:.0f} / {target_f}г
                </span>

                <span style="color: #FF6384;">
                    🍞 Вугл:
                    {carbs:.0f} / {target_c}г
                </span>

            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # METRICS
    # ========================================================

    c1, c2 = st.columns(2)

    c1.metric(
        "🍽️ З'їв",
        f"{int(consumed)} ккал"
    )

    c2.metric(
        "🔥 Спалено",
        f"{int(total_burned)} ккал"
    )


    # ========================================================
    # DETAIL OF CALORIES
    # ========================================================

    with st.expander(
        "🔥 Деталі витрат калорій"
    ):

        d1, d2, d3 = st.columns(3)

        d1.metric(
            "🫀 БМР",
            f"{int(bmr_used)} ккал"
        )

        d2.metric(
            "🏃 Активність",
            f"{int(active_burned)} ккал"
        )

        d3.metric(
            "🔥 Разом",
            f"{int(total_burned)} ккал"
        )


    # ========================================================
    # LOG
    # ========================================================

    log_html_lines = []

    for _, row in day_df.iterrows():

        t_val = str(
            row["Час"]
        )[:5]

        icon = (
            "💪"
            if row["Тип"] == "Тренування"
            else "🍽️"
        )

        desc = row["Опис"]

        kcal = int(
            row["Спалено"]
            if row["Тип"] == "Тренування"
            else row["Спожито"]
        )

        log_html_lines.append(
            f"""
            <div class="log-item">

                <div class="log-left">
                    {t_val}
                    {icon}
                    {desc}
                </div>

                <div class="log-right">
                    <b>{kcal} ккал</b>
                </div>

            </div>
            """
        )

    st.markdown(
        f"""
        <div class="food-box">

            <b>📝 Лог:</b><br>

            {"".join(log_html_lines)}

        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # EDIT LOG
    # ========================================================

    if st.button(
        "✏️ Редагувати лог (таблиця)",
        use_container_width=True
    ):

        st.session_state[
            "edit_log_mode"
        ] = not st.session_state[
            "edit_log_mode"
        ]


    if st.session_state[
        "edit_log_mode"
    ]:

        with st.container(border=True):

            st.subheader(
                "Редагування записів за день"
            )

            day_indices = day_df.index

            edited_day_df = st.data_editor(
                df_data.loc[day_indices],
                key=f"editor_{selected_date}",
                use_container_width=True
            )

            if st.button(
                "💾 Зберегти зміни в лозі",
                type="primary",
                use_container_width=True
            ):

                # Зберігаємо стан до редагування
                push_undo(df_data)

                df_data.loc[
                    day_indices
                ] = edited_day_df

                df_data.to_excel(
                    EXCEL_FILE,
                    index=False
                )

                st.session_state[
                    "edit_log_mode"
                ] = False

                st.rerun()


    # ========================================================
    # GEMINI ADVICE
    # ========================================================

    if st.button(
        "💡 Порада Gemini",
        use_container_width=True
    ):

        st.session_state[
            "show_advice"
        ] = True

    if st.session_state[
        "show_advice"
    ]:

        try:

            advice_prompt = (
                f"Аналіз за {selected_date}. "
                f"З'їдено: {consumed:.0f} ккал. "
                f"БМР: {bmr_used:.0f} ккал. "
                f"Активність: {active_burned:.0f} ккал. "
                f"Всього витрачено: "
                f"{total_burned:.0f} ккал. "
                f"Баланс: {balance:.0f} ккал. "
                f"Білки: {protein:.0f} г. "
                f"Жири: {fat:.0f} г. "
                f"Вуглеводи: {carbs:.0f} г. "
                f"Дай коротку практичну пораду."
            )

            advice_resp = (
                client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=advice_prompt
                )
            )

            st.markdown(
                f"""
                <div class="advice-box">

                    <b>💡 Порада:</b><br>

                    {advice_resp.text}

                </div>
                """,
                unsafe_allow_html=True
            )

        except Exception as e:

            st.error(
                f"Помилка Gemini: {e}"
            )


else:

    st.info(
        f"За цей день ({selected_date}) "
        f"ще немає записів."
    )


# ============================================================
# НАКОПИЧУВАЛЬНИЙ ДЕФІЦИТ
# ============================================================

history_df = calculate_history(
    df_data,
    user_settings
)

if not history_df.empty:

    accumulated_balance = float(
        history_df.iloc[-1][
            "Накопичений баланс"
        ]
    )

    accumulated_weight_change = (
        accumulated_balance / 7700
    )

    if accumulated_balance >= 0:

        acc_title = "🔥 Накопичений дефіцит"

        acc_text = (
            f"−{abs(int(accumulated_balance)):,}"
            .replace(",", " ")
            + " ккал"
        )

        acc_weight = (
            f"−{abs(accumulated_weight_change):.2f} кг"
        )

    else:

        acc_title = "⚠️ Накопичений профіцит"

        acc_text = (
            f"+{abs(int(accumulated_balance)):,}"
            .replace(",", " ")
            + " ккал"
        )

        acc_weight = (
            f"+{abs(accumulated_weight_change):.2f} кг"
        )

    with st.container(border=True):

        st.subheader(
            acc_title
        )

        a1, a2 = st.columns(2)

        a1.metric(
            "Баланс за весь час",
            acc_text
        )

        a2.metric(
            "Розрахункова зміна ваги",
            acc_weight
        )


# ============================================================
# ТИЖНЕВИЙ ПІДСУМОК
# ============================================================

if not history_df.empty:

    today = datetime.now(
        LOCAL_TZ
    ).date()

    week_start = (
        today
        - timedelta(days=6)
    )

    history_dates = pd.to_datetime(
        history_df["Дата"],
        errors="coerce"
    )

    week_mask = (
        history_dates.dt.date
        >= week_start
    ) & (
        history_dates.dt.date
        <= today
    )

    week_df = history_df[
        week_mask
    ]

    if not week_df.empty:

        week_consumed = float(
            week_df["З'їдено"].sum()
        )

        week_burned = float(
            week_df["Витрачено"].sum()
        )

        week_active = float(
            week_df["Активність"].sum()
        )

        week_balance = (
            week_burned
            - week_consumed
        )

        week_weight_change = (
            week_balance / 7700
        )

        with st.container(border=True):

            st.subheader(
                "📅 Підсумок за останні 7 днів"
            )

            w1, w2 = st.columns(2)

            w1.metric(
                "🍽️ З'їдено",
                f"{int(week_consumed)} ккал"
            )

            w2.metric(
                "🔥 Витрачено",
                f"{int(week_burned)} ккал"
            )

            w3, w4 = st.columns(2)

            if week_balance >= 0:

                w3.metric(
                    "📉 Дефіцит",
                    f"−{abs(int(week_balance))} ккал"
                )

                w4.metric(
                    "⚖️ Зміна ваги",
                    f"−{abs(week_weight_change):.2f} кг"
                )

            else:

                w3.metric(
                    "📈 Профіцит",
                    f"+{abs(int(week_balance))} ккал"
                )

                w4.metric(
                    "⚖️ Зміна ваги",
                    f"+{abs(week_weight_change):.2f} кг"
                )

            st.caption(
                f"🏃 Активні калорії: "
                f"{int(week_active)} ккал"
            )


# ============================================================
# ГРАФІК ВАГИ
# ============================================================

if not history_df.empty:

    chart_df = history_df[
        [
            "Дата",
            "Розрахункова вага"
        ]
    ].copy()

    chart_df["Дата"] = pd.to_datetime(
        chart_df["Дата"],
        errors="coerce"
    )

    chart_df = chart_df.dropna(
        subset=["Дата"]
    )

    chart_df = chart_df.set_index(
        "Дата"
    )

    if len(chart_df) >= 1:

        with st.container(border=True):

            st.subheader(
                "⚖️ Графік розрахункової ваги"
            )

            st.line_chart(
                chart_df[
                    ["Розрахункова вага"]
                ],
                height=260,
                use_container_width=True
            )


# ============================================================
# БЕЗПЕЧНЕ ОЧИЩЕННЯ ДНЯ
# ============================================================

with st.expander(
    "⚠️ Небезпечні дії"
):

    st.caption(
        "Очищення дня видалить усі записи "
        "за вибрану дату. Перед видаленням "
        "буде створено резервну копію, "
        "і дію можна буде скасувати."
    )

    if not st.session_state[
        "confirm_clear_day"
    ]:

        if st.button(
            "⚠️ Очистити цей день",
            use_container_width=True
        ):

            st.session_state[
                "confirm_clear_day"
            ] = True

            st.rerun()

    else:

        st.warning(
            f"Точно видалити всі записи "
            f"за {selected_date}?"
        )

        confirm_col1, confirm_col2 = (
            st.columns(2)
        )

        with confirm_col1:

            if st.button(
                "❌ Так, видалити",
                use_container_width=True
            ):

                push_undo(df_data)

                df_data = df_data[
                    df_data["Дата"].astype(str)
                    != selected_date
                ]

                df_data.to_excel(
                    EXCEL_FILE,
                    index=False
                )

                st.session_state[
                    "confirm_clear_day"
                ] = False

                st.rerun()

        with confirm_col2:

            if st.button(
                "↩️ Скасувати",
                use_container_width=True
            ):

                st.session_state[
                    "confirm_clear_day"
                ] = False

                st.rerun()
