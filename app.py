# Назва поля годинника
st.number_input(
    "⌚ Спалені калорії з годинника (ккал)",
    min_value=0.0,
    step=10.0,
    key=watch_key,
    on_change=on_watch_change,
)

# HTML кружка (без відображення ваги всередині)
donut_html = f'''
<div class="section">
    <div class="donut-wrap">
        <div class="donut" style="background:{gradient};">
            <div class="donut-hole">
                <div class="balance">{balance_label}</div>
                <div class="kcal-main">{consumed:.0f}</div>
                <div class="kcal-sub">з {target:.0f} ккал</div>
            </div>
        </div>
        <div class="macros">
            <div class="macro p">🥩 Білки {protein:.0f}/{settings["protein"]} г</div>
            <div class="macro f">🥑 Жири {fat:.0f}/{settings["fat"]} г</div>
            <div class="macro c">🍞 Вуглеводи {carbs:.0f}/{settings["carbs"]} г</div>
        </div>
    </div>
</div>
'''
st.markdown(donut_html, unsafe_allow_html=True)

# Заголовок логу та повідомлення
st.markdown(f"### 📝 Лог за {selected_date}")

if day_df.empty and watch_now <= 0:
    st.info("За цей день немає записів.")
