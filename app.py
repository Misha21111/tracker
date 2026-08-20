import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
from google import genai
from google.genai import types

# =========================
# ЧАСОВИЙ ПОЯС
# =========================
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


st.set_page_config(
    page_title="Мій Фітнес",
    page_icon="🏋️",
    layout="centered"
)


# =========================
# ВИБІР ПРОФІЛЮ
# =========================
user_profile = st.sidebar.selectbox(
    "👤 Оберіть профіль:",
    ["Я", "Дружина"]
)

profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
WEIGHT_FILE = f"weight_data_{profile_prefix}.json"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"

IMAGE_URL = "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"


# =========================
# CSS
# =========================
st.markdown(
    f"""
    <style>

    .stApp {{
        background-image:
            linear-gradient(
                rgba(0, 0, 0, 0.76),
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

    /* -------------------------
       КНОПКИ
    ------------------------- */

    div.stButton > button {{
        border-radius: 14px !important;
        min-height: 46px !important;

        border: 1px solid rgba(255,255,255,.12) !important;

        background:
            linear-gradient(
                135deg,
                rgba(45,45,52,.98),
                rgba(20,20,25,.98)
            ) !important;

        color: white !important;

        font-weight: 700 !important;

        box-shadow:
            0 6px 18px rgba(0,0,0,.25);

        transition:
            all .18s ease;
    }}

    div.stButton > button:hover {{
        transform: translateY(-2px);

        border-color:
            rgba(54,162,235,.65) !important;

        box-shadow:
            0 10px 25px rgba(0,0,0,.35),
            0 0 15px rgba(54,162,235,.12);
    }}

    div.stButton > button:active {{
        transform: translateY(0);
    }}

    div.stButton > button[kind="primary"] {{
        background:
            linear-gradient(
                135deg,
                #36A2EB,
                #1976D2
            ) !important;

        border: none !important;

        box-shadow:
            0 8px 22px
            rgba(54,162,235,.30);
    }}

    div.stButton > button[kind="primary"]:hover {{
        box-shadow:
            0 12px 30px
            rgba(54,162,235,.42);
    }}


    /* -------------------------
       INPUT
    ------------------------- */

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{
        border-radius: 12px !important;

        background:
            rgba(18,18,22,.90) !important;

        color: white !important;
    }}


    /* -------------------------
       METRICS / BOXES
    ------------------------- */

    div[data-testid="stMetric"],
    div[data-testid="stMarkdownContainer"] {{
        color: white;
    }}

    .food-box,
    .advice-box {{
        background:
            rgba(20,20,20,.88);

        border:
            1px solid rgba(255,255,255,.10);

        border-radius: 14px;

        padding:
            12px 16px;

        color: white;

        margin-top: 10px;
    }}

    .advice-box {{
        border-left:
            4px solid #36A2EB;
    }}


    /* -------------------------
       DONUT
    ------------------------- */

    .donut-container {{
        display:
            flex;

        flex-direction:
            column;

        align-items:
            center;

        justify-content:
            center;

        margin:
            20px 0;
    }}

    .donut-ring {{
        width:
            205px;

        height:
            205px;

        border-radius:
            50%;

        display:
            flex;

        justify-content:
            center;

        align-items:
            center;

        box-shadow:
            0 0 25px
            rgba(0,0,0,.75);
    }}

    .donut-hole {{
        width:
            142px;

        height:
            142px;

        background:
            #141414;

        border-radius:
            50%;

        display:
            flex;

        flex-direction:
            column;

        justify-content:
            center;

        align-items:
            center;

        text-align:
            center;

        color:
            white;

        box-shadow:
            inset 0 0 20px
            rgba(0,0,0,.65);
    }}

    .deficit {{
        color:
            #35D07F;
    }}

    .surplus {{
        color:
            #FF6B6B;
    }}

    .neutral {{
        color:
            #FFD166;
    }}


    /* -------------------------
       MACROS
    ------------------------- */

    .macros-row {{
        display:
            flex;

        justify-content:
            space-around;

        width:
            100%;

        max-width:
            350px;

        margin-top:
            14px;

        font-size:
            11px;

        background:
            rgba(20,20,20,.92);

        padding:
            9px 6px;

        border-radius:
            12px;

        border:
            1px solid
            rgba(255,255,255,.10);
    }}


    /* -------------------------
       LOG
    ------------------------- */

    .log-item {{
        display:
            flex;

        justify-content:
            space-between;

        align-items:
            flex-start;

        border-bottom:
            1px solid
            rgba(255,255,255,.08);

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

    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# SESSION STATE
# =========================
for key, default_val in [
    ("show_advice", False),
    ("advice_text", ""),
    ("edit_mode", False),
    ("open_camera", False),
    ("edit_log_mode", False),
    ("confirm_clear_day", False),
]:

    if key not in st.session_state:
        st.session_state[key] = default_val


# =========================
# GEMINI
# =========================
api_key = (
    st.secrets.get("GEMINI_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
)

if not api_key:
    st.error("⚠️ Не знайдено API ключ GEMINI_API_KEY!")
    st.stop()

client = genai.Client(api_key=api_key)


# =========================
# НАЛАШТУВАННЯ
# =========================
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

                return {
                    **default,
                    **json.load(f)
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


# =========================
# ЗАВАНТАЖЕННЯ ДАНИХ
# =========================
def load_data():

    empty_df = pd.DataFrame(
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

    if os.path.exists(EXCEL_FILE):

        try:

            df = pd.read_excel(EXCEL_FILE)

            if "Час" not in df.columns:

                df["Час"] = (
                    datetime.now(LOCAL_TZ)
                    .strftime("%H:%M")
                )

            return df

        except Exception:

            return empty_df

    return empty_df


# =========================
# РОЗРАХУНОК ВАГИ
# =========================
def calculate_current_weight(df, settings):

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

    today = (
        datetime.now(LOCAL_TZ)
        .strftime("%Y-%m-%d")
    )

    now = datetime.now(LOCAL_TZ)

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

        # Для сьогоднішнього дня беремо
        # тільки BMR за вже минулий час.
        if date_str == today:

            hours_passed = (
                now.hour +
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
                bmr_for_day +
                exercise_burned
            )

        else:

            total_burned = bmr_for_day

        # Позитивне число = дефіцит.
        # Негативне = профіцит.
        total_balance += (
            total_burned -
            consumed
        )

    # 7700 ккал ≈ 1 кг.
    weight_change = (
        total_balance /
        7700.0
    )

    current_weight = (
        initial_weight -
        weight_change
    )

    return max(
        0.0,
        current_weight
    )


# =========================
# ЗАПУСК
# =========================
user_settings = load_settings()

df_data = load_data()

calculated_weight = calculate_current_weight(
    df_data,
    user_settings
)


# =========================
# ЗАГОЛОВОК
# =========================
st.title(
    f"🏋️ Фітнес: {user_profile}"
)


# =========================
# ВВІД
# =========================
user_input = st.text_input(
    "📥 Що з'їв / тренування:",
    placeholder="Наприклад: з'їв 30г хліба"
)


# =========================
# КАМЕРА
# =========================
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


captured_image = st.camera_input(
    "Зробити фото"
) if st.session_state["open_camera"] else None


submit_btn = st.button(
    "✅ Записати в лог",
    type="primary",
    use_container_width=True
)


# =========================
# ОБРОБКА ЗАПИСУ
# =========================
if submit_btn and (
    user_input or
    captured_image
):

    current_time_str = (
        datetime.now(LOCAL_TZ)
        .strftime("%H:%M")
    )

    current_date_str = (
        datetime.now(LOCAL_TZ)
        .strftime("%Y-%m-%d")
    )

    try:

        if captured_image:

            image_bytes = (
                captured_image.getvalue()
            )

            image_part = (
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                )
            )

            prompt = """
            Проаналізуй страву на фото.
            Поверни суворо JSON з ключами:
            food_description,
            kcal_burned,
            total_consumed_kcal,
            total_protein,
            total_fat,
            total_carbs.
            """

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

            prompt = f'''
            Аналізуй: "{user_input}".

            Поверни суворо JSON з ключами:
            food_description,
            kcal_burned,
            total_consumed_kcal,
            total_protein,
            total_fat,
            total_carbs.
            '''

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

        burned = float(
            data.get("kcal_burned") or 0
        )

        consumed = float(
            data.get("total_consumed_kcal") or 0
        )

        new_entry = pd.DataFrame(
            [{
                "Дата":
                    current_date_str,

                "Час":
                    current_time_str,

                "Опис":
                    data.get(
                        "food_description"
                    )
                    or user_input
                    or "Запис",

                "Тип":
                    "Тренування"
                    if burned > 0
                    else "Їжа",

                "Спожито":
                    consumed,

                "Спалено":
                    burned,

                "Білки":
                    float(
                        data.get(
                            "total_protein"
                        ) or 0
                    ),

                "Жири":
                    float(
                        data.get(
                            "total_fat"
                        ) or 0
                    ),

                "Вуглеводи":
                    float(
                        data.get(
                            "total_carbs"
                        ) or 0
                    )
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
            f"Помилка обробки: {e}"
        )


st.divider()


# =========================
# ДНІ
# =========================
today_str = (
    datetime.now(LOCAL_TZ)
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


# =========================
# КНОПКИ
# =========================
col_b1, col_b2 = st.columns(2)


with col_b1:

    btn_settings = st.button(
        "⚙️ Налаштування",
        use_container_width=True
    )


with col_b2:

    btn_del = st.button(
        "🗑️ Видалити останній запис",
        use_container_width=True
    )


if btn_settings:

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


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

    with open(
        TRASH_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            last_row,
            f,
            ensure_ascii=False
        )

    df_data = df_data.iloc[:-1]

    df_data.to_excel(
        EXCEL_FILE,
        index=False
    )

    st.rerun()


# =========================
# НАЛАШТУВАННЯ
# =========================
if st.session_state["edit_mode"]:

    st.subheader(
        "⚙️ Налаштування цілей"
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

    e_initial_weight = st.number_input(
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

    if st.button(
        "💾 Зберегти цілі",
        type="primary",
        use_container_width=True
    ):

        save_settings(
            {
                "calories": e_cal,
                "protein": e_prot,
                "fat": e_fat,
                "carbs": e_carb,
                "bmr_daily":
                    user_settings.get(
                        "bmr_daily",
                        1850
                    ),
                "initial_weight":
                    e_initial_weight,
                "include_exercise_in_deficit":
                    True
            }
        )

        st.session_state[
            "edit_mode"
        ] = False

        st.rerun()


# =========================
# СТАТИСТИКА ДНЯ
# =========================
if not df_data.empty:

    day_df = df_data[
        df_data["Дата"].astype(str)
        == selected_date
    ]

else:

    day_df = pd.DataFrame()


if not day_df.empty:

    consumed = pd.to_numeric(
        day_df["Спожито"],
        errors="coerce"
    ).fillna(0).sum()

    explicit_burned = pd.to_numeric(
        day_df["Спалено"],
        errors="coerce"
    ).fillna(0).sum()

    protein = pd.to_numeric(
        day_df["Білки"],
        errors="coerce"
    ).fillna(0).sum()

    fat = pd.to_numeric(
        day_df["Жири"],
        errors="coerce"
    ).fillna(0).sum()

    carbs = pd.to_numeric(
        day_df["Вуглеводи"],
        errors="coerce"
    ).fillna(0).sum()


    # =========================
    # BMR + ТРЕНУВАННЯ
    # =========================

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
            now.hour +
            now.minute / 60
        )

        bmr_elapsed = (
            bmr_total / 24
        ) * hours_passed

    else:

        bmr_elapsed = bmr_total


    total_burned = (
        bmr_elapsed +
        explicit_burned
    )


    # =========================
    # ДЕФІЦИТ / ПРОФІЦИТ
    # =========================

    balance = (
        total_burned -
        consumed
    )


    if balance > 0:

        balance_label = "ДЕФІЦИТ"

        balance_class = "deficit"

        balance_icon = "📉"

        balance_text = (
            f"-{abs(balance):.0f} ккал"
        )

    elif balance < 0:

        balance_label = "ПРОФІЦИТ"

        balance_class = "surplus"

        balance_icon = "📈"

        balance_text = (
            f"+{abs(balance):.0f} ккал"
        )

    else:

        balance_label = "БАЛАНС"

        balance_class = "neutral"

        balance_icon = "⚖️"

        balance_text = "0 ккал"


    # =========================
    # ВАГА
    # =========================

    calculated_weight = (
        calculate_current_weight(
            df_data,
            user_settings
        )
    )


    st.markdown(
        f"""
        **📅 {selected_date}
        | Поточна вага:
        ~{calculated_weight:.1f} кг**
        """
    )


    # =========================
    # MACROS DONUT
    # =========================

    total_macros = (
        protein +
        fat +
        carbs
    )


    if total_macros > 0:

        p_deg = (
            protein /
            total_macros *
            360
        )

        f_deg = (
            p_deg +
            fat /
            total_macros *
            360
        )

        c_deg = (
            f_deg +
            carbs /
            total_macros *
            360
        )

    else:

        p_deg = 0
        f_deg = 0
        c_deg = 360


    # =========================
    # КРУЖОК
    # =========================

    st.markdown(
        f"""
        <div class="donut-container">

            <div
                class="donut-ring"
                style="
                    background:
                    conic-gradient(
                        #36A2EB
                        0deg
                        {p_deg}deg,

                        #FFCE56
                        {p_deg}deg
                        {f_deg}deg,

                        #FF6384
                        {f_deg}deg
                        {c_deg}deg
                    );
                "
            >

                <div class="donut-hole">

                    <span
                        class="{balance_class}"
                        style="
                            font-size:13px;
                            font-weight:800;
                        "
                    >
                        {balance_icon}
                        {balance_label}
                    </span>


                    <b
                        class="{balance_class}"
                        style="
                            font-size:21px;
                            line-height:1.15;
                        "
                    >
                        {balance_text}
                    </b>


                    <span
                        style="
                            font-size:10px;
                            color:#aaa;
                            margin-top:5px;
                        "
                    >
                        {int(consumed)}
                        /
                        {user_settings['calories']}
                        ккал
                    </span>


                    <span
                        style="
                            font-size:10px;
                            color:#aaa;
                            margin-top:3px;
                        "
                    >
                        🔥
                        {int(total_burned)}
                        ккал
                    </span>


                    <span
                        style="
                            font-size:10px;
                            color:#aaa;
                            margin-top:3px;
                        "
                    >
                        ⚖️
                        <b style="color:white;">
                            {calculated_weight:.1f} кг
                        </b>
                    </span>

                </div>

            </div>


            <div class="macros-row">

                <span
                    style="color:#36A2EB;"
                >
                    🥩
                    {protein:.0f}
                    /
                    {user_settings['protein']}г
                </span>

                <span
                    style="color:#FFCE56;"
                >
                    🥑
                    {fat:.0f}
                    /
                    {user_settings['fat']}г
                </span>

                <span
                    style="color:#FF6384;"
                >
                    🍞
                    {carbs:.0f}
                    /
                    {user_settings['carbs']}г
                </span>

            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    # =========================
    # ЛОГ
    # =========================

    log_lines = []

    for _, row in day_df.iterrows():

        t_val = str(
            row["Час"]
        )[:5]

        icon = (
            "💪"
            if row["Тип"] == "Тренування"
            else "🍽️"
        )

        kcal = int(
            row["Спалено"]
            if row["Тип"] == "Тренування"
            else row["Спожито"]
        )

        log_lines.append(
            f"""
            <div class="log-item">

                <div class="log-left">
                    {t_val}
                    {icon}
                    {row["Опис"]}
                </div>

                <div class="log-right">
                    <b>
                        {kcal} ккал
                    </b>
                </div>

            </div>
            """
        )


    st.markdown(
        f"""
        <div class="food-box">

            <b>📝 Лог:</b>

            <br>

            {"".join(log_lines)}

        </div>
        """,
        unsafe_allow_html=True
    )


else:

    calculated_weight = (
        calculate_current_weight(
            df_data,
            user_settings
        )
    )

    st.markdown(
        f"""
        **📅 {selected_date}
        | Поточна вага:
        ~{calculated_weight:.1f} кг**
        """
    )

    st.info(
        "За цей день ще немає записів. "
        "Додайте перший продукт або тренування вище!"
)
