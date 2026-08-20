import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
from io import StringIO

from google import genai
from google.genai import types


# ============================================================
# ОСНОВНІ НАЛАШТУВАННЯ
# ============================================================

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=2))


st.set_page_config(
    page_title="Калорійний трекер",
    page_icon="⚖️",
    layout="centered"
)


IMAGE_URL = (
    "https://i.postimg.cc/kMS67m1J/"
    "Screenshot-20260819-175524-Facebook.jpg"
)

# Gemini саме 3.6
GEMINI_MODEL = "gemini-3.6-flash"

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


# ============================================================
# ПРОФІЛЬ
# ============================================================

user_profile = st.sidebar.selectbox(
    "👤 Профіль",
    ["Я", "Дружина"]
)

profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
WATCH_FILE = f"watch_calories_{profile_prefix}.json"
UNDO_FILE = f"fitness_undo_{profile_prefix}.json"


# ============================================================
# CSS
# ============================================================

st.markdown(
    f"""
<style>

.stApp {{
    background:
        linear-gradient(
            rgba(0,0,0,.78),
            rgba(0,0,0,.88)
        ),
        url("{IMAGE_URL}");

    background-size: cover;
    background-attachment: fixed;
    background-position: center;
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


/* ---------------- КАРТКИ ---------------- */

.card {{
    background: rgba(15,18,25,.90);
    border: 1px solid rgba(255,255,255,.14);
    border-radius: 18px;
    padding: 18px;
    margin: 12px 0;
    box-shadow: 0 8px 30px rgba(0,0,0,.25);
}}


/* ---------------- ЗАГОЛОВКИ ---------------- */

.section-title {{
    font-size: 1.35rem;
    font-weight: 800;
    margin: 18px 0 10px;
}}

.small {{
    color: #aeb4c0;
    font-size: .9rem;
}}


/* ---------------- КРУЖОК ---------------- */

.donut-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
}}

.donut {{
    width: 230px;
    height: 230px;

    border-radius: 50%;

    display: flex;
    align-items: center;
    justify-content: center;

    box-shadow:
        0 0 28px rgba(0,0,0,.5);
}}

.donut-hole {{
    width: 158px;
    height: 158px;

    border-radius: 50%;

    background: #10131a;

    display: flex;
    flex-direction: column;

    align-items: center;
    justify-content: center;

    text-align: center;
}}

.donut-main {{
    font-size: 1.65rem;
    font-weight: 900;
    line-height: 1.1;
}}

.donut-status {{
    font-size: .95rem;
    font-weight: 800;
    margin-top: 6px;
}}

.donut-sub {{
    color: #aeb4c0;
    font-size: .78rem;
    margin-top: 4px;
}}


/* ---------------- Б/Ж/В ---------------- */

.stats {{
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 8px;

    width: 100%;
    margin-top: 10px;
}}

.stat {{
    background: rgba(255,255,255,.06);
    border-radius: 12px;
    padding: 10px 5px;
    text-align: center;
}}

.stat b {{
    display: block;
    font-size: .92rem;
    margin-top: 4px;
}}


/* ---------------- ВЛОГ ---------------- */

.log-card {{
    background: rgba(12,15,21,.86);

    border: 1px solid rgba(255,255,255,.12);

    border-radius: 16px;

    padding: 15px;

    margin: 10px 0;
}}

.log-top {{
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: flex-start;
}}

.log-desc {{
    font-weight: 700;
    white-space: pre-wrap;
    word-break: break-word;
    margin-top: 5px;
}}

.log-kcal {{
    font-weight: 900;
    white-space: nowrap;
}}


/* ---------------- КНОПКИ ---------------- */

[data-testid="stButton"] button {{
    border-radius: 14px;

    min-height: 44px;

    font-weight: 750;

    border: 1px solid rgba(255,255,255,.16);

    transition: .12s ease;
}}

[data-testid="stButton"] button:hover {{
    transform: translateY(-1px);

    border-color:
        rgba(255,255,255,.3);
}}

[data-testid="stButton"] button:active {{
    transform:
        translateY(1px)
        scale(.98);
}}


/* ---------------- МОБІЛЬНИЙ ЕКРАН ---------------- */

@media (max-width: 600px) {{

    .donut {{
        width: 210px;
        height: 210px;
    }}

    .donut-hole {{
        width: 145px;
        height: 145px;
    }}

    .stats {{
        font-size: .8rem;
    }}

}}

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "editor_open" not in st.session_state:
    st.session_state["editor_open"] = False

if "settings_open" not in st.session_state:
    st.session_state["settings_open"] = False


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

def default_settings():
    return {
        "calories": 2000,
        "protein": 160,
        "fat": 70,
        "carbs": 180,
        "bmr_daily": 1850,
        "initial_weight": 89.0,
    }


def load_settings():

    settings = default_settings()

    if os.path.exists(SETTINGS_FILE):

        try:

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                settings.update(
                    json.load(f)
                )

        except Exception:
            pass

    return settings


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
# DATAFRAME
# ============================================================

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

        for column in COLUMNS:

            if column not in df.columns:

                if column in [
                    "Дата",
                    "Час",
                    "Опис",
                    "Тип"
                ]:
                    df[column] = ""

                else:
                    df[column] = 0

        return df[COLUMNS]

    except Exception:

        return empty_df()


def save_data(df):

    df.to_excel(
        EXCEL_FILE,
        index=False
    )


# ============================================================
# КАЛОРІЇ З ГОДИННИКА
# ============================================================

def load_watch():

    if os.path.exists(WATCH_FILE):

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
            pass

    return {}


def save_watch(watch):

    with open(
        WATCH_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            watch,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# UNDO — ДО 10 ДІЙ
# ============================================================

def load_undo():

    if os.path.exists(UNDO_FILE):

        try:

            with open(
                UNDO_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:
            pass

    return []


def save_undo(stack):

    with open(
        UNDO_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            stack[-10:],
            f,
            ensure_ascii=False
        )


def make_snapshot(df, watch):

    return {
        "data": df.to_json(
            orient="split",
            force_ascii=False
        ),
        "watch": watch,
    }


def restore_snapshot(saved):

    if saved.get("data"):

        df = pd.read_json(
            StringIO(
                saved["data"]
            ),
            orient="split"
        )

    else:

        df = empty_df()

    for column in COLUMNS:

        if column not in df.columns:

            if column in [
                "Дата",
                "Час",
                "Опис",
                "Тип"
            ]:
                df[column] = ""

            else:
                df[column] = 0

    df = df[COLUMNS]

    watch = {
        str(k): float(v)
        for k, v in saved.get(
            "watch",
            {}
        ).items()
    }

    return df, watch


def push_undo(df, watch):

    stack = load_undo()

    stack.append(
        make_snapshot(
            df,
            watch
        )
    )

    save_undo(stack)


def undo_last():

    stack = load_undo()

    if not stack:
        return False

    previous = stack.pop()

    old_df, old_watch = restore_snapshot(
        previous
    )

    save_data(old_df)
    save_watch(old_watch)
    save_undo(stack)

    return True


# ============================================================
# ДОПОМІЖНЕ
# ============================================================

def num(value):

    try:
        return float(
            value or 0
        )

    except Exception:
        return 0.0


# ============================================================
# РОЗРАХУНОК ВАГИ
# ============================================================

def calculate_current_weight(
    df,
    settings,
    watch
):

    initial_weight = float(
        settings["initial_weight"]
    )

    if df.empty and not watch:
        return initial_weight

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    total_balance = 0.0

    dates = set(
        watch.keys()
    )

    if not df.empty:

        dates |= set(
            df["Дата"].astype(str)
        )

    for date in dates:

        if not df.empty:

            day = df[
                df["Дата"].astype(str)
                == date
            ]

        else:

            day = empty_df()

        if not day.empty:

            eaten = pd.to_numeric(
                day["Спожито"],
                errors="coerce"
            ).fillna(0).sum()

            training = pd.to_numeric(
                day["Спалено"],
                errors="coerce"
            ).fillna(0).sum()

        else:

            eaten = 0
            training = 0

        if date == today:

            now = datetime.now(
                LOCAL_TZ
            )

            hours = (
                now.hour
                + now.minute / 60
            )

            bmr = (
                float(
                    settings["bmr_daily"]
                )
                * hours
                / 24
            )

        else:

            bmr = float(
                settings["bmr_daily"]
            )

        watch_burned = float(
            watch.get(date, 0)
        )

        total_balance += (
            bmr
            + watch_burned
            + training
            - eaten
        )

    return (
        initial_weight
        - total_balance / 7700
    )


# ============================================================
# СТАТИСТИКА ДНЯ
# ============================================================

def day_totals(
    df,
    date,
    watch,
    settings
):

    if not df.empty:

        day = df[
            df["Дата"].astype(str)
            == date
        ].copy()

    else:

        day = empty_df()

    if not day.empty:

        eaten = pd.to_numeric(
            day["Спожито"],
            errors="coerce"
        ).fillna(0).sum()

        training = pd.to_numeric(
            day["Спалено"],
            errors="coerce"
        ).fillna(0).sum()

        protein = pd.to_numeric(
            day["Білки"],
            errors="coerce"
        ).fillna(0).sum()

        fat = pd.to_numeric(
            day["Жири"],
            errors="coerce"
        ).fillna(0).sum()

        carbs = pd.to_numeric(
            day["Вуглеводи"],
            errors="coerce"
        ).fillna(0).sum()

    else:

        eaten = 0
        training = 0
        protein = 0
        fat = 0
        carbs = 0

    today = datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")

    if date == today:

        now = datetime.now(
            LOCAL_TZ
        )

        hours = (
            now.hour
            + now.minute / 60
        )

        bmr = (
            float(
                settings["bmr_daily"]
            )
            * hours
            / 24
        )

    else:

        bmr = float(
            settings["bmr_daily"]
        )

    watch_burned = float(
        watch.get(date, 0)
    )

    burned = (
        bmr
        + watch_burned
        + training
    )

    return (
        eaten,
        burned,
        protein,
        fat,
        carbs,
        training
    )


# ============================================================
# ЗАВАНТАЖЕННЯ
# ============================================================

settings = load_settings()
df = load_data()
watch = load_watch()


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    "⚖️ Калорійний трекер"
)

st.caption(
    f"📅 "
    f"{datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')}"
    f"  |  "
    f"Поточна вага: "
    f"~{calculate_current_weight(df, settings, watch):.1f} кг"
)


# ============================================================
# ВІДМІНИТИ
# ============================================================

if st.button(
    "↩️ Відмінити останню дію",
    use_container_width=True
):

    if undo_last():

        st.rerun()

    else:

        st.info(
            "Немає дій для відміни. "
            "Зберігається до 10 останніх дій."
        )


# ============================================================
# ВИДАЛИТИ ОСТАННІЙ
# ============================================================

if st.button(
    "🗑️ Видалити останній запис",
    use_container_width=True
):

    if not df.empty:

        push_undo(
            df,
            watch
        )

        df = df.iloc[:-1].reset_index(
            drop=True
        )

        save_data(df)

        st.rerun()

    else:

        st.info(
            "Записів немає."
        )


# ============================================================
# ВИБІР ДНЯ
# ============================================================

all_dates = {
    datetime.now(
        LOCAL_TZ
    ).strftime("%Y-%m-%d")
}

if not df.empty:

    all_dates |= set(
        df["Дата"].astype(str)
    )

all_dates |= set(
    watch.keys()
)

selected_date = st.selectbox(
    "📅 День",
    sorted(
        all_dates,
        reverse=True
    )
)


# ============================================================
# ДЕННА СТАТИСТИКА
# ============================================================

(
    eaten,
    burned,
    protein,
    fat,
    carbs,
    training
) = day_totals(
    df,
    selected_date,
    watch,
    settings
)

balance = burned - eaten


if balance >= 0:

    status = (
        f"Дефіцит: "
        f"{abs(balance):.0f} ккал"
    )

    status_color = "#35d07f"

else:

    status = (
        f"Профіцит: "
        f"{abs(balance):.0f} ккал"
    )

    status_color = "#ff6384"


# ============================================================
# КРУЖОК
# ============================================================

if settings["calories"]:

    progress = min(
        max(
            eaten
            / float(settings["calories"]),
            0
        ),
        1
    )

else:

    progress = 0


end = progress * 360


if progress <= 0:

    gradient = (
        "#303542 0deg 360deg"
    )

elif progress < 1:

    gradient = (
        f"#36A2EB 0deg "
        f"{end:.1f}deg, "
        f"#303542 "
        f"{end:.1f}deg "
        f"360deg"
    )

else:

    gradient = (
        "#35d07f 0deg 360deg"
    )


st.markdown(
    f"""
<div class="card">

    <div class="donut-wrap">

        <div
            class="donut"
            style="
                background:
                conic-gradient(
                    {gradient}
                );
            "
        >

            <div class="donut-hole">

                <div
                    class="donut-status"
                    style="
                        color:{status_color};
                    "
                >
                    {status}
                </div>

                <div class="donut-main">
                    {eaten:.0f}
                </div>

                <div class="donut-sub">
                    з'їдено з
                    {float(settings['calories']):.0f}
                    ккал
                </div>

            </div>

        </div>


        <div class="stats">

            <div class="stat">
                🥩 Білки
                <b>
                    {protein:.0f}
                    /
                    {settings['protein']} г
                </b>
            </div>

            <div class="stat">
                🥑 Жири
                <b>
                    {fat:.0f}
                    /
                    {settings['fat']} г
                </b>
            </div>

            <div class="stat">
                🍞 Вуглеводи
                <b>
                    {carbs:.0f}
                    /
                    {settings['carbs']} г
                </b>
            </div>

        </div>

    </div>

</div>
""",
    unsafe_allow_html=True
)


# ============================================================
# ГОДИННИК
# ============================================================

st.markdown(
    '<div class="section-title">'
    '⌚ Калорії з годинника'
    '</div>',
    unsafe_allow_html=True
)

with st.form("watch_form"):

    watch_value = st.number_input(
        "Спалено за цей день, ккал",
        min_value=0.0,
        value=float(
            watch.get(
                selected_date,
                0
            )
        ),
        step=10.0,
        format="%.0f"
    )

    watch_submit = st.form_submit_button(
        "⌚ Оновити",
        use_container_width=True
    )


if watch_submit:

    push_undo(
        df,
        watch
    )

    # ВАЖЛИВО:
    # не додаємо, а ЗАМІНЮЄМО
    watch[selected_date] = float(
        watch_value
    )

    save_watch(watch)

    st.rerun()


# ============================================================
# ДОДАТИ ЇЖУ
# ============================================================

st.markdown(
    '<div class="section-title">'
    '🍽️ Додати їжу'
    '</div>',
    unsafe_allow_html=True
)

with st.form(
    "food_form",
    clear_on_submit=True
):

    food_text = st.text_area(
        "Продукт / страва",
        placeholder=(
            "Наприклад: "
            "плов з куркою 350 г, "
            "чорний хліб 2 скибки, "
            "2 яйця"
        ),
        height=90
    )

    manual_kcal = st.number_input(
        "Калорії вручну "
        "(0 = Gemini)",
        min_value=0.0,
        value=0.0,
        step=10.0,
        format="%.0f"
    )

    food_submit = st.form_submit_button(
        "✅ Додати",
        use_container_width=True
    )


if food_submit and food_text.strip():

    try:

        api_key = (
            st.secrets.get(
                "GEMINI_API_KEY"
            )
            or os.environ.get(
                "GEMINI_API_KEY"
            )
        )

        if (
            manual_kcal <= 0
            and not api_key
        ):

            st.error(
                "Немає GEMINI_API_KEY. "
                "Або вкажи калорії вручну."
            )

        else:

            push_undo(
                df,
                watch
            )

            # -------------------------
            # РУЧНІ КАЛОРІЇ
            # -------------------------

            if manual_kcal > 0:

                items = [
                    {
                        "name":
                            food_text.strip(),

                        "kcal":
                            manual_kcal,

                        "protein":
                            0,

                        "fat":
                            0,

                        "carbs":
                            0
                    }
                ]

            # -------------------------
            # GEMINI
            # -------------------------

            else:

                client = genai.Client(
                    api_key=api_key
                )

                prompt = f"""
Оціни їжу:

{food_text.strip()}

Поверни ТІЛЬКИ JSON:

{{
  "items": [
    {{
      "name": "назва продукту",
      "kcal": 0,
      "protein": 0,
      "fat": 0,
      "carbs": 0
    }}
  ]
}}

Правила:

1. Кожен окремий продукт
   повинен бути окремим item.

2. kcal — калорії.

3. protein — білки в грамах.

4. fat — жири в грамах.

5. carbs — вуглеводи в грамах.

6. Усі значення числа.

7. Без markdown.
"""

                response = (
                    client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                )

                parsed = json.loads(
                    response.text
                )

                items = parsed.get(
                    "items",
                    []
                )


            if not items:

                raise ValueError(
                    "Gemini не повернув "
                    "список продуктів"
                )


            lines = []

            total_kcal = 0.0
            total_p = 0.0
            total_f = 0.0
            total_c = 0.0


            for item in items:

                name = str(
                    item.get(
                        "name",
                        "Продукт"
                    )
                ).strip()

                kcal = num(
                    item.get("kcal")
                )

                p = num(
                    item.get("protein")
                )

                f = num(
                    item.get("fat")
                )

                c = num(
                    item.get("carbs")
                )


                # КОЖЕН ПРОДУКТ МАЄ
                # СВОЇ КАЛОРІЇ

                lines.append(
                    f"🍽️ {name} — "
                    f"{kcal:.0f} ккал"
                )


                total_kcal += kcal
                total_p += p
                total_f += f
                total_c += c


            now = datetime.now(
                LOCAL_TZ
            )


            new_row = pd.DataFrame(
                [
                    {
                        "Дата":
                            selected_date,

                        "Час":
                            now.strftime(
                                "%H:%M"
                            ),

                        "Опис":
                            "\n".join(lines),

                        "Тип":
                            "Їжа",

                        "Спожито":
                            total_kcal,

                        "Спалено":
                            0,

                        "Білки":
                            total_p,

                        "Жири":
                            total_f,

                        "Вуглеводи":
                            total_c,
                    }
                ]
            )


            df = pd.concat(
                [
                    df,
                    new_row
                ],
                ignore_index=True
            )


            save_data(df)

            # clear_on_submit=True
            # очищає поле

            st.rerun()


    except Exception as exc:

        st.error(
            f"Помилка Gemini: {exc}"
        )


# ============================================================
# ТРЕНУВАННЯ
# ============================================================

st.markdown(
    '<div class="section-title">'
    '💪 Додати тренування'
    '</div>',
    unsafe_allow_html=True
)

with st.form(
    "training_form",
    clear_on_submit=True
):

    training_name = st.text_input(
        "Назва",
        placeholder=(
            "Ходьба, зал, біг..."
        )
    )

    training_kcal = st.number_input(
        "Спалено, ккал",
        min_value=0.0,
        value=0.0,
        step=10.0,
        format="%.0f"
    )

    training_submit = (
        st.form_submit_button(
            "✅ Додати тренування",
            use_container_width=True
        )
    )


if (
    training_submit
    and training_kcal > 0
):

    push_undo(
        df,
        watch
    )

    now = datetime.now(
        LOCAL_TZ
    )

    row = {
        "Дата":
            selected_date,

        "Час":
            now.strftime("%H:%M"),

        "Опис":
            training_name
            or "Тренування",

        "Тип":
            "Тренування",

        "Спожито":
            0,

        "Спалено":
            float(training_kcal),

        "Білки":
            0,

        "Жири":
            0,

        "Вуглеводи":
            0,
    }


    df = pd.concat(
        [
            df,
            pd.DataFrame([row])
        ],
        ignore_index=True
    )


    save_data(df)

    st.rerun()


# ============================================================
# НАЛАШТУВАННЯ
# ============================================================

settings_label = (
    "🔽 Налаштування"
    if st.session_state["settings_open"]
    else "▶️ Налаштування"
)


if st.button(
    settings_label,
    use_container_width=True,
    type=(
        "primary"
        if st.session_state["settings_open"]
        else "secondary"
    )
):

    st.session_state[
        "settings_open"
    ] = not st.session_state[
        "settings_open"
    ]

    st.rerun()


if st.session_state["settings_open"]:

    with st.form(
        "settings_form"
    ):

        target_cal = st.number_input(
            "Добова норма калорій",
            min_value=0.0,
            value=float(
                settings["calories"]
            ),
            step=50.0
        )

        target_protein = st.number_input(
            "Білки, г/добу",
            min_value=0.0,
            value=float(
                settings["protein"]
            ),
            step=5.0
        )

        target_fat = st.number_input(
            "Жири, г/добу",
            min_value=0.0,
            value=float(
                settings["fat"]
            ),
            step=5.0
        )

        target_carbs = st.number_input(
            "Вуглеводи, г/добу",
            min_value=0.0,
            value=float(
                settings["carbs"]
            ),
            step=5.0
        )

        bmr = st.number_input(
            "Базова витрата ккал/добу",
            min_value=0.0,
            value=float(
                settings["bmr_daily"]
            ),
            step=50.0
        )

        initial_weight = st.number_input(
            "Початкова вага, кг",
            min_value=0.0,
            value=float(
                settings["initial_weight"]
            ),
            step=0.1
        )

        settings_submit = (
            st.form_submit_button(
                "💾 Зберегти",
                use_container_width=True
            )
        )


    if settings_submit:

        push_undo(
            df,
            watch
        )

        save_settings(
            {
                "calories":
                    target_cal,

                "protein":
                    target_protein,

                "fat":
                    target_fat,

                "carbs":
                    target_carbs,

                "bmr_daily":
                    bmr,

                "initial_weight":
                    initial_weight,
            }
        )

        st.rerun()


# ============================================================
# РЕДАКТОР
# ============================================================

editor_label = (
    "🔽 Редактор"
    if st.session_state["editor_open"]
    else "▶️ Редактор"
)


if st.button(
    editor_label,
    use_container_width=True,
    type=(
        "primary"
        if st.session_state["editor_open"]
        else "secondary"
    )
):

    st.session_state[
        "editor_open"
    ] = not st.session_state[
        "editor_open"
    ]

    st.rerun()


if st.session_state["editor_open"]:

    st.markdown(
        """
<div class="small">
Змінюєш поле → натискаєш «Зберегти».
Всі калорії, Б/Ж/В,
дефіцит/профіцит і вага
перераховуються автоматично.
</div>
""",
        unsafe_allow_html=True
    )


    if not df.empty:

        day_indices = [
            i
            for i in df.index
            if str(
                df.at[i, "Дата"]
            ) == selected_date
        ]

    else:

        day_indices = []


    for i in reversed(day_indices):

        title = (
            str(
                df.at[
                    i,
                    "Опис"
                ]
            )
            .replace("\n", " ")
            [:45]
        )


        with st.expander(
            f"{str(df.at[i, 'Час'])[:5]} · {title}"
        ):

            with st.form(
                f"edit_{i}"
            ):

                desc = st.text_area(
                    "Опис",
                    value=str(
                        df.at[
                            i,
                            "Опис"
                        ]
                    ),
                    key=f"desc_{i}"
                )

                kcal = st.number_input(
                    "З'їдено, ккал",
                    min_value=0.0,
                    value=num(
                        df.at[
                            i,
                            "Спожито"
                        ]
                    ),
                    step=10.0,
                    key=f"k_{i}"
                )

                burn = st.number_input(
                    "Спалено, ккал",
                    min_value=0.0,
                    value=num(
                        df.at[
                            i,
                            "Спалено"
                        ]
                    ),
                    step=10.0,
                    key=f"b_{i}"
                )

                edit_protein = st.number_input(
                    "Білки, г",
                    min_value=0.0,
                    value=num(
                        df.at[
                            i,
                            "Білки"
                        ]
                    ),
                    step=1.0,
                    key=f"p_{i}"
                )

                edit_fat = st.number_input(
                    "Жири, г",
                    min_value=0.0,
                    value=num(
                        df.at[
                            i,
                            "Жири"
                        ]
                    ),
                    step=1.0,
                    key=f"f_{i}"
                )

                edit_carbs = st.number_input(
                    "Вуглеводи, г",
                    min_value=0.0,
                    value=num(
                        df.at[
                            i,
                            "Вуглеводи"
                        ]
                    ),
                    step=1.0,
                    key=f"c_{i}"
                )

                save_btn = (
                    st.form_submit_button(
                        "💾 Зберегти",
                        use_container_width=True
                    )
                )


            delete_btn = st.button(
                "🗑️ Видалити цей запис",
                key=f"delete_{i}",
                use_container_width=True
            )


            if save_btn:

                push_undo(
                    df,
                    watch
                )

                df.at[
                    i,
                    "Опис"
                ] = desc

                df.at[
                    i,
                    "Спожито"
                ] = kcal

                df.at[
                    i,
                    "Спалено"
                ] = burn

                df.at[
                    i,
                    "Білки"
                ] = edit_protein

                df.at[
                    i,
                    "Жири"
                ] = edit_fat

                df.at[
                    i,
                    "Вуглеводи"
                ] = edit_carbs

                if (
                    burn > 0
                    and kcal == 0
                ):

                    df.at[
                        i,
                        "Тип"
                    ] = "Тренування"

                else:

                    df.at[
                        i,
                        "Тип"
                    ] = "Їжа"


                save_data(df)

                st.rerun()


            if delete_btn:

                push_undo(
                    df,
                    watch
                )

                df = (
                    df
                    .drop(index=i)
                    .reset_index(
                        drop=True
                    )
                )

                save_data(df)

                st.rerun()


# ============================================================
# ВЛОГ
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📋 Влог'
    '</div>',
    unsafe_allow_html=True
)


if not df.empty:

    log_day = df[
        df["Дата"].astype(str)
        == selected_date
    ].copy()

else:

    log_day = empty_df()


if log_day.empty:

    st.info(
        "Записів ще немає. "
        "Додай їжу або тренування."
    )

else:

    for _, row in log_day.iloc[::-1].iterrows():

        is_training = (
            str(row["Тип"])
            == "Тренування"
        )

        if is_training:

            icon = "💪"

            value = num(
                row["Спалено"]
            )

            sign = "−"

        else:

            icon = "🍽️"

            value = num(
                row["Спожито"]
            )

            sign = "+"


        description = str(
            row["Опис"]
        )


        st.markdown(
            f"""
<div class="log-card">

    <div class="log-top">

        <div>

            <b>
                {str(row["Час"])[:5]}
                {icon}
            </b>

            <div class="log-desc">
                {description}
            </div>

        </div>

        <div class="log-kcal">
            {sign}{value:.0f} ккал
        </div>

    </div>

</div>
""",
            unsafe_allow_html=True
        )


# ============================================================
# ПІДСУМОК
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📊 Підсумок'
    '</div>',
    unsafe_allow_html=True
)


st.markdown(
    f"""
<div class="card">

    <div class="kcal-line">
        🍽️ З'їдено:
        {eaten:.0f} ккал
    </div>

    <div class="kcal-line">
        🔥 Всього спалено:
        {burned:.0f} ккал
    </div>

    <div
        class="kcal-line"
        style="color:{status_color};"
    >
        {
            "📉"
            if balance >= 0
            else "📈"
        }
        {status}
    </div>

</div>
""",
    unsafe_allow_html=True
)
