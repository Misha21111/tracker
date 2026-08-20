# ============================================================
# DONUT + МАКРОСИ
# ============================================================

# Якщо ці значення у тебе вже рахуються вище в коді,
# просто залиш їхні назви такими самими.

# Калорії
target_cal = float(target_cal)
consumed = float(consumed)

# Макроси
protein = float(protein)
fat = float(fat)
carbs = float(carbs)

target_p = float(target_p)
target_f = float(target_f)
target_c = float(target_c)


# ------------------------------------------------------------
# РОЗРАХУНОК DONUT
# ------------------------------------------------------------

# Калорії з макросів
protein_cal = protein * 4
fat_cal = fat * 9
carbs_cal = carbs * 4

macro_total = protein_cal + fat_cal + carbs_cal


# Захист від ділення на нуль
if macro_total > 0:

    p_deg = (protein_cal / macro_total) * 360

    f_deg = p_deg + (fat_cal / macro_total) * 360

    c_deg = 360

else:

    p_deg = 0
    f_deg = 0
    c_deg = 360


# ------------------------------------------------------------
# БАЛАНС КАЛОРІЙ
# ------------------------------------------------------------

balance = target_cal - consumed


if balance > 0:

    balance_label = "Залишилось"
    balance_text = f"{int(balance)} ккал"
    balance_color = "#36A2EB"

elif balance == 0:

    balance_label = "Ціль досягнута"
    balance_text = "0 ккал"
    balance_color = "#4CAF50"

else:

    balance_label = "Перевищено"
    balance_text = f"{int(abs(balance))} ккал"
    balance_color = "#FF6384"


# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------

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
    margin-bottom: 20px;
}

.donut-ring {
    width: 180px;
    height: 180px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.donut-hole {
    width: 125px;
    height: 125px;
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
    align-items: center;
    justify-content: center;

    gap: 18px;
    flex-wrap: wrap;

    margin-top: 18px;

    font-size: 13px;
}

.macros-row span {
    white-space: nowrap;
}

</style>
""",
    unsafe_allow_html=True
)


# ------------------------------------------------------------
# DONUT HTML
# ------------------------------------------------------------

st.markdown(
    f"""<div class="donut-container">

<div
    class="donut-ring"
    style="background: conic-gradient(
        #36A2EB 0deg {p_deg}deg,
        #FFCE56 {p_deg}deg {f_deg}deg,
        #FF6384 {f_deg}deg {c_deg}deg
    );"
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
        font-size: 14px;
        line-height: 1.2;
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

</div>""",
    unsafe_allow_html=True
)
