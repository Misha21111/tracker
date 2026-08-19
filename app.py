# У функції load_settings додав bmr_daily
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"calories": 1990, "protein": 160, "fat": 70, "carbs": 180, "height": 178, "age": 35, "bmr_daily": 1850}

# У блоці редагування налаштувань (всередині st.session_state["edit_mode"])
        e_bmr = st.number_input("Базовий метаболізм (ккал/добу)", value=int(user_settings.get("bmr_daily", 1850)), step=10)
        
        if st.button("💾 Зберегти зміни", type="primary", use_container_width=True):
            user_settings = {
                "calories": e_cal, "protein": e_prot, "fat": e_fat, 
                "carbs": e_carb, "height": e_height, "age": e_age, 
                "bmr_daily": e_bmr
            }
            save_settings(user_settings)
            # ... далі як було ...

# У блоці розрахунку (замість формули використовуємо налаштування)
    bmr_daily = user_settings.get("bmr_daily", 1850)
    hours_passed = now.hour + (now.minute / 60)
    bmr_so_far = (bmr_daily / 24) * hours_passed
