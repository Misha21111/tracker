# =========================================================
# DONUT
# =========================================================

# Безпечне отримання значень, щоб не було NameError
p_deg = globals().get("p_deg", 0)
f_deg = globals().get("f_deg", 0)
c_deg = globals().get("c_deg", 360)

balance_color = globals().get("balance_color", "#36A2EB")
balance_label = globals().get("balance_label", "Залишилось")

consumed = globals().get("consumed", 0)
target_cal = globals().get("target_cal", 0)

protein = globals().get("protein", 0)
target_p = globals().get("target_p", 0)

fat = globals().get("fat", 0)
target_f = globals().get("target_f", 0)

carbs = globals().get("carbs", 0)
target_c = globals().get("target_c", 0)


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
    gap: 3px;
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


# =========================================================
# HTML DONUT
# =========================================================

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
            {float(protein):.0f} / {float(target_p):.0f}г
        </span>

        <span style="color: #FFCE56;">
            🥑 Жири:
            {float(fat):.0f} / {float(target_f):.0f}г
        </span>

        <span style="color: #FF6384;">
            🍞 Вугл:
            {float(carbs):.0f} / {float(target_c):.0f}г
        </span>

    </div>

</div>
""",
    unsafe_allow_html=True
)
