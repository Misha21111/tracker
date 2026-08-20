import streamlit as st
from datetime import datetime, date
import json

# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

st.set_page_config(
    page_title="Калорійний трекер",
    page_icon="⚖️",
    layout="centered"
)

DEFAULT_TARGET = 2000.0
DEFAULT_BMR = 1850.0
DEFAULT_WEIGHT = 89.0
UNDO_LIMIT = 10


# =========================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# =========================================================

def current_time():
    return datetime.now().strftime("%H:%M")


def current_date():
    return date.today().isoformat()


def init_state():
    defaults = {
        "entries": [],
        "clock_calories": 0.0,
        "target": DEFAULT_TARGET,
        "bmr": DEFAULT_BMR,
        "weight": DEFAULT_WEIGHT,
        "undo_stack": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def make_snapshot():
    return {
        "entries": json.loads(
            json.dumps(st.session_state.entries)
        ),
        "clock_calories": float(st.session_state.clock_calories),
        "target": float(st.session_state.target),
        "bmr": float(st.session_state.bmr),
        "weight": float(st.session_state.weight),
    }


def save_undo():
    st.session_state.undo_stack.append(make_snapshot())

    if len(st.session_state.undo_stack) > UNDO_LIMIT:
        st.session_state.undo_stack.pop(0)


def restore_snapshot(snapshot):
    st.session_state.entries = snapshot["entries"]
    st.session_state.clock_calories = snapshot["clock_calories"]
    st.session_state.target = snapshot["target"]
    st.session_state.bmr = snapshot["bmr"]
    st.session_state.weight = snapshot["weight"]


def undo_last():
    if not st.session_state.undo_stack:
        return

    snapshot = st.session_state.undo_stack.pop()
    restore_snapshot(snapshot)


def add_food(name, calories):
    name = name.strip()

    if not name:
        return False

    save_undo()

    st.session_state.entries.append({
        "id": datetime.now().timestamp(),
        "time": current_time(),
        "kind": "food",
        "title": name,
        "kcal": float(calories),
    })

    return True


def add_activity(name, calories):
    name = name.strip()

    if not name:
        name = "Тренування"

    save_undo()

    st.session_state.entries.append({
        "id": datetime.now().timestamp(),
        "time": current_time(),
        "kind": "activity",
        "title": name,
        "kcal": -abs(float(calories)),
    })


def total_eaten():
    return sum(
        item["kcal"]
        for item in st.session_state.entries
        if item["kind"] == "food"
    )


def total_manual_burned():
    return sum(
        abs(item["kcal"])
        for item in st.session_state.entries
        if item["kind"] == "activity"
    )


def total_burned():
    return (
        total_manual_burned()
        + float(st.session_state.clock_calories)
    )


def net_calories():
    return total_eaten() - total_burned()


def current_balance():
    # Позитивне число = дефіцит
    # Негативне число = профіцит
    return float(st.session_state.target) - net_calories()


def estimated_weight():
    # 7700 ккал ≈ 1 кг
    balance = current_balance()
    return float(st.session_state.weight) - balance / 7700.0


# =========================================================
# ІНІЦІАЛІЗАЦІЯ
# =========================================================

init_state()


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    html, body {
        background: #080b10;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(
                circle at top,
                rgba(55, 70, 95, 0.25),
                transparent 40%
            ),
            #080b10;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        max-width: 760px;
        padding-top: 25px;
        padding-bottom: 70px;
    }

    h1, h2, h3, p, label, span, div {
        color: #f3f4f6;
    }

    /* Кнопки */

    div.stButton > button,
    div.stFormSubmitButton > button {
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,.16) !important;
        background: rgba(27,31,41,.95) !important;
        color: #ffffff !important;
        min-height: 48px !important;
        font-weight: 700 !important;
        transition: .12s ease !important;
    }

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover {
        background: rgba(43,48,62,1) !important;
        border-color: rgba(255,255,255,.28) !important;
    }

    div.stButton > button:active,
    div.stFormSubmitButton > button:active {
        transform: scale(.97) !important;
        filter: brightness(1.25);
    }

    /* Поля */

    input,
    textarea {
        color: #ffffff !important;
    }

    [data-baseweb="input"] {
        background: #20232e !important;
        border-radius: 16px !important;
    }

    [data-baseweb="select"] > div {
        background: #20232e !important;
        border-radius: 16px !important;
    }

    /* Картка */

    .card {
        background: rgba(15,19,26,.88);
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 22px;
        padding: 18px;
        margin: 14px 0;
        box-shadow: 0 10px 35px rgba(0,0,0,.25);
    }

    /* KPI */

    .kpi {
        background: rgba(27,31,41,.95);
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 18px;
        padding: 14px 8px;
        text-align: center;
        min-height: 95px;
    }

    .kpi-number {
        font-size: 1.35rem;
        font-weight: 900;
        margin-top: 5px;
    }

    .kpi-label {
        color: #aeb5c2 !important;
        font-size: .82rem;
    }

    /* КРУЖОК */

    .donut-wrap {
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 20px 0 25px;
    }

    .donut {
        width: 285px;
        height: 285px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow:
            0 0 45px rgba(54,162,235,.12),
            0 15px 45px rgba(0,0,0,.45);
    }

    .donut-hole {
        width: 205px;
        height: 205px;
        border-radius: 50%;
        background: #10141b;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 15px;
        box-shadow: inset 0 0 25px rgba(0,0,0,.45);
    }

    .donut-status {
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .donut-main {
        font-size: 34px;
        line-height: 1.05;
        font-weight: 900;
    }

    .donut-sub {
        color: #aeb5c2 !important;
        font-size: 13px;
        margin-top: 8px;
    }

    /* Баланс */

    .balance {
        border-radius: 20px;
        padding: 18px;
        text-align: center;
        font-size: 20px;
        font-weight: 900;
        margin: 18px 0;
    }

    .deficit {
        background: rgba(39,174,96,.18);
        border: 1px solid rgba(39,174,96,.45);
    }

    .surplus {
        background: rgba(231,76,60,.18);
        border: 1px solid rgba(231,76,60,.45);
    }

    .neutral {
        background: rgba(149,165,166,.15);
        border: 1px solid rgba(149,165,166,.35);
    }

    /* Влог */

    .log {
        background: rgba(14,18,24,.88);
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 20px;
        padding: 17px;
        margin: 12px 0;
    }

    .log-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
    }

    .log-left {
        min-width: 0;
    }

    .log-time {
        color: #9fa7b4 !important;
        font-size: 13px;
        margin-bottom: 4px;
    }

    .log-title {
        font-weight: 800;
        font-size: 16px;
        overflow-wrap: anywhere;
    }

    .log-kcal {
        font-size: 18px;
        font-weight: 900;
        white-space: nowrap;
    }

    .food-kcal {
        color: #ffce56 !important;
    }

    .burn-kcal {
        color: #36a2eb !important;
    }

    .small-note {
        color: #aeb5c2 !important;
        font-size: 13px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ЗАГОЛОВОК
# =========================================================

st.title("⚖️ Калорійний трекер")

st.caption(
    f"📅 {current_date()}  |  "
    f"Поточна вага: ~{estimated_weight():.1f} кг"
)


# =========================================================
# КНОПКИ
# =========================================================

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "↩️ Відмінити",
        use_container_width=True,
        disabled=not st.session_state.undo_stack
    ):
        undo_last()
        st.rerun()

