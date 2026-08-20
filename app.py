st.title(f"🏋️ Фітнес: {user_profile}")

# --- БЛОК ВВОДУ ---
with st.container(border=True):
    user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")
    
    # Кнопки в ряд для камери та запису
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if not st.session_state["open_camera"]:
            if st.button("📸 Камера"):
                st.session_state["open_camera"] = True
                st.rerun()
        else:
            if st.button("❌ Вимкнути"):
                st.session_state["open_camera"] = False
                st.rerun()
    with col_b:
        submit_btn = st.button("✅ Записати", type="primary")

    if st.session_state["open_camera"]:
        captured_image = st.camera_input("Зробити фото")
    else:
        captured_image = None

# --- БЛОК УПРАВЛІННЯ ---
st.markdown("---")
# Використовуємо columns для компактності кнопок
c1, c2, c3 = st.columns(3)
with c1:
    btn_settings = st.button("⚙️ Налаштування")
with c2:
    btn_del = st.button("🗑️ Видалити")
with c3:
    btn_back = st.button("🔄 Повернути")

# Логіка кнопок
if submit_btn and (user_input or captured_image):
    # (Тут твоя логіка обробки запису залишається без змін)
    pass 

if btn_settings: st.session_state["edit_mode"] = not st.session_state["edit_mode"]
if btn_del:
    # Логіка видалення
    pass
if btn_back:
    # Логіка повернення
    pass

st.markdown("---")
# --- ВИБІР ДАТИ ---
selected_date = st.selectbox("📅 Вибрати день для перегляду:", available_dates)
