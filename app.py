    # Розрахунок реальних пропорцій для секторів кола на основі з'їдених грамів
    total_macros = protein + fat + carbs
    if total_macros > 0:
        p_deg = (protein / total_macros) * 360
        f_deg = p_deg + (fat / total_macros) * 360
        c_deg = 360
    else:
        p_deg, f_deg, c_deg = 120, 240, 360

    percent_target = min(100, int((consumed / target_cal) * 100)) if target_cal > 0 else 0
    st.markdown(f"""
        <div class="donut-container">
            <div class="donut-ring" style="background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg);">
                <div class="donut-hole">
                    <span style="font-size: 20px; font-weight: bold;">{int(consumed)}</span>
                    <span style="font-size: 11px; color: #aaa;">із {target_cal} ккал</span>
                    <span style="font-size: 12px; color: #4CAF50;"><b>{percent_target}%</b></span>
                </div>
            </div>
            <div class="macros-row">
                <span>🥩 {protein:.0f}/{target_prot}г</span><span>🥑 {fat:.0f}/{target_fat}г</span><span>🍞 {carbs:.0f}/{target_carb}г</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