with col2:
    if st.button(
        "🗑️ Видалити останній запис",
        use_container_width=True,
        disabled=not st.session_state.entries
    ):
        save_undo()
        st.session_state.entries.pop()
        st.rerun()


# =========================================================
# РОЗРАХУНКИ
# =========================================================

eaten = total_eaten()
clock = float(st.session_state.clock_calories)
manual_burned = total_manual_burned()
burned = total_burned()
net = net_calories()
balance = current_balance()
target = float(st.session_state.target)

progress = 0.0

if target > 0:
    progress = eaten / target * 100.0

progress = max(0.0, min(progress, 100.0))

angle = progress * 3.6

second_angle = min(angle + 35.0, 360.0)

ring = (
    "conic-gradient("
    f"#36A2EB 0deg {angle:.2f}deg, "
    f"#FFCE56 {angle:.2f}deg {second_angle:.2f}deg, "
    f"#FF6384 {second_angle:.2f}deg 360deg"
)


if balance > 0.5:
    status_text = f"Дефіцит: {round(balance)} ккал"
elif balance < -0.5:
    status_text = f"Профіцит: {round(abs(balance))} ккал"
else:
    status_text = "Баланс: 0 ккал"


# =========================================================
# КРУЖОК
# =========================================================

st.markdown(
    f"""
    <div class="donut-wrap">
        <div class="donut" style="background:{ring};">
            <div class="donut-hole">

                <div class="donut-status">
                    {status_text}
                </div>

                <div class="donut-main">
                    {round(eaten)}
                </div>

                <div class="donut-sub">
                    з'їдено з {round(target)} ккал
                </div>

            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# СТАТИСТИКА
# =========================================================

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        f"""
        <div class="kpi">
            🍽️
            <div class="kpi-number">{round(eaten)}</div>
            <div class="kpi-label">з'їдено, ккал</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"""
        <div class="kpi">
            🔥
            <div class="kpi-number">{round(burned)}</div>
            <div class="kpi-label">спалено, ккал</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    st.markdown(
        f"""
        <div class="kpi">
            🎯
            <div class="kpi-number">{round(target)}</div>
            <div class="kpi-label">добова норма</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# КАЛОРІЇ З ГОДИННИКА
# =========================================================

st.subheader("⌚ Калорії з годинника")

with st.form("clock_form", clear_on_submit=False):

    clock_value = st.number_input(
        "Спалено сьогодні, ккал",
        min_value=0.0,
        value=float(st.session_state.clock_calories),
        step=10.0,
        format="%.2f"
    )

    update_clock = st.form_submit_button(
        "⌚ Оновити",
        use_container_width=True
    )

    if update_clock:
        save_undo()

        # ВАЖЛИВО:
        # НЕ додаємо нове значення.
        # Повністю ЗАМІНЮЄМО старе.
        st.session_state.clock_calories = float(clock_value)

        st.rerun()


# =========================================================
# ДОДАТИ ЇЖУ
# =========================================================

st.subheader("🍽️ Додати їжу")

with st.form("food_form", clear_on_submit=True):

    food_name = st.text_input(
        "Продукт / страва",
        placeholder="Наприклад: Плов з куркою, хліб..."
    )

    food_calories = st.number_input(
        "Калорії, ккал",
        min_value=0.0,
        value=0.0,
        step=10.0,
        format="%.0f"
    )

    food_ok = st.form_submit_button(
        "✅ ОК",
        use_container_width=True
    )

    if food_ok:

        if not food_name.strip():
            st.warning("Введи назву продукту.")
        else:
            add_food(
                food_name,
                food_calories
            )

            # clear_on_submit=True очищає поле
            st.rerun()


# =========================================================
# ДОДАТИ ТРЕНУВАННЯ
# =========================================================

with st.expander("💪 Додати тренування"):

    with st.form(
        "activity_form",
        clear_on_submit=True
    ):

        activity_name = st.text_input(
            "Опис",
            placeholder="Тренування"
        )

        activity_calories = st.number_input(
            "Спалено, ккал",
            min_value=0.0,
            value=0.0,
            step=10.0,
            format="%.0f"
        )

        activity_ok = st.form_submit_button(
            "➕ Додати",
            use_container_width=True
        )

        if activity_ok:

            add_activity(
                activity_name,
                activity_calories
            )

            st.rerun()


# =========================================================
# РЕДАКТОР
# =========================================================

with st.expander("✏️ Редактор"):

    with st.form("settings_form"):

        new_target = st.number_input(
            "Добова норма, ккал",
            min_value=500.0,
            value=float(st.session_state.target),
            step=50.0
        )

        new_bmr = st.number_input(
            "Базова витрата, ккал",
            min_value=500.0,
            value=float(st.session_state.bmr),
            step=50.0
        )

        new_weight = st.number_input(
            "Початкова вага, кг",
            min_value=20.0,
            value=float(st.session_state.weight),
            step=0.1
        )

        save_settings = st.form_submit_button(
            "💾 Зберегти",
            use_container_width=True
        )

        if save_settings:

            save_undo()

            st.session_state.target = float(new_target)
            st.session_state.bmr = float(new_bmr)
            st.session_state.weight = float(new_weight)

            st.rerun()


# =========================================================
# ВЛОГ
# =========================================================

st.subheader(
    f"📋 Влог за {current_date()}"
)

if not st.session_state.entries:

    st.info(
        "Записів ще немає. "
        "Додай їжу або тренування вище."
    )

else:

    for item in reversed(
        st.session_state.entries
    ):

        is_food = item["kind"] == "food"

        if is_food:
            icon = "🍽️"
            kcal_text = f"+{round(item['kcal'])} ккал"
            kcal_class = "food-kcal"
        else:
            icon = "💪"
            kcal_text = f"-{round(abs(item['kcal']))} ккал"
            kcal_class = "burn-kcal"

        st.markdown(
            f"""
            <div class="log">

                <div class="log-row">

                    <div class="log-left">

                        <div class="log-time">
                            {item["time"]}
                        </div>

                        <div class="log-title">
                            {icon} {item["title"]}
                        </div>

                    </div>

                    <div class="log-kcal {kcal_class}">
                        {kcal_text}
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        # ---------------------------------------------
        # РЕДАГУВАННЯ КОНКРЕТНОГО ЗАПИСУ
        # ---------------------------------------------

        with st.expander(
            "✏️ Редагувати",
            expanded=False
        ):

            with st.form(
                f"edit_form_{item['id']}"
            ):

                edited_title = st.text_input(
                    "Назва",
                    value=item["title"]
                )

                edited_kcal = st.number_input(
                    "Калорії, ккал",
                    min_value=0.0,
                    value=abs(float(item["kcal"])),
                    step=10.0,
                    format="%.0f"
                )

                save_item = st.form_submit_button(
                    "💾 Зберегти",
                    use_container_width=True
                )

                if save_item:

                    save_undo()

                    item["title"] = (
                        edited_title.strip()
                        or item["title"]
                    )

                    if is_food:
                        item["kcal"] = float(
                            edited_kcal
                        )
                    else:
                        item["kcal"] = -abs(
                            float(edited_kcal)
                        )

                    st.rerun()

        # ---------------------------------------------
        # ВИДАЛЕННЯ
        # ---------------------------------------------

        if st.button(
            "🗑️ Видалити",
            key=f"delete_{item['id']}",
            use_container_width=True
        ):

            save_undo()

            st.session_state.entries = [
                x
                for x in st.session_state.entries
                if x["id"] != item["id"]
            ]

            st.rerun()


# =========================================================
# ПІДСУМОК
# =========================================================

st.subheader("📊 Підсумок")


final_balance = current_balance()


if final_balance > 0.5:

    final_text = (
        f"📉 Дефіцит: "
        f"{round(final_balance)} ккал"
    )

    final_class = "deficit"

elif final_balance < -0.5:

    final_text = (
        f"📈 Профіцит: "
        f"{round(abs(final_balance))} ккал"
    )

    final_class = "surplus"

else:

    final_text = "⚖️ Баланс: 0 ккал"
    final_class = "neutral"


st.markdown(
    f"""
    <div class="balance {final_class}">
        {final_text}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ДЕТАЛІ
# =========================================================

st.markdown(
    f"""
    <div class="card">

        <b>🍽️ З'їдено:</b>
        {round(eaten)} ккал
        <br><br>

        <b>⌚ З годинника:</b>
        {round(clock)} ккал
        <br><br>

        <b>💪 Інші тренування:</b>
        {round(manual_burned)} ккал
        <br><br>

        <b>🔥 Всього спалено:</b>
        {round(burned)} ккал
        <br><br>

        <b>🎯 Добова норма:</b>
        {round(target)} ккал
        <br><br>

        <b>⚖️ Розрахункова вага:</b>
        {estimated_weight():.1f} кг

    </div>
    """,
    unsafe_allow_html=True
)


st.caption(
    "⚖️ Орієнтир: приблизно 7700 ккал накопиченого "
    "дефіциту ≈ 1 кг. Зміна ваги є розрахунковою."
)
