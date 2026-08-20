import streamlit as st

# =========================================================
# НАЛАШТУВАННЯ СТОРІНКИ
# =========================================================

st.set_page_config(
    page_title="Трекер харчування",
    page_icon="🥗",
    layout="centered"
)

# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>
        .donut-container {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-top: 20px;
        }

        .donut-ring {
            width: 190px;
            height: 190px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .donut-hole {
            width: 130px;
            height: 130px;
            border-radius: 50%;
            background: #0e1117;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 4px;
        }

        .macros-row {
            width: 100%;
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 20px;
            font-size: 14px;
        }

        .macro-item {
            white-space: nowrap;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# ДАНІ
# =========================================================
# Тут можеш замінити числа на свої значення
# або підставити свої змінні з програми.

target_cal = 2000       # денна ціль калорій
consumed = 1450         # спожито калорій

target_p = 120          # ціль білків, г
target_f = 65           # ціль жирів, г
target_c = 220          # ціль вуглеводів, г

protein = 85            # фактично білків, г
fat = 48                # фактично жирів, г
carbs = 165              # фактично вуглеводів, г


# =========================================================
# ПЕРЕВІРКА ДАНИХ
# =========================================================

target_cal = max(float(target_cal), 1)
consumed = max(float(consumed), 0)

target_p = max(float(target_p), 0)
target_f = max(float(target_f), 0)
target_c = max(float(target_c), 0)

protein = max(float(protein), 0)
fat = max(float(fat), 0)
carbs = max(float(carbs), 0)


# =========================================================
# РОЗРАХУНОК КАЛОРІЙ З МАКРОНУТРІЄНТІВ
# =========================================================

protein_cal = protein * 4
fat_cal = fat * 9
carbs_cal = carbs * 4

macro_total_cal = protein_cal + fat_cal + carbs_cal


# =========================================================
# РОЗРАХУНОК КУТІВ DONUT
# =========================================================

if macro_total_cal > 0:

    p_deg = (protein_cal / macro_total_cal) * 360
    f_deg = p_deg + (fat_cal / macro_total_cal) * 360
    c_deg = 360

else:

    p_deg = 0
    f_deg = 0
    c_deg = 360


# =========================================================
# БАЛАНС КАЛОРІЙ
# =========================================================

remaining = target_cal - consumed


if remaining > 0:

    balance_label = "Залишилось"
    balance_text = f"{int(remaining)} ккал"
    balance_color = "#36A2EB"

elif remaining == 0:

    balance_label = "Ціль"
    balance_text = "Досягнуто"
    balance_color = "#4CAF50"

else:

    balance_label = "Перевищено"
    balance_text = f"{int(abs(remaining))} ккал"
    balance_color = "#FF6384"


# =========================================================
# ВІДСОТОК КАЛОРІЙ
# =========================================================

calorie_percent = min(
    max(consumed / target_cal, 0),
    1
)

calorie_percent_text = f"{calorie_percent * 100:.0f}%"


# =========================================================
# ЗАГОЛОВОК
# =========================================================

st.title("🥗 Трекер харчування")

st.subheader("Сьогодні")


# =========================================================
# DONUT
# =========================================================

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
                    {balance_label}
                </span>

                <b
                    style="
                        font-size: 20px;
                    "
                >
                    {int(consumed)} / {int(target_cal)}
                </b>

                <span
                    style="
                        font-size: 9px;
                        color: #888;
                    "
                >
                    ккал
                </span>

                <span
                    style="
                        font-size: 9px;
                        color: #aaa;
                    "
                >
                    {calorie_percent_text}
                </span>

            </div>

        </div>


        <div class="macros-row">

            <span
                class="macro-item"
                style="color: #36A2EB;"
            >
                🥩 Білки:
                {protein:.0f} / {target_p:.0f} г
            </span>


            <span
                class="macro-item"
                style="color: #FFCE56;"
            >
                🥑 Жири:
                {fat:.0f} / {target_f:.0f} г
            </span>


            <span
                class="macro-item"
                style="color: #FF6384;"
            >
                🍞 Вуглеводи:
                {carbs:.0f} / {target_c:.0f} г
            </span>

        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ДОДАТКОВА ІНФОРМАЦІЯ
# =========================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "🥩 Білки",
        f"{protein:.0f} г",
        f"{protein - target_p:.0f} г"
    )

with col2:
    st.metric(
        "🥑 Жири",
        f"{fat:.0f} г",
        f"{fat - target_f:.0f} г"
    )

with col3:
    st.metric(
        "🍞 Вуглеводи",
        f"{carbs:.0f} г",
        f"{carbs - target_c:.0f} г"
    )


# =========================================================
# КАЛОРІЇ
# =========================================================

st.divider()

st.write(
    f"🔥 **Калорії:** {int(consumed)} / {int(target_cal)} ккал"
)

st.progress(calorie_percent)
