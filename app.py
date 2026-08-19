import json
import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# --- НАЛАШТУВАННЯ СТИЛЮ (ЧІТКИЙ ФОН) ---
st.set_page_config(page_title='Мій Фітнес', layout='centered')

st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(10, 10, 10, 0.8), rgba(10, 10, 10, 0.8)), url("https://i.ibb.co/jXZnnG5/IMG-20260819-144933.jpg");
        background-repeat: no-repeat;
        background-position: center center;
        background-attachment: fixed;
        background-size: cover;
        background-color: #000000;
    }
    /* Компактні блоки з читабельним текстом */
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(20, 20, 20, 0.92);
        border-radius: 12px;
        padding: 8px 12px;
        color: white;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

EXCEL_FILE = 'fitness_tracker.xlsx'
BASE_CALORIE_TARGET = 2050
DAYS_UA = {'Monday': 'Понеділок', 'Tuesday': 'Вівторок', 'Wednesday': 'Середа', 'Thursday': 'Четвер', 'Friday': 'П’ятниця', 'Saturday': 'Субота', 'Sunday': 'Неділя'}

api_key = st.secrets.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
if not api_key:
    st.error('⚠️ Не знайдено API ключ!')
    st.stop()

client = genai.Client(api_key=api_key)

# Красивий заголовок з емодзі пончика замість зламаної картинки
st.title("🍩 Фітнес-трекер")

with st.container(border=True):
    user_input = st.text_input('📥 Введіть дані:', placeholder="Наприклад: з'їв 30г хліба, спалено 300 ккал")
    submit_btn = st.button('Записати', type='primary', use_container_width=True)

if submit_btn and user_input:
    prompt = f"""Аналізуй: "{user_input}". Поверни JSON: food_description, steps, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs."""
    try:
        response = client.models.generate_content(model='gemini-3.6-flash', contents=prompt, config=types.GenerateContentConfig(response_mime_type='application/json'))
        data = json.loads(response.text)
        
        if os.path.exists(EXCEL_FILE): df = pd.read_excel(EXCEL_FILE)
        else: df = pd.DataFrame(columns=['Дата', 'День тижня', 'Раціон', 'Кроки', 'Спалено (ккал)', 'Спожито (ккал)', 'Білки (г)', 'Жири (г)', 'Вуглеводи (г)', 'Баланс (ккал)'])

        now = pd.Timestamp.today()
        date_str = now.strftime('%Y-%m-%d')
        
        if date_str in df['Дата'].astype(str).values:
            idx = df[df['Дата'].astype(str) == date_str].index[0]
            df.loc[idx, 'Спожито (ккал)'] += float(data.get('total_consumed_kcal', 0))
            df.loc[idx, 'Спалено (ккал)'] += float(data.get('kcal_burned', 0))
            df.loc[idx, 'Баланс (ккал)'] = df.loc[idx, 'Спожито (ккал)'] - df.loc[idx, 'Спалено (ккал)']
        else:
            new_row = pd.DataFrame({'Дата': [date_str], 'День тижня': [DAYS_UA.get(now.strftime('%A'))], 'Раціон': [data.get('food_description')], 'Кроки': [data.get('steps')], 'Спалено (ккал)': [data.get('kcal_burned')], 'Спожито (ккал)': [data.get('total_consumed_kcal')], 'Білки (г)': [data.get('total_protein')], 'Жири (г)': [data.get('total_fat')], 'Вуглеводи (г)': [data.get('total_carbs')], 'Баланс (ккал)': [data.get('total_consumed_kcal', 0) - data.get('kcal_burned', 0)]})
            df = pd.concat([df, new_row], ignore_index=True)
            
        df.to_excel(EXCEL_FILE, index=False)
        st.success('✅ Записано!')
    except Exception as e:
        st.error(f'Помилка: {e}')

# --- КОМПАКТНЕ ВІДОБРАЖЕННЯ НА ОДИН ЕКРАН ---
if os.path.exists(EXCEL_FILE):
    df_current = pd.read_excel(EXCEL_FILE)
    if not df_current.empty:
        latest = df_current.sort_values(by='Дата', ascending=False).iloc[0]
        
        st.markdown(f"**📅 {latest['Дата']} ({latest['День тижня']})**")

        # Метрики поруч
        c1, c2 = st.columns(2)
        c1.metric("🥗 Їжа", f"{int(latest['Спожито (ккал)'])} ккал")
        c2.metric("🔥 Спорт", f"{int(latest['Спалено (ккал)'])} ккал")
        
        st.info(f"🍱 {latest['Раціон']}")
