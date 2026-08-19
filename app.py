# ... (код завантаження даних)

# Логіка оновлення ваги (заміни цей блок у себе):
today_df = df_data[df_data["Дата"].astype(str) == date_str] if not df_data.empty else pd.DataFrame()
if not today_df.empty:
    consumed = today_df["Спожито"].sum()
    explicit_burned = today_df["Спалено"].sum()
    
    # Розрахунок дефіциту: ціль - спожито + спалене (з годинника)
    # BMR за день - це константа, не додаємо її кожну хвилину, щоб не псувати вагу
    daily_deficit = user_settings["calories"] - consumed + explicit_burned
    
    # Оновлюємо "банк" дефіциту в файлі лише один раз на день або при записі
    # Використовуємо 7700 як коефіцієнт
    current_weight = w_data["start_weight"] - (w_data.get("total_deficit", 0) / 7700)
    
    st.markdown(f"**📅 {date_str} | Вага: ~{current_weight:.2f} кг**")
