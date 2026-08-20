import os
import json
import html
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
# CSS STREAMLIT
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


#MainMenu,
footer,
header {{
    visibility: hidden;
}}


/* ==========================================================
   КНОПКИ
   ========================================================== */

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

    color: #ffffff !important;

    font-weight: 700 !important;

    box-shadow:
        0 7px 20px
        rgba(0,0,0,0.35);

    transition:
        all 0.18s ease;
}}


div.stButton > button:hover {{
    transform:
        translateY(-2px);

    border-color:
        rgba(54,162,235,0.65) !important;

    box-shadow:
        0 10px 28px
        rgba(0,0,0,0.45);
}}


div.stButton > button:active {{
    transform:
        translateY(0);
}}


/* ==========================================================
   INPUT
   ========================================================== */

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {{
    border-radius:
        12px !important;

    background:
        rgba(18,18,22,0.94) !important;

    color:
        #ffffff !important;
}}


/* ==========================================================
   КАРТКИ
   ========================================================== */

.food-box,
.advice-box {{
    background:
        rgba(20,20,20,0.90);

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


/* ==========================================================
   ЛОГ
   ========================================================== */

.log-item {{
    display:
        flex;

    justify-content:
        space-between;

    align-items:
        flex-start;

    border-bottom:
        1px solid
        rgba(255,255,255,0.08);

    padding:
        9px 0;

    font-size:
        14px;
}}


.log-item:last-child {{
    border-bottom:
        none;
}}


.log-left {{
    word-break:
        break-word;

    flex-grow:
        1;

    margin-right:
        10px;
}}


.log-right {{
    white-space:
        nowrap;

    font-weight:
        bold;

    color:
        #36A2EB;
}}


/* ==========================================================
   ЗАГОЛОВКИ
   ========================================================== */

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

for key, default_value in [
    ("edit_mode", False),
    ("open_camera", False)
]:
    if key not in st.session_state:
        st.session_state[key] = default_value


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
        "⚠️ Не знайдено GEMINI_API_KEY!"
    )

    st.info(
        "Додай GEMINI_API_KEY у "
        "Streamlit Secrets."
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
# РОЗРАХУНОК ВАГИ
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


    for date_str in work_df["Дата"].unique():

        day_df = work_df[
            work_df["Дата"] == date_str
        ]


        consumed = float(
            day_df["Спожито"].sum()
        )


        exercise_burned = float(
            day_df["Спалено"].sum()
        )


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

            bmr_for_day = bmr_daily


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

            total_burned = bmr_for_day


        total_balance += (
            total_burned
            -
            consumed
        )


    # 7700 ккал ≈ 1 кг
    weight_change = (
        total_balance / 7700
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


captured_image = None


if st.session_state["open_camera"]:

    captured_image = st.camera_input(
        "Зробити фото"
    )


# ============================================================
# ЗАПИС
# ============================================================

submit_btn = st.button(
    "✅ Записати в лог",
    type="primary",
    use_container_width=True
)


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

        # ----------------------------------------------------
        # ФОТО
        # ----------------------------------------------------

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
Проаналізуй фото.

Це може бути їжа або тренування.

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

Якщо це їжа:
- total_consumed_kcal > 0
- kcal_burned = 0

Якщо це тренування:
- kcal_burned > 0
- total_consumed_kcal = 0

Білки, жири та вуглеводи
вказуй у грамах.

Якщо значення невідоме —
використовуй 0.

Поверни тільки JSON.
"""


            response = (
                client.models.generate_content(
                    model="gemini-3.5-flash",
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


        # ----------------------------------------------------
        # ТЕКСТ
        # ----------------------------------------------------

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

Якщо це їжа:
- total_consumed_kcal > 0
- kcal_burned = 0

Якщо це тренування:
- kcal_burned > 0
- total_consumed_kcal = 0

Білки, жири та вуглеводи
вказуй у грамах.

Якщо значення невідоме —
використовуй 0.

Поверни тільки JSON.
"""


            response = (
                client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type=(
                            "application/json"
                        )
                    )
                )
            )


        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        response_text = (
            response.text or ""
        ).strip()


        data = json.loads(
            response_text
        )


        consumed_value = float(
            data.get(
                "total_consumed_kcal",
                0
            ) or 0
        )


        burned_value = float(
            data.get(
                "kcal_burned",
                0
            ) or 0
        )


        protein_value = float(
            data.get(
                "total_protein",
                0
            ) or 0
        )


        fat_value = float(
            data.get(
                "total_fat",
                0
            ) or 0
        )


        carbs_value = float(
            data.get(
                "total_carbs",
                0
            ) or 0
        )


        description = (
            data.get(
                "food_description"
            )
            or user_input
            or "Запис"
        )


        entry_type = (
            "Тренування"
            if burned_value > 0
            else "Їжа"
        )


        # ----------------------------------------------------
        # НОВИЙ РЯДОК
        # ----------------------------------------------------

        new_entry = pd.DataFrame(
            [{
                "Дата":
                    current_date_str,

                "Час":
                    current_time_str,

                "Опис":
                    description,

                "Тип":
                    entry_type,

                "Спожито":
                    consumed_value,

                "Спалено":
                    burned_value,

                "Білки":
                    protein_value,

                "Жири":
                    fat_value,

                "Вуглеводи":
                    carbs_value
            }]
        )


        df_data = pd.concat(
            [
                df_data,
                new_entry
            ],
            ignore_index=True
        )


        # ----------------------------------------------------
        # ЗБЕРІГАЄМО
        # ----------------------------------------------------

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

        if "response_text" in locals():

            st.code(
                response_text
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

    for d in sorted(
        df_data["Дата"]
        .astype(str)
        .unique(),
        reverse=True
    ):

        if d not in available_dates:

            available_dates.append(d)


selected_date = st.selectbox(
    "📅 Вибрати день:",
    available_dates
)


# ============================================================
# КНОПКИ
# ============================================================

col_b1, col_b2 = st.columns(2)


with col_b1:

    btn_settings = st.button(
        "⚙️ Налаштування",
        use_container_width=True
    )


with col_b2:

    btn_del = st.button(
        "🗑️ Видалити останній",
        use_container_width=True
    )


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

if btn_settings:

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


# ============================================================
# ВИДАЛЕННЯ
# ============================================================

if (
    btn_del
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
        df_data
        .iloc[:-1]
        .reset_index(drop=True)
    )


    df_data.to_excel(
        EXCEL_FILE,
        index=False
    )


    st.rerun()


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

if st.session_state["edit_mode"]:

    st.subheader(
        "⚙️ Налаштування"
    )


    e_cal = st.number_input(
        "🎯 Ціль калорій",
        min_value=0,
        value=int(
            user_settings["calories"]
        ),
        step=10
    )


    e_prot = st.number_input(
        "🥩 Ціль білків (г)",
        min_value=0,
        value=int(
            user_settings["protein"]
        ),
        step=5
    )


    e_fat = st.number_input(
        "🥑 Ціль жирів (г)",
        min_value=0,
        value=int(
            user_settings["fat"]
        ),
        step=5
    )


    e_carb = st.number_input(
        "🍞 Ціль вуглеводів (г)",
        min_value=0,
        value=int(
            user_settings["carbs"]
        ),
        step=5
    )


    e_bmr = st.number_input(
        "🔥 Добова витрата BMR",
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
        "💪 Враховувати тренування "
        "у дефіциті",

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

        bmr_elapsed = bmr_total


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

        total_burned = bmr_elapsed


    # --------------------------------------------------------
    # БАЛАНС
    #
    # burned - consumed
    #
    # + = дефіцит
    # - = профіцит
    # --------------------------------------------------------

    balance = (
        total_burned
        -
        consumed
    )


    if balance > 0:

        balance_label = "ДЕФІЦИТ"
        balance_icon = "📉"
        balance_color = "#35D07F"
        balance_text = (
            f"−{abs(balance):.0f} ккал"
        )

    elif balance < 0:

        balance_label = "ПРОФІЦИТ"
        balance_icon = "📈"
        balance_color = "#FF6262"
        balance_text = (
            f"+{abs(balance):.0f} ккал"
        )

    else:

        balance_label = "БАЛАНС"
        balance_icon = "⚖️"
        balance_color = "#FFD166"
        balance_text = "0 ккал"


    # --------------------------------------------------------
    # ПОТОЧНА ВАГА
    # --------------------------------------------------------

    calculated_weight = (
        calculate_current_weight(
            df_data,
            user_settings
        )
    )


    # --------------------------------------------------------
    # ЗАГОЛОВОК
    # --------------------------------------------------------

    st.markdown(
        f"""
### 📅 {selected_date}

**⚖️ Поточна вага:
~{calculated_weight:.1f} кг**
"""
    )


    # ========================================================
    # МАКРОСИ
    # ========================================================

    total_macros = (
        protein
        +
        fat
        +
        carbs
    )


    if total_macros > 0:

        p_deg = (
            protein
            /
            total_macros
            *
            360
        )


        f_deg = (
            p_deg
            +
            fat
            /
            total_macros
            *
            360
        )


        c_deg = 360

    else:

        p_deg = 0
        f_deg = 0
        c_deg = 360


    # ========================================================
    # БЕЗПЕЧНІ ЗНАЧЕННЯ ДЛЯ HTML
    # ========================================================

    safe_balance_label = html.escape(
        balance_label
    )

    safe_balance_icon = html.escape(
        balance_icon
    )

    safe_balance_text = html.escape(
        balance_text
    )


    # ========================================================
    # СПРАВЖНІЙ HTML DONUT
    #
    # ВАЖЛИВО:
    # НЕ st.markdown()
    #
    # components.html() створює HTML iframe,
    # тому HTML НЕ показується текстом.
    # ========================================================

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


.container {{

    width: 250px;

    min-height: 280px;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

}}


/* ========================================================
   КРУГ
   ======================================================== */

.donut {{

    width: 205px;
    height: 205px;

    border-radius: 50%;

    background:
        conic-gradient(
            #36A2EB
            0deg
            {p_deg:.2f}deg,

            #FFCE56
            {p_deg:.2f}deg
            {f_deg:.2f}deg,

            #FF6384
            {f_deg:.2f}deg
            {c_deg:.2f}deg
        );

    display: flex;

    align-items: center;
    justify-content: center;

    box-shadow:
        0 0 28px
        rgba(0,0,0,0.65);

}}


/* ========================================================
   ЦЕНТР
   ======================================================== */

.hole {{

    width: 146px;
    height: 146px;

    border-radius: 50%;

    background:
        #15171c;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    text-align: center;

    box-shadow:
        inset 0 0 24px
        rgba(0,0,0,0.8);

}}


.status {{

    color:
        {balance_color};

    font-size:
        13px;

    font-weight:
        900;

    margin-bottom:
        5px;

}}


.balance {{

    color:
        {balance_color};

    font-size:
        22px;

    font-weight:
        900;

    line-height:
        1.1;

}}


.food {{

    color:
        #aaaaaa;

    font-size:
        10px;

    margin-top:
        8px;

}}


.burn {{

    color:
        #aaaaaa;

    font-size:
        10px;

    margin-top:
        3px;

}}


.weight {{

    color:
        #ffffff;

    font-size:
        10px;

    font-weight:
        700;

    margin-top:
        4px;

}}


/* ========================================================
   МАКРОСИ
   ======================================================== */

.macros {{

    width:
        205px;

    margin-top:
        10px;

    padding:
        8px 0;

    display:
        flex;

    justify-content:
        space-around;

    border-radius:
        11px;

    background:
        rgba(20,20,20,0.95);

    border:
        1px solid
        rgba(255,255,255,0.10);

    font-size:
        10px;

    font-weight:
        800;

}}


.protein {{
    color: #36A2EB;
}}


.fat {{
    color: #FFCE56;
}}


.carbs {{
    color: #FF6384;
}}

</style>

</head>


<body>

<div class="container">


    <div class="donut">


        <div class="hole">


            <div class="status">

                {safe_balance_icon}
                {safe_balance_label}

            </div>


            <div class="balance">

                {safe_balance_text}

            </div>


            <div class="food">

                🍽️ {consumed:.0f}
                /
                {int(user_settings["calories"])}
                ккал

            </div>


            <div class="burn">

                🔥 {total_burned:.0f} ккал

            </div>


            <div class="weight">

                ⚖️ {calculated_weight:.1f} кг

            </div>


        </div>


    </div>


    <div class="macros">


        <span class="protein">

            🥩
            {protein:.0f}
            /
            {int(user_settings["protein"])}г

        </span>


        <span class="fat">

            🥑
            {fat:.0f}
            /
            {int(user_settings["fat"])}г

        </span>


        <span class="carbs">

            🍞
            {carbs:.0f}
            /
            {int(user_settings["carbs"])}г

        </span>


    </div>


</div>

</body>

</html>
"""


    # ========================================================
    # ВИВІД СПРАВЖНЬОГО КРУЖКА
    # ========================================================

    components.html(
        donut_html,
        height=300,
        scrolling=False
    )


    # ========================================================
    # ІНФОРМАЦІЙНА КАРТКА
    # ========================================================

    balance_sign = (
        "−"
        if balance > 0
        else "+"
        if balance < 0
        else ""
    )


    st.markdown(
        f"""
<div class="food-box">

    <div style="
        display:flex;
        justify-content:space-around;
        gap:10px;
        flex-wrap:wrap;
        text-align:center;
    ">

        <span>
            🍽️<br>
            <b>{consumed:.0f}</b><br>
            ккал
        </span>


        <span>
            🔥<br>
            <b>{total_burned:.0f}</b><br>
            ккал
        </span>


        <span>
            {balance_icon}<br>
            <b style="color:{balance_color};">
                {balance_sign}{abs(balance):.0f}
            </b><br>
            {balance_label.lower()}
        </span>


        <span>
            ⚖️<br>
            <b>{calculated_weight:.1f}</b><br>
            кг
        </span>

    </div>

</div>
""",
        unsafe_allow_html=True
    )


    # ========================================================
    # ЛОГ
    # ========================================================

    log_lines = []


    for _, row in day_df.iterrows():

        t_val = html.escape(
            str(row.get("Час", ""))[:5]
        )


        description = html.escape(
            str(row.get("Опис", ""))
        )


        row_type = str(
            row.get(
                "Тип",
                "Їжа"
            )
        )


        if row_type == "Тренування":

            icon = "💪"

            kcal = int(
                float(
                    row.get(
                        "Спалено",
                        0
                    ) or 0
                )
            )

        else:

            icon = "🍽️"

            kcal = int(
                float(
                    row.get(
                        "Спожито",
                        0
                    ) or 0
                )
            )


        log_lines.append(
            f"""
<div class="log-item">

    <div class="log-left">

        {t_val}
        {icon}
        {description}

    </div>


    <div class="log-right">

        {kcal} ккал

    </div>

</div>
"""
        )


    st.markdown(
        f"""
<div class="food-box">

    <b>📝 Лог за {selected_date}</b>

    <br>

    {"".join(log_lines)}

</div>
""",
        unsafe_allow_html=True
    )


# ============================================================
# ЯКЩО ДЕНЬ ПОРОЖНІЙ
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
    # Порожній круг
    # --------------------------------------------------------

    empty_html = f"""
<!DOCTYPE html>

<html>

<head>

<style>

html,
body {{

    margin: 0;
    padding: 0;

    background: transparent;

}}


body {{

    height: 290px;

    display: flex;

    align-items: center;

    justify-content: center;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

}}


.wrapper {{

    display: flex;

    flex-direction: column;

    align-items: center;

}}


.donut {{

    width: 205px;
    height: 205px;

    border-radius: 50%;

    background:
        conic-gradient(
            #333333
            0deg 360deg
        );

    display: flex;

    align-items: center;
    justify-content: center;

    box-shadow:
        0 0 25px
        rgba(0,0,0,0.65);

}}


.hole {{

    width: 146px;
    height: 146px;

    border-radius: 50%;

    background:
        #15171c;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    text-align: center;

}}


.title {{

    color:
        #aaaaaa;

    font-size:
        13px;

    font-weight:
        800;

}}


.value {{

    color:
        #ffffff;

    font-size:
        21px;

    font-weight:
        900;

    margin-top:
        5px;

}}


.weight {{

    color:
        #aaaaaa;

    font-size:
        10px;

    margin-top:
        7px;

}}

</style>

</head>


<body>

<div class="wrapper">

    <div class="donut">

        <div class="hole">

            <div class="title">
                ⚖️ БАЛАНС
            </div>

            <div class="value">
                0 ккал
            </div>

            <div class="weight">
                ⚖️ {calculated_weight:.1f} кг
            </div>

        </div>

    </div>

</div>

</body>

</html>
"""


    components.html(
        empty_html,
        height=290,
        scrolling=False
    )


    st.info(
        f"За {selected_date} "
        "ще немає записів. "
        "Додайте їжу або тренування вище."
)
