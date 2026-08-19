import json
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google import genai
from google.genai import types

# --- НАЛАШТУВАННЯ СТИЛЮ ---
st.set_page_config(page_title='Мій Фітнес', layout='centered')

st.markdown("""
    <style>
    .stApp {
        background-image: linear-gradient(rgba(10, 10, 10, 0.75), rgba(10, 10, 10, 0.75)), url("https://i.ibb.co/jXZnnG5/IMG-20260819-144933.jpg");
        background-repeat: no-repeat;
        background-position: center center;
        background-attachment: fixed;
        background-size: cover;
        background-color: #000000;
    }
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(20, 20, 20, 0.92);
        border-radius: 12px;
        padding: 10px 14px;
        color: white;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .food-box {
        background-color: rgba(20, 20, 20, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 12px 16px;
        color: #ffffff;
        font-size: 16px;
        line-height: 1.5;
        margin-top: 10px;
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

st.title("🏋️ Мій фітнес")

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

# --- ВЕЛИКИЙ ПОНЧИК-ДІАГРАМА ТА ВИПРАВЛЕНИЙ ТЕКСТ ЇДИ ---
if os.path.exists(EXCEL_FILE):
    df_current = pd.read_excel(EXCEL_FILE)
    if not df_current.empty:
        latest = df_current.sort_values(by='Дата', ascending=False).iloc[0]
        
        st.markdown(f"**📅 {latest['Дата']} ({latest['День тижня']})**")

        consumed = float(latest['Спожито (ккал)'])
        target = BASE_CALORIE_TARGET
        remaining = max(0, target - consumed)

        fig = go.Figure(data=[go.Pie(
            labels=['Спожито', 'Залишок'],
            values=[consumed, remaining],
            hole=0.7,
            marker=dict(colors=['#ff5252', '#4CAF50']),
            textinfo='label+percent',
            textfont=dict(size=14, color='white'),
            hoverinfo='label+value'
        )])

        fig.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=320,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0,0)',
            annotations=[dict(
                text=f"<b>{int(consumed)}</b><br><span style='font-size:12px; color:#aaa;'>з {target} ккал</span>",
                x=0.5, y=0.5,
                font=dict(size=20, color='white'),
                showarrow=False
            )]
        )

        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric("🥗 Їжа", f"{int(consumed)} ккал")
        c2.metric("🔥 Спорт", f"{int(latest['Спалено (ккал)'])} ккал")
        
        st.markdown(f"""
            <div class="food-box">
                <b>🍱 Раціон:</b><br>{latest['Раціон']}
            </div>
        """, unsafe_allow_html=True)
