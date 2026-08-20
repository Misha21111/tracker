import os
import json
import html
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
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="🏋️",
    layout="centered"
)


# ============================================================
# ПРОФІЛЬ
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


# ============================================================
# ФАЙЛИ
# ============================================================

EXCEL_FILE = (
    f"fitness_entries_{profile_prefix}.xlsx"
)

SETTINGS_FILE = (
    f"user_settings_{profile_prefix}.json"
)

TRASH_FILE = (
    f"fitness_trash_{profile_prefix}.json"
)


# ============================================================
# ФОН
# ============================================================

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
            rgba(0, 0, 0, 0.72),
            rgba(0, 0, 0, 0.88)
        ),
        url("{IMAGE_URL}");

    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}


/* Прибираємо стандартні елементи */

#MainMenu,
footer,
header {{
    visibility: hidden;
}}


/* ============================================================
   КНОПКИ
   ============================================================ */

div.stButton > button {{
    min-height: 46px !important;

    border-radius: 14px !important;

    border:
        1px solid
        rgba(255,255,255,0.12) !important;

    background:
        linear-gradient(
            135deg,
            rgba(42,42,50,0.98),
            rgba(18,18,23,0.98)
        ) !important;

    color: #ffffff !important;

    font-weight: 700 !important;

    box-shadow:
        0 6px 18px
        rgba(0,0,0,0.30);

    transition:
        all 0.18s ease;
}}


div.stButton > button:hover {{
    transform:
        translateY(-2px);

    border-color:
        rgba(54,162,235,0.65) !important;

    box-shadow:
        0 10px 26px
        rgba(0,0,0,0.40);
}}


div.stButton > button:active {{
    transform:
        translateY(0);
}}


/* Primary */

div.stButton > button[kind="primary"] {{
    background:
        linear-gradient(
            135deg,
            #36A2EB,
            #1976D2
        ) !important;

    border:
        none !important;

    box-shadow:
        0 8px 22px
        rgba(54,162,235,0.35);
}}


/* ============================================================
   INPUT
   ============================================================ */

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
    border-radius:
        12px !important;

    background:
        rgba(18,18,22,0.92) !important;

    color:
        #ffffff !important;
}}


/* ============================================================
   КАРТКИ
   ============================================================ */

.food-box,
.advice-box {{
    background:
        rgba(20,20,20,0.88);

    border:
        1px solid
        rgba(255,255,255,0.10);

    border-radius:
        14px;

    padding:
        12px 16px;

    color:
        #ffffff;

    margin-top:
        10px;
}}


.advice-box {{
    border-left:
        4px solid #36A2EB;
}}


/* ============================================================
   DONUT
   ============================================================ */

.donut-container {{
    display:
        flex;

    flex-direction:
        column;

    align-items:
        center;

    justify-content:
        center;

    width:
        100%;

    margin:
        20px 0;
}}


.donut-ring {{
    width:
        210px;

    height:
        210px;

    border-radius:
        50%;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    box-shadow:
        0 0 30px
        rgba(0,0,0,0.75);
}}


.donut-hole {{
    width:
        148px;

    height:
        148px;

    border-radius:
        50%;

    background:
        #141414;

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

    color:
        #ffffff;

    box-shadow:
        inset 0 0 22px
        rgba(0,0,0,0.75);
}}


/* ============================================================
   БАЛАНС
   ============================================================ */

.deficit {{
    color:
        #35D07F !important;
}}


.surplus {{
    color:
        #FF6262 !important;
}}


.neutral {{
    color:
        #FFD166 !important;
}}


/* ============================================================
   МАКРОСИ
   ============================================================ */

.macros-row {{
    display:
        flex;

    justify-content:
        space-around;

    align-items:
        center;

    width:
        100%;

    max-width:
        360px;

    margin-top:
        14px;

    padding:
        10px 6px;

    border-radius:
        12px;

    background:
        rgba(20,20,20,0.92);

    border:
        1px solid
        rgba(255,255,255,0.10);

    font-size:
        11px;
}}


/* ============================================================
   ЛОГ
   ============================================================ */

.log-item {{
    display:
        flex;

    justify-content:
        space-between;

    align-items:
        flex-start;

    padding:
        9px 0;

    border-bottom:
        1px solid
        rgba(255,255,255,0.08);

    font-size:
        14px;
}}


.log-item:last-child {{
    border-bottom:
        none;
}}


.log-left {{
    flex-grow:
        1;

    margin-right:
        10px;

    word-break:
        break-word;
}}


