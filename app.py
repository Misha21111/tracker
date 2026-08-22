import streamlit as st
import json
from datetime import datetime
from google import genai
from google.genai import types

# Налаштування сторінки
st.set_page_config(page_title="Калорійний трекер", layout="centered")

# Ініціалізація Gemini API
api_key = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key)

st.title("⚖️ Калорійний трекер — Я")

# Поля введення
selected_date = st.date_input("📅 Оберіть день", datetime.now()).strftime("%Y-%m-%d")
user_input = st.text_input("🍽️ Що з'їв / тренування", placeholder="Наприклад: Плов з куркою 450 грамм")

if st.button("✅ ОК — додати"):
    if not user_input.strip():
        st.warning("⚠️ Введіть опис їжі або тренування!")
    else:
        try:
            prompt = """
            Ти — розумний асистент для трекера калорій та здоров'я. 
            Проаналізуй введений користувачем текст і поверни СУВОРО валідний JSON-об'єкт (без жодних форматувань markdown типу ```json чи додаткового тексту) з такими ключами:
            - "entry_type": "їжа" або "тренування"
            - "description": назва продукту чи тренування (стрічка)
            - "consumed_kcal": кількість спожитих калорій (число, якщо це їжа, інакше 0)
            - "burned_kcal": кількість спалених калорій (число, якщо це тренування, інакше 0)
            - "protein": білки в грамах (число)
            - "fat": жири в грамах (число)
            - "carbs": вуглеводи в грамах (число)
            """

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt + "\n\nЗапис користувача:\n" + user_input.strip()
            )

            raw = (response.text or "").strip()
            
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            result = json.loads(raw)

            now = datetime.now()
            new_row = [
                selected_date,
                now.strftime("%H:%M"),
                result.get("description", user_input),
                result.get("entry_type", "їжа"),
                result.get("consumed_kcal", 0),
                result.get("burned_kcal", 0),
                result.get("protein", 0),
                result.get("fat", 0),
                result.get("carbs", 0)
            ]

            # Додавання в Google Таблицю
            sheet.append_row(new_row)
            
            st.success("✅ Запис успішно додано в Google Таблицю!")
            st.rerun()

        except Exception as error:
            st.error(f"❌ Помилка: {error}")

# ==========================================
# КНОПКИ КЕРУВАННЯ ТА ВИВЕДЕННЯ ДАНИХ
# ==========================================
col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("⚙️ Налаштування"):
        pass

st.markdown(f"### 📋 Лог за {selected_date}")
