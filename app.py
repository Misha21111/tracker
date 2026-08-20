# -----------------------------
# DONUT CHART DATA
# -----------------------------

# Захист від ділення на 0
target_cal = float(target_cal) if target_cal else 1.0

# Відсоток спожитих калорій
cal_percent = min(max(consumed / target_cal, 0), 1)

# Кути для donut
p_deg = cal_percent * 360
f_deg = p_deg + ((fat * 9) / target_cal) * 360
c_deg = f_deg + ((carbs * 4) / target_cal) * 360

# Не дозволяємо перевищити 360°
f_deg = min(f_deg, 360)
c_deg = min(c_deg, 360)

# Баланс
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


# -----------------------------
# DONUT
# -----------------------------

st.markdown(
    f"""
    <div class="donut-container">

        <div
            class="donut-ring"
            style="
                background: conic-gradient(
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
                    {balance_label}: {balance_text}
                </span>

                <b style="font-size: 14px;">
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

            </div>

        </div>

        <div class="macros-row">

            <span style="color: #36A2EB;">
                🥩 Білки:
                {protein:.0f} / {target_p:.0f}г
            </span>

            <span style="color: #FFCE56;">
                🥑 Жири:
                {fat:.0f} / {target_f:.0f}г
            </span>

            <span style="color: #FF6384;">
                🍞 Вугл:
                {carbs:.0f} / {target_c:.0f}г
            </span>

        </div>

    </div>
    """,
    unsafe_allow_html=True
)
st.markdown(
    f"""
    <div class="donut-container">
        <div
            class="donut-ring"
            style="
                background: conic-gradient(
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
                    {balance_label}: {balance_text}
                </span>

                <b style="font-size: 14px;">
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
            </div>
        </div>

        <div class="macros-row">
            <span style="color: #36A2EB;">
                🥩 Білки:
                {protein:.0f} / {target_p:.0f}г
            </span>

            <span style="color: #FFCE56;">
                🥑 Жири:
                {fat:.0f} / {target_f:.0f}г
            </span>

            <span style="color: #FF6384;">
                🍞 Вугл:
                {carbs:.0f} / {target_c:.0f}г
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