.log-right {{
    white-space:
        nowrap;

    font-weight:
        bold;

    color:
        #36A2EB;
}}


/* ============================================================
   TITLE
   ============================================================ */

h1 {{
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

if "edit_mode" not in st.session_state:
    st.session_state["edit_mode"] = False

if "open_camera" not in st.session_state:
    st.session_state["open_camera"] = False


# ============================================================
# GEMINI API
# ============================================================

api_key = None

try:
    api_key = st.secrets.get(
        "GEMINI_API_KEY"
    )
except Exception:
    api_key = None


if not api_key:
    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )


if not api_key:

    st.error(
        "⚠️ Не знайдено GEMINI_API_KEY."
    )

    st.info(
        "Додай GEMINI_API_KEY у Secrets "
        "свого Streamlit-проєкту."
    )

    st.stop()


client = genai.Client(
    api_key=api_key
)


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

        "initial_weight": 89.0,

        "include_exercise_in_deficit": True

    }


    if os.path.exists(
        SETTINGS_FILE
    ):

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

def empty_dataframe():

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


def load_data():

    if not os.path.exists(
        EXCEL_FILE
    ):
        return empty_dataframe()


    try:

        df = pd.read_excel(
            EXCEL_FILE
        )

    except Exception:

        return empty_dataframe()


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

            elif column == "Тип":

                df[column] = "Їжа"

            elif column == "Опис":

                df[column] = ""

            elif column == "Час":

                df[column] = datetime.now(
                    LOCAL_TZ
                ).strftime("%H:%M")

            elif column == "Дата":

                df[column] = datetime.now(
                    LOCAL_TZ
                ).strftime("%Y-%m-%d")


    return df[required_columns]


# ============================================================
# РОЗРАХУНОК ПОТОЧНОЇ ВАГИ
# ============================================================

