    st.markdown(
        f"""
        <div class="donut-container">
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
        </div>
        """,
        unsafe_allow_html=True
    )
