import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
from google import genai
from google.genai import types

# Налаштування часу
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except ImportError:
    LOCAL_TZ = timezone(timedelta(hours=2))

st.set_page_config(page_title="Мій Фітнес", layout="centered")

# Основні шляхи
EXCEL_FILE = "fitness_entries.xlsx"
SETTINGS_FILE = "user_settings.json"

# API ключ
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("API ключ не знайдено!")
    st.stop()
client = genai.Client(api_key=api_key)

# Допоміжні функції
def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    return pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

def clean_float(val):
    try: return float(val)
    except: return 0.0

# Інтерфейс
st.title("🏋️ Мій Фітнес")

user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")
uploaded_photo = st.file_uploader("📸 Додати фото їжі", type=["jpg", "jpeg", "png"])
submit_btn = st.button("Записати в лог", type="primary")

if submit_btn:
    if not user_input and uploaded_photo is None:
        st.error("⚠️ Введіть опис або завантажте фото!")
    else:
        with st.spinner("🧠 Gemini аналізує..."):
            try:
                if uploaded_photo:
                    image_bytes = uploaded_photo.getvalue()
                    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                    prompt = "Проаналізуй страву на фото. Поверни JSON: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs."
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=[image_part, prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
                else:
                    prompt = f'Аналізуй: "{user_input}". Поверни JSON: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs.'
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
                
                data = json.loads(response.text)
                new_entry = pd.DataFrame([{
                    "Дата": datetime.now(LOCAL_TZ).strftime("%Y-%m-%d"),
                    "Час": datetime.now(LOCAL_TZ).strftime("%H:%M"),
                    "Опис": data.get("food_description", "Їжа"),
                    "Тип": "Тренування" if clean_float(data.get("kcal_burned")) > 0 else "Їжа",
                    "Спожито": clean_float(data.get("total_consumed_kcal")),
                    "Спалено": clean_float(data.get("kcal_burned")),
                    "Білки": clean_float(data.get("total_protein")),
                    "Жири": clean_float(data.get("total_fat")),
                    "Вуглеводи": clean_float(data.get("total_carbs"))
                }])
                
                df = load_data()
                df = pd.concat([df, new_entry], ignore_index=True)
                df.to_excel(EXCEL_FILE, index=False)
                st.success("✅ Записано!")
            except Exception as e:
                st.error(f"Помилка: {e}")

# Вивід логу
st.subheader("📋 Останні записи")
df = load_data()
if not df.empty:
    st.dataframe(df.tail(10))