def calculate_current_weight(
    df,
    settings
):

    initial_weight = float(
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

        return initial_weight


    work_df = df.copy()


    work_df["Дата"] = (
        work_df["Дата"]
        .astype(str)
    )


    work_df["Спожито"] = pd.to_numeric(
        work_df["Спожито"],
        errors="coerce"
    ).fillna(0)


    work_df["Спалено"] = pd.to_numeric(
        work_df["Спалено"],
        errors="coerce"
    ).fillna(0)


    total_balance = 0.0


    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")


    now = datetime.now(
        LOCAL_TZ
    )


    for date_str in (
        work_df["Дата"].unique()
    ):

        day_df = work_df[
            work_df["Дата"] == date_str
        ]


        consumed = float(
            day_df["Спожито"].sum()
        )


        exercise_burned = float(
            day_df["Спалено"].sum()
        )


        # ----------------------------------------------------
        # BMR
        # ----------------------------------------------------

        if date_str == today:

            hours_passed = (
                now.hour
                +
                now.minute / 60
            )


            bmr_for_day = (
                bmr_daily / 24
            ) * hours_passed

        else:

            bmr_for_day = (
                bmr_daily
            )


        # ----------------------------------------------------
        # Загальна витрата
        # ----------------------------------------------------

        if settings.get(
            "include_exercise_in_deficit",
            True
        ):

            total_burned = (
                bmr_for_day
                +
                exercise_burned
            )

        else:

            total_burned = (
                bmr_for_day
            )


        # ----------------------------------------------------
        # ДЕФІЦИТ / ПРОФІЦИТ
        #
        # burned - consumed
        #
        # + = дефіцит
        # - = профіцит
        # ----------------------------------------------------

        total_balance += (
            total_burned
            -
            consumed
        )


    # --------------------------------------------------------
    # 7700 ккал ≈ 1 кг
    # --------------------------------------------------------

    weight_change = (
        total_balance / 7700.0
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
# ЗАВАНТАЖЕННЯ
# ============================================================

user_settings = load_settings()

df_data = load_data()


calculated_weight = (
    calculate_current_weight(
        df_data,
        user_settings
    )
)


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    f"🏋️ Фітнес: {user_profile}"
)


# ============================================================
# ВВЕДЕННЯ
# ============================================================

user_input = st.text_input(
    "📥 Що з'їв / тренування:",
    placeholder=(
        "Наприклад: з'їв 30 г хліба"
    )
)


# ============================================================
# КАМЕРА
# ============================================================

if not st.session_state[
    "open_camera"
]:

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


captured_image = None


if st.session_state[
    "open_camera"
]:

    captured_image = st.camera_input(
        "Зробити фото"
    )


# ============================================================
# КНОПКА ЗАПИСУ
# ============================================================

submit_btn = st.button(
    "✅ Записати в лог",
    type="primary",
    use_container_width=True
)


# ============================================================
# GEMINI АНАЛІЗ
# ============================================================

if submit_btn and (
    user_input
    or captured_image
):

    current_time_str = (
        datetime
        .now(LOCAL_TZ)
        .strftime("%H:%M")
    )


    current_date_str = (
        datetime
        .now(LOCAL_TZ)
        .strftime("%Y-%m-%d")
    )


    try:

        # ====================================================
        # ФОТО
        # ====================================================

        if captured_image:

            image_bytes = (
                captured_image
                .getvalue()
            )


            image_part = (
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                )
            )


            prompt = """
Ти аналізуєш їжу або тренування.

Поверни ТІЛЬКИ JSON.

Формат:

{
    "food_description": "опис",
    "kcal_burned": 0,
    "total_consumed_kcal": 0,
    "total_protein": 0,
    "total_fat": 0,
    "total_carbs": 0
}

Правила:

1. Якщо на фото їжа:
   - total_consumed_kcal > 0
   - kcal_burned = 0

2. Якщо на фото тренування:
   - kcal_burned > 0
   - total_consumed_kcal = 0

3. Білки, жири та вуглеводи
   вказуй у грамах.

4. Якщо значення невідоме,
   використовуй 0.

5. Не додавай Markdown.
6. Не додавай пояснення.
7. Поверни тільки JSON.
"""


            response = (
                client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=[
                        image_part,
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
            )


        # ====================================================
        # ТЕКСТ
        # ====================================================

        else:

            prompt = f"""
Проаналізуй цей запис:

"{user_input}"

Визнач, чи це їжа або тренування.

Поверни ТІЛЬКИ JSON.

Формат:

{{
    "food_description": "опис",
    "kcal_burned": 0,
    "total_consumed_kcal": 0,
    "total_protein": 0,
    "total_fat": 0,
    "total_carbs": 0
}}

Правила:

1. Якщо це їжа:
   - total_consumed_kcal > 0
   - kcal_burned = 0

2. Якщо це тренування:
   - kcal_burned > 0
   - total_consumed_kcal = 0

3. Білки, жири та вуглеводи
   вказуй у грамах.

4. Якщо значення невідоме,
   використовуй 0.

5. Поверни тільки JSON.
"""


            response = (
                client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
            )


        # ====================================================
        # ОТРИМУЄМО JSON
        # ====================================================

        response_text = (
            response.text
            or ""
        ).strip()


        data = json.loads(
            response_text
        )


        # ====================================================
        # ЗНАЧЕННЯ
        # ====================================================

        burned = float(
            data.get(
                "kcal_burned",
                0
            )
            or 0
        )


        consumed = float(
            data.get(
                "total_consumed_kcal",
                0
            )
            or 0
        )


        protein_value = float(
            data.get(
                "total_protein",
                0
            )
            or 0
        )


        fat_value = float(
            data.get(
                "total_fat",
                0
            )
            or 0
        )


        carbs_value = float(
            data.get(
                "total_carbs",
                0
            )
            or 0
        )


        description = (
            data.get(
                "food_description"
            )
            or user_input
            or "Запис"
        )


        # ====================================================
        # НОВИЙ ЗАПИС
        # ====================================================

        new_entry = pd.DataFrame(
            [
                {
                    "Дата":
                        current_date_str,

                    "Час":
                        current_time_str,

                    "Опис":
                        description,

                    "Тип":
                        (
                            "Тренування"
                            if burned > 0
                            else "Їжа"
                        ),

                    "Спожито":
                        consumed,

                    "Спалено":
                        burned,

                    "Білки":
                        protein_value,

                    "Жири":
                        fat_value,

                    "Вуглеводи":
                        carbs_value
                }
            ]
        )


        # ====================================================
        # ДОДАЄМО
        # ====================================================

        df_data = pd.concat(
            [
                df_data,
                new_entry
            ],
            ignore_index=True
        )


        # ====================================================
        # ЗБЕРІГАЄМО EXCEL
        # ====================================================

        df_data.to_excel(
            EXCEL_FILE,
            index=False
        )


        st.session_state[
            "open_camera"
        ] = False


        st.success(
            "✅ Запис додано!"
        )


        st.rerun()


    except json.JSONDecodeError:

        st.error(
            "❌ Gemini повернув некоректний JSON."
        )

        st.code(
            response_text
            if "response_text" in locals()
            else ""
        )


    except Exception as e:

        st.error(
            f"❌ Помилка обробки: {e}"
        )


# ============================================================
# РОЗДІЛ
# ============================================================

st.divider()


# ============================================================
# ДАТИ
# ============================================================

today_str = (
    datetime
    .now(LOCAL_TZ)
    .strftime("%Y-%m-%d")
)


available_dates = [
    today_str
]


if (
    not df_data.empty
    and "Дата" in df_data.columns
):

    dates = (
        df_data["Дата"]
        .astype(str)
        .unique()
    )


    for date_value in sorted(
        dates,
        reverse=True
    ):

        if date_value not in available_dates:

            available_dates.append(
                date_value
            )


selected_date = st.selectbox(
    "📅 Вибрати день:",
    available_dates
)


# ============================================================
# КНОПКИ
# ============================================================

col1, col2 = st.columns(2)


with col1:

    settings_button = st.button(
        "⚙️ Налаштування",
        use_container_width=True
    )


with col2:

    delete_button = st.button(
        "🗑️ Видалити останній",
        use_container_width=True
    )


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

if settings_button:

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


# ============================================================
# ВИДАЛИТИ ОСТАННІЙ
# ============================================================

if (
    delete_button
    and not df_data.empty
):

    last_row = (
        df_data
        .iloc[-1:]
        .to_dict(
            orient="records"
        )
    )


    try:

        with open(
            TRASH_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                last_row,
                f,
                ensure_ascii=False,
                indent=2,
                default=str
            )

    except Exception:
        pass


    df_data = (
        df_data.iloc[:-1]
        .reset_index(drop=True)
    )


    df_data.to_excel(
        EXCEL_FILE,
        index=False
    )


    st.rerun()


# ============================================================
# ФОРМА НАЛАШТУВАНЬ
# ============================================================

if st.session_state[
    "edit_mode"
]:

    st.subheader(
        "⚙️ Налаштування"
    )


    e_cal = st.number_input(
        "🎯 Ціль калорій",
        min_value=0,
        value=int(
            user_settings.get(
                "calories",
                2000
            )
        ),
        step=10
    )


    e_prot = st.number_input(
        "🥩 Ціль білків (г)",
        min_value=0,
        value=int(
            user_settings.get(
                "protein",
                160
            )
        ),
        step=5
    )


    e_fat = st.number_input(
        "🥑 Ціль жирів (г)",
        min_value=0,
        value=int(
            user_settings.get(
                "fat",
                70
            )
        ),
        step=5
    )


    e_carb = st.number_input(
        "🍞 Ціль вуглеводів (г)",
        min_value=0,
        value=int(
            user_settings.get(
                "carbs",
                180
            )
        ),
        step=5
    )


    e_bmr = st.number_input(
        "🔥 Добова витрата BMR (ккал)",
        min_value=0,
        value=int(
            user_settings.get(
                "bmr_daily",
                1850
            )
        ),
        step=50
    )


    e_initial_weight = (
        st.number_input(
            "⚖️ Початкова вага (кг)",
            min_value=0.0,
            value=float(
                user_settings.get(
                    "initial_weight",
                    89.0
                )
            ),
            step=0.1
        )
    )


    e_exercise = st.checkbox(
        "💪 Враховувати тренування у дефіциті",

        value=user_settings.get(
            "include_exercise_in_deficit",
            True
        )
    )


    if st.button(
        "💾 Зберегти налаштування",
        type="primary",
        use_container_width=True
    ):

        save_settings(
            {
                "calories":
                    e_cal,

                "protein":
                    e_prot,

                "fat":
                    e_fat,

                "carbs":
                    e_carb,

                "bmr_daily":
                    e_bmr,

                "initial_weight":
                    e_initial_weight,

                "include_exercise_in_deficit":
                    e_exercise
            }
        )


        st.session_state[
            "edit_mode"
        ] = False


        st.rerun()


# ============================================================
# ДАНІ ВИБРАНОГО ДНЯ
# ============================================================

if not df_data.empty:

    day_df = df_data[
        df_data["Дата"]
        .astype(str)
        ==
        selected_date
    ].copy()

else:

    day_df = empty_dataframe()


# ============================================================
# СТАТИСТИКА
# ============================================================

if not day_df.empty:

    # --------------------------------------------------------
    # ЧИСЛА
    # --------------------------------------------------------

    consumed = (
        pd.to_numeric(
            day_df["Спожито"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )


    explicit_burned = (
        pd.to_numeric(
            day_df["Спалено"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )


    protein = (
        pd.to_numeric(
            day_df["Білки"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )


    fat = (
        pd.to_numeric(
            day_df["Жири"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )


    carbs = (
        pd.to_numeric(
            day_df["Вуглеводи"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )


    # --------------------------------------------------------
    # BMR
    # --------------------------------------------------------

    bmr_total = float(
        user_settings.get(
            "bmr_daily",
            1850
        )
    )


    now = datetime.now(
        LOCAL_TZ
    )


    if selected_date == today_str:

        hours_passed = (
            now.hour
            +
            now.minute / 60
        )


        bmr_elapsed = (
            bmr_total / 24
        ) * hours_passed

    else:

        bmr_elapsed = (
            bmr_total
        )


    # --------------------------------------------------------
    # ЗАГАЛЬНА ВИТРАТА
    # --------------------------------------------------------

    if user_settings.get(
        "include_exercise_in_deficit",
        True
    ):

        total_burned = (
            bmr_elapsed
            +
            explicit_burned
        )

    else:

        total_burned = (
            bmr_elapsed
        )


    # --------------------------------------------------------
    # БАЛАНС
    #
    # burned - consumed
    #
    # > 0 = дефіцит
    # < 0 = профіцит
    # --------------------------------------------------------

    balance = (
        total_burned
        -
        consumed
    )


    if balance > 0:

        balance_label = (
            "ДЕФІЦИТ"
        )

        balance_icon = (
            "📉"
        )

        balance_class = (
            "deficit"
        )

        balance_text = (
            f"-{abs(balance):.0f} ккал"
        )


    elif balance < 0:

        balance_label = (
            "ПРОФІЦИТ"
        )

        balance_icon = (
            "📈"
        )

        balance_class = (
            "surplus"
        )

        balance_text = (
            f"+{abs(balance):.0f} ккал"
        )


    else:

        balance_label = (
            "БАЛАНС"
        )

        balance_icon = (
            "⚖️"
        )

        balance_class = (
            "neutral"
        )

        balance_text = (
            "0 ккал"
        )


    # ========================================================
    # ПОТОЧНА ВАГА
    # ========================================================

    calculated_weight = (
        calculate_current_weight(
            df_data,
            user_settings
        )
    )


    # ========================================================
    # ЗАГОЛОВОК
    # ========================================================

    st.markdown(
        f"""
### 📅 {selected_date}

**⚖️ Поточна вага:
~{calculated_weight:.1f} кг**
"""
    )


    # ========================================================
    # DONUT MACROS
    # ========================================================

    total_macros = (
        protein
        +
        fat
        +
        carbs
    )


    if total_macros > 0:

        protein_deg = (
            protein
            /
            total_macros
            *
            360
        )


        fat_deg = (
            protein_deg
            +
            fat
            /
            total_macros
            *
            360
        )


        carbs_deg = 360

    else:

        protein_deg = 0

        fat_deg = 0

        carbs_deg = 360


    # ========================================================
    # БЕЗПЕЧНИЙ ТЕКСТ ДЛЯ HTML
    # ========================================================

    safe_date = html.escape(
        str(selected_date)
    )


    # ========================================================
    # DONUT HTML
    # ========================================================

    donut_html = f"""
<div class="donut-container">

    <div
        class="donut-ring"
        style="
            background:
            conic-gradient(
                #36A2EB
                0deg
                {protein_deg:.2f}deg,

                #FFCE56
                {protein_deg:.2f}deg
                {fat_deg:.2f}deg,

                #FF6384
                {fat_deg:.2f}deg
                {carbs_deg:.2f}deg
            );
        "
    >

        <div class="donut-hole">

            <span
                class="{balance_class}"
                style="
                    font-size:13px;
                    font-weight:800;
                    margin-bottom:4px;
                "
            >
                {balance_icon}
                {balance_label}
            </span>


            <b
                class="{balance_class}"
                style="
                    font-size:22px;
                    line-height:1.1;
                "
            >
                {balance_text}
            </b>


            <span
                style="
                    font-size:10px;
                    color:#aaaaaa;
                    margin-top:7px;
                "
            >
                🍽️ {int(consumed)}
                /
                {int(user_settings["calories"])}
                ккал
            </span>


            <span
                style="
                    font-size:10px;
                    color:#aaaaaa;
                    margin-top:3px;
                "
            >
                🔥 {int(total_burned)}
                ккал
            </span>


            <span
                style="
                    font-size:10px;
                    color:#aaaaaa;
                    margin-top:3px;
                "
            >
                ⚖️ {calculated_weight:.1f}
                кг
            </span>

        </div>

    </div>


    <div class="macros-row">

        <span style="color:#36A2EB;">
            🥩
            {protein:.0f}
            /
            {int(user_settings["protein"])}
            г
        </span>


        <span style="color:#FFCE56;">
            🥑
            {fat:.0f}
            /
            {int(user_settings["fat"])}
            г
        </span>


        <span style="color:#FF6384;">
            🍞
            {carbs:.0f}
            /
            {int(user_settings["carbs"])}
            г
        </span>

    </div>

</div>
"""


    # ========================================================
    # ВИВІД DONUT
    # ========================================================

    st.markdown(
        donut_html,
        unsafe_allow_html=True
    )


    # ========================================================
    # ДОДАТКОВА ІНФОРМАЦІЯ
    # ========================================================

    info_html = f"""
<div class="food-box">

    <div style="
        display:flex;
        justify-content:space-between;
        gap:10px;
        flex-wrap:wrap;
    ">

        <span>
            🍽️ Спожито:
            <b>{consumed:.0f}</b> ккал
        </span>

        <span>
            🔥 Спалено:
            <b>{total_burned:.0f}</b> ккал
        </span>

        <span>
            ⚖️ Баланс:
            <b>{balance_text}</b>
        </span>

    </div>

</div>
"""


    st.markdown(
        info_html,
        unsafe_allow_html=True
    )


    # ========================================================
    # ЛОГ
    # ========================================================

    log_lines = []


    for _, row in day_df.iterrows():

        time_value = html.escape(
            str(row.get("Час", ""))[:5]
        )


        description = html.escape(
            str(row.get("Опис", ""))
        )


        entry_type = str(
            row.get("Тип", "Їжа")
        )


        if entry_type == "Тренування":

            icon = "💪"

            kcal = int(
                float(
                    row.get(
                        "Спалено",
                        0
                    )
                    or 0
                )
            )

        else:

            icon = "🍽️"

            kcal = int(
                float(
                    row.get(
                        "Спожито",
                        0
                    )
                    or 0
                )
            )


        log_lines.append(
            f"""
<div class="log-item">

    <div class="log-left">

        {time_value}
        {icon}
        {description}

    </div>


    <div class="log-right">

        {kcal} ккал

    </div>

</div>
"""
        )


    log_html = f"""
<div class="food-box">

    <b>📝 Лог за {safe_date}</b>

    <br>

    {"".join(log_lines)}

</div>
"""


    st.markdown(
        log_html,
        unsafe_allow_html=True
    )


# ============================================================
# ПОРОЖНІЙ ДЕНЬ
# ============================================================

else:

    calculated_weight = (
        calculate_current_weight(
            df_data,
            user_settings
        )
    )


    st.markdown(
        f"""
### 📅 {selected_date}

**⚖️ Поточна вага:
~{calculated_weight:.1f} кг**
"""
    )


    # --------------------------------------------------------
    # Порожній donut
    # --------------------------------------------------------

    empty_donut = """
<div class="donut-container">

    <div
        class="donut-ring"
        style="
            background:
            conic-gradient(
                #333333 0deg 360deg
            );
        "
    >

        <div class="donut-hole">

            <span
                style="
                    font-size:13px;
                    font-weight:800;
                    color:#aaaaaa;
                "
            >
                ⚖️ БАЛАНС
            </span>


            <b
                style="
                    font-size:21px;
                    color:#ffffff;
                "
            >
                0 ккал
            </b>


            <span
                style="
                    font-size:10px;
                    color:#888888;
                    margin-top:5px;
                "
            >
                🍽️ 0 ккал
            </span>


            <span
                style="
                    font-size:10px;
                    color:#888888;
                    margin-top:3px;
                "
            >
                🔥 0 ккал
            </span>


            <span
                style="
                    font-size:10px;
                    color:#888888;
                    margin-top:3px;
                "
            >
                ⚖️
                """
    + f"""
                {calculated_weight:.1f}
                кг
            </span>

        </div>

    </div>

</div>
"""


    st.markdown(
        empty_donut,
        unsafe_allow_html=True
    )


    st.info(
        f"За {selected_date} "
        "ще немає записів. "
        "Додайте їжу або тренування вище."
    )
