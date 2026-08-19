  if not today_row.empty:
    r = today_row.iloc[0]
    consumed = float(r['Спожито (ккал)'])
    burned = float(r['Спалено (ккал)'])
    p_val = float(r['Білки (г)'])
    f_val = float(r['Жири (г)'])
    c_val = float(r['Вуглеводи (г)'])

    # ФОРМУЛА: Скільки ще можна з'їсти = (Ціль + Спалено) - Спожито
    # Якщо число додатне — це ваш "запас" на вечір.
    # Якщо від'ємне — ви вже перевищили норму.
    remaining_kcal = (TARGETS['kcal'] + burned) - consumed

    col1, col2, col3, col4 = st.columns(4)
    
    # Головний показник тепер — ЗАЛИШОК
    col1.metric(
        'Залишок (ккал)',
        f'{int(remaining_kcal)}',
        help="Ціль (2050) + Спалено - Спожито",
        delta=f'Спожито: {consumed} (Спалено: {burned})',
    )
    col2.metric(
        'Білки',
        f'{p_val} г',
        delta=f'{p_val - TARGETS["protein"]:.1f} г',
    )
    col3.metric(
        'Жири',
        f'{f_val} г',
        delta=f'{f_val - TARGETS["fat"]:.1f} г',
    )
    col4.metric(
        'Вуглеводи',
        f'{c_val} г',
        delta=f'{c_val - TARGETS["carbs"]:.1f} г',
    )

    if remaining_kcal >= 0:
      st.success(f'✅ Ви в дефіциті. Можете спожити ще {int(remaining_kcal)} ккал.')
    else:
      st.error(f'❌ Ви перевищили ліміт на {abs(int(remaining_kcal))} ккал!')
