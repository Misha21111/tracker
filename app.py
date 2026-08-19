import json
import os
import pandas as pd
import streamlit as st
import plotly.express as px
from google import genai
from google.genai import types

# --- НАЛАШТУВАННЯ СТИЛЮ ТА ТВОГО ФОНУ ---
st.set_page_config(page_title='Мій Фітнес', layout='centered')

st.markdown("""
    <style>
    .stApp {
        background: url("https://i.ibb.co/jXZnnG5/IMG-20260819-144933.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    /* Напівпрозорий темний шар для блоків, щоб текст було ідеально видно на фоні */
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(15, 15, 15, 0.82);
        border-radius: 12px;
        padding: 10px;
        color: white;
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

st.title("🏋️ Мій фітнес-прогрес")

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

# --- ВІДОБРАЖЕННЯ ДАНИХ ТА КРУГОВОЇ ДІАГРАМИ ---
if os.path.exists(EXCEL_FILE):
    df_current = pd.read_excel(EXCEL_FILE)
    if not df_current.empty:
        latest = df_current.sort_values(by='Дата', ascending=False).iloc[0]
        
        st.divider()
        st.subheader(f"📅 Останній запис: {latest['Дата']} ({latest['День тижня']})")

        # Кругова діаграма (пончик) із твоїм фоном
        chart_data = pd.DataFrame({
            'Показник': ['Спожито', 'Спалено'],
            'Ккал': [float(latest['Спожито (ккал)']), float(latest['Спалено (ккал)'])]
        })
        
        fig = px.pie(
            chart_data, 
            values='Ккал', 
            names='Показник', 
            hole=0.6,
            color='Показник',
            color_discrete_map={'Спожито': '#FF5252', 'Спалено': '#4CAF50'}
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            margin=dict(t=10, b=10, l=10, r=10),
            height=250
        )
        st.plotly_chart(fig, use_container_width=True)

        # Метрики та раціон
        c1, c2 = st.columns(2)
        c1.metric("🥗 Їжа", f"{int(latest['Спожито (ккал)'])} ккал")
        c2.metric("🔥 Спорт", f"{int(latest['Спалено (ккал)'])} ккал")
        
        st.info(f"🍱 **Що їв:** {latest['Раціон']}")
