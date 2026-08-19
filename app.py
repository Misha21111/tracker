with st.container(border=True):
    user_input = st.text_input("📥 Опис їжі (або назва):", placeholder="Наприклад: з'їв 30г хліба")
    uploaded_photo = st.file_uploader("Додати фото їжі", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    submit_btn = st.button("Записати в лог", type="primary", use_container_width=True)

# Логіка обробки (заміна попередньої автоматичної логіки)
if submit_btn:
    if not user_input and uploaded_photo is None:
        st.error("⚠️ Будь ласка, введіть опис або завантажте фото!")
    else:
        with st.spinner("🧠 Gemini аналізує ваше фото..."):
            current_time_str = datetime.now(LOCAL_TZ).strftime("%H:%M")
            current_date_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
            
            try:
                # Визначаємо, що саме аналізувати
                if uploaded_photo:
                    image_bytes = uploaded_photo.getvalue()
                    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                    prompt = "Проаналізуй цю страву на фото. Визнач назву, приблизну вагу, калорії та БЖВ. Поверни JSON з ключами: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs."
                    response = client.models.generate_content(
                        model="gemini-1.5-flash", 
                        contents=[image_part, prompt], 
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                else:
                    prompt = f'Аналізуй цей текст: "{user_input}". Поверни JSON з ключами: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs.'
                    response = client.models.generate_content(
                        model="gemini-1.5-flash", 
                        contents=prompt, 
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    
                data = json.loads(response.text)
                
                # Формуємо запис
                new_entry = pd.DataFrame([{
                    "Дата": current_date_str, 
                    "Час": current_time_str, 
                    "Опис": data.get("food_description", user_input if user_input else "Їжа з фото"), 
                    "Тип": "Тренування" if clean_float(data.get("kcal_burned")) > 0 else "Їжа", 
                    "Спожито": clean_float(data.get("total_consumed_kcal")), 
                    "Спалено": clean_float(data.get("kcal_burned")), 
                    "Білки": clean_float(data.get("total_protein")), 
                    "Жири": clean_float(data.get("total_fat")), 
                    "Вуглеводи": clean_float(data.get("total_carbs"))
                }])
                
                # Додаємо до файлу
                df_data = pd.concat([df_data, new_entry], ignore_index=True)
                df_data.to_excel(EXCEL_FILE, index=False)
                st.success("✅ Записано успішно!")
                st.rerun()
            except Exception as e: 
                st.error(f"Помилка аналізу (перевірте ключ API або фото): {e}")
