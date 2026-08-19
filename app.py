# ... (весь код до заголовка "🏋️ Мій фітнес" залишається без змін)

st.title("🏋️ Мій фітнес")

# 1. Поле введення їжі — ТЕПЕР ПЕРШЕ
now = datetime.now()
today_str = now.strftime("%Y-%m-%d")

with st.container(border=True):
    user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")
    submit_btn = st.button("Записати в лог", type="primary", use_container_width=True)

# 2. Логіка запису (теж вище)
if submit_btn and user_input:
    # ... (код обробки Gemini як був раніше)
    # Переконайтеся, що тут є df_data.to_excel(...) та st.rerun()

# 3. Решта елементів — НИЖЧЕ
selected_date = st.selectbox("📅 Вибрати день для перегляду:", available_dates)

# Кнопки: Налаштування окремо, Видалити + Повернути — в одному рядку
if st.button("⚙️ Налаштування", use_container_width=True): 
    st.session_state["edit_mode"] = not st.session_state["edit_mode"]

# Блок кнопок в одному рядку
col1, col2 = st.columns(2)
with col1:
    if st.button("🗑️ Видалити останнє", use_container_width=True):
        if not df_data.empty:
            last_row = df_data.iloc[-1:].to_dict(orient="records")
            with open(TRASH_FILE, "w") as f: json.dump(last_row, f)
            df_data = df_data.iloc[:-1]
            df_data.to_excel(EXCEL_FILE, index=False)
            st.rerun()
with col2:
    if os.path.exists(TRASH_FILE):
        if st.button("🔄 Повернути", use_container_width=True):
            with open(TRASH_FILE, "r") as f: restored = json.load(f)
            df_data = pd.concat([df_data, pd.DataFrame(restored)], ignore_index=True)
            df_data.to_excel(EXCEL_FILE, index=False)
            os.remove(TRASH_FILE)
            st.rerun()
    else:
        st.button("🔄 Повернути", disabled=True, use_container_width=True)

# ... (далі йде решта коду з відображенням графіків та логів)
