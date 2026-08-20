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

    #MainMenu, footer, header {{
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

    /* ОДНАКОВА ВИСОТА ВСІХ КНОПОК */
    div.stButton > button {{
        min-height: 46px !important;
        height: 46px !important;
        border-radius: 10px !important;
        white-space: normal !important;
        line-height: 1.2 !important;
    }}

    div.stButton > button p {{
        margin: 0 !important;
        line-height: 1.2 !important;
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


# ============================================================
# GEMINI API
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
# WEIGHT
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
# LOAD DATA
# ============================================================

def load_data():

    if os.path.exists(EXCEL_FILE):

        try:

            df = pd.read_excel(EXCEL_FILE)

            if "Час" not in df.columns:

                df["Час"] = datetime.now(
                    LOCAL_TZ
                ).strftime("%H:%M")

            else:

                df["Час"] = df["Час"].fillna(
                    datetime.now(
                        LOCAL_TZ
                    ).strftime("%H:%M")
                )

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

    include_exercise = bool(
        settings.get(
            "include_exercise_in_deficit",
            True
        )
    )

    if df.empty:
        return initial_weight

    work_df = df.copy()

    work_df["Дата"] = (
        work_df["Дата"]
        .astype(str)
    )

    for column in [
        "Спожито",
        "Спалено"
    ]:

        work_df[column] = pd.to_numeric(
            work_df[column],
            errors="coerce"
        ).fillna(0)

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    now = datetime.now(
        LOCAL_TZ
    )

    accumulated_balance = 0.0

    unique_dates = sorted(
        work_df["Дата"].unique()
    )

    for date_str in unique_dates:

        day_df = work_df[
            work_df["Дата"] == date_str
        ]

        consumed_day = float(
            day_df["Спожито"].sum()
        )

        active_burned_day = float(
            day_df["Спалено"].sum()
        )

        if date_str == today:

            hours_passed = (
                now.hour
                + now.minute / 60
                + now.second / 3600
            )

            bmr_for_day = (
                bmr_daily / 24
            ) * hours_passed

        else:

            bmr_for_day = bmr_daily

        if include_exercise:

            total_burned_day = (
                bmr_for_day
                + active_burned_day
            )

        else:

            total_burned_day = bmr_for_day

        daily_balance = (
            total_burned_day
            - consumed_day
        )

        accumulated_balance += daily_balance

    weight_change = (
        accumulated_balance / 7700
    )

    calculated_weight = (
        initial_weight
        - weight_change
    )

    return max(
        0.0,
        calculated_weight
    )


# ============================================================
# ЗАВАНТАЖЕННЯ
# ============================================================

user_settings = load_settings()
w_data = load_weight()
df_data = load_data()

calculated_weight = calculate_current_weight(
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
# GEMINI LOG
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
# BUTTONS
# ============================================================

btn_settings = st.button(
    "⚙️ Налаштування",
    use_container_width=True
)

btn_del = st.button(
    "🗑️ Видалити останній запис",
    use_container_width=True
)

has_trash = os.path.exists(
    TRASH_FILE
)

btn_back = st.button(
    "🔄 Повернути",
    disabled=not has_trash,
    use_container_width=True
)


# ============================================================
# SETTINGS BUTTON
# ============================================================

if btn_settings:

    st.session_state[
        "edit_mode"
    ] = not st.session_state[
        "edit_mode"
    ]

    st.rerun()


# ============================================================
# DELETE LAST
# ============================================================

if btn_del:

    if not df_data.empty:

        last_row = (
            df_data.iloc[-1:]
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


# ============================================================
# RESTORE
# ============================================================

if btn_back and has_trash:

    try:

        with open(
            TRASH_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            restored = json.load(f)

        df_data = pd.concat(
            [
                df_data,
                pd.DataFrame(restored)
            ],
            ignore_index=True
        )

        df_data.to_excel(
            EXCEL_FILE,
            index=False
        )

        os.remove(
            TRASH_FILE
        )

        st.rerun()

    except Exception as e:

        st.error(
            f"Помилка відновлення: {e}"
        )


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
                "initial_weight": e_initial_weight,
                "include_exercise_in_deficit": (
                    e_include_exercise
                )
            }

            save_settings(
                new_settings
            )

            save_weight({
                "current_weight":
                    e_initial_weight
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
# DISPLAY DAY
# ============================================================

if not day_df.empty:

    consumed = float(
        day_df["Спожито"].sum()
    )

    explicit_burned = float(
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

    bmr_total = float(
        user_settings.get(
            "bmr_daily",
            1850
        )
    )

    include_exercise = bool(
        user_settings.get(
            "include_exercise_in_deficit",
            True
        )
    )


    # --------------------------------------------------------
    # BMR
    # --------------------------------------------------------

    if selected_date == today_str:

        hours_passed = (
            now.hour
            + now.minute / 60
            + now.second / 3600
        )

        bmr_used = (
            bmr_total / 24
        ) * hours_passed

    else:

        bmr_used = bmr_total


    # --------------------------------------------------------
    # ACTIVE CALORIES
    # --------------------------------------------------------

    if include_exercise:

        total_burned = (
            bmr_used
            + explicit_burned
        )

    else:

        total_burned = bmr_used


    # --------------------------------------------------------
    # BALANCE
    # --------------------------------------------------------

    balance = (
        total_burned
        - consumed
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
    # BALANCE TEXT
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
    # DATE + WEIGHT
    # ========================================================

    st.markdown(
        f"**📅 {selected_date} | "
        f"Вага (розрахункова): "
        f"{calculated_weight:.1f} кг**"
    )


    # ========================================================
    # MACROS
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


    # ========================================================
    # DONUT
    # ========================================================

    st.markdown(
f"""<div class="donut-container">
<div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg);">
<div class="donut-hole">
<span style="font-size: 10px; color: {balance_color};">{balance_label}: {balance_text}</span>
<b style="font-size: 14px;">{int(consumed)} / {target_cal}</b>
<span style="font-size: 9px; color: #888;">ккал</span>
</div>
</div>
<div class="macros-row">
<span style="color: #36A2EB;">🥩 Білки: {protein:.0f} / {target_p}г</span>
<span style="color: #FFCE56;">🥑 Жири: {fat:.0f} / {target_f}г</span>
<span style="color: #FF6384;">🍞 Вугл: {carbs:.0f} / {target_c}г</span>
</div>
</div>""",
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
            f'<div class="log-item">'
            f'<div class="log-left">'
            f'{t_val} {icon} {desc}'
            f'</div>'
            f'<div class="log-right">'
            f'<b>{kcal} ккал</b>'
            f'</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="food-box">'
        f'<b>📝 Лог:</b><br>'
        f'{"".join(log_html_lines)}'
        f'</div>',
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

            advice_resp = (
                client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=(
                        f"Аналіз за {selected_date}: "
                        f"{consumed} ккал, "
                        f"{protein}г білків. "
                        f"Коротка порада."
                    )
                )
            )

            st.markdown(
                f'<div class="advice-box">'
                f'<b>💡 Порада:</b><br>'
                f'{advice_resp.text}'
                f'</div>',
                unsafe_allow_html=True
            )

        except Exception as e:

            st.error(
                f"Помилка Gemini: {e}"
            )


    # ========================================================
    # CLEAR SELECTED DAY
    # ========================================================

    if st.button(
        "⚠️ Очистити цей день",
        use_container_width=True
    ):

        df_data = df_data[
            df_data["Дата"].astype(str)
            != selected_date
        ]

        df_data.to_excel(
            EXCEL_FILE,
            index=False
        )

        st.rerun()


else:

    st.info(
        f"За цей день ({selected_date}) "
        f"ще немає записів."
    )
