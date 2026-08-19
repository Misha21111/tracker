  st.subheader('📅 Історія прогресу')
  
  if not df_current.empty:
    for index, row in df_current.iterrows():
      # Визначаємо колір картки залежно від балансу
      balance = float(row['Баланс (ккал)'])
      status_color = "border-color: #26C6DA;" if balance <= 2050 else "border-color: #EF5350;"
      
      with st.container(border=True):
        # Заголовок з датою
        st.markdown(f"**{row['Дата']}** • *{row['День тижня']}*")
        
        # Компактні показники з іконками
        cols = st.columns(3)
        cols[0].metric("🥗 Спожито", f"{int(row['Спожито (ккал)'])}")
        cols[1].metric("🔥 Спалено", f"{int(row['Спалено (ккал)'])}")
        cols[2].metric("📊 Баланс", f"{int(balance)}")
        
        # Красива стрічка з раціоном
        st.info(f"**Раціон:** {row['Раціон']}", icon="🍱")
        
        # Естетична візуалізація БЖВ
        col_p, col_f, col_c = st.columns(3)
        col_p.caption(f"🥩 Білки: {row['Білки (г)']}г")
        col_f.caption(f"🥑 Жири: {row['Жири (г)']}г")
        col_c.caption(f"🍞 Вуглі: {row['Вуглеводи (г)']}г")
    
    # Меню видалення внизу
    with st.expander('⚙️ Налаштування історії'):
      dates = df_current['Дата'].astype(str).tolist()
      target_date = st.selectbox('Вибрати дату:', dates)
      if st.button('Видалити запис', type='primary'):
        df_updated = df_current[df_current['Дата'].astype(str) != target_date]
        df_updated.to_excel(EXCEL_FILE, index=False)
        st.rerun()
