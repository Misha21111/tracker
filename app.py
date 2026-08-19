    # Розрахунок градусів для кожного сегмента
    total_macros = protein + fat + carbs
    if total_macros > 0:
        p_deg = (protein / total_macros) * 360
        f_deg = p_deg + (fat / total_macros) * 360
        c_deg = f_deg + (carbs / total_macros) * 360
    else:
        p_deg, f_deg, c_deg = 0, 0, 0

    st.markdown(f"""
        <div class="donut-container">
            <div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg);">
                <div class="donut-hole">
                    <b>{int(consumed)}</b><br>із {target_cal} ккал<br><b>{percent_target}%</b>
                </div>
            </div>
            <div class="macros-row">
                <span>🥩 {protein:.0f}/{user_settings['protein']}г</span>
                <span>🥑 {fat:.0f}/{user_settings['fat']}г</span>
                <span>🍞 {carbs:.0f}/{user_settings['carbs']}г</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
