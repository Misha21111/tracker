import json
import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# --- НАЛАШТУВАННЯ СТИЛЮ ---
st.set_page_config(page_title='Мій Фітнес', layout='centered')

st.markdown("""
    <style>
    .stApp {
        background-image: url("https://i.ibb.co/jXZnnG5/IMG-20260819-144933.jpg");
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
    .donut-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 15px 0;
    }
    .donut-ring {
        width: 190px;
        height: 190px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow: 0 0 15px rgba(0,0,0,0.6);
    }
    .donut-hole {
        width: 125px;
        height: 125px;
        background-color: #141414;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: white;
    }
    .macros-row {
        display: flex;
        justify-content: space-around;
        width: 100%;
        margin-top: 12px;
        font-size: 14px;
        background-color: rgba(20, 20, 20, 0.92);
        padding: 10px;
        border-radius: 10px;
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
    user_input = st.text_input('📥 Введи, що зїв / тренування:', placeholder="Наприклад: з'їв 30г хліба, спалено 300 ккал")
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
            df.loc[idx, 'Білки (г)'] += float(data.get('total_protein', 0))
            df.loc[idx, 'Жири (г)'] += float(data.get('total_fat', 0))
            df.loc[idx, 'Вуглеводи (г)'] += float(data.get('total_carbs', 0))
            df.loc[idx, 'Баланс (ккал)'] = df.loc[idx, 'Спожито (ккал)'] - df.loc[idx, 'Спалено (ккал)']
        else:
            new_row = pd.DataFrame({'Дата': [date_str], 'День тижня': [DAYS_UA.get(now.strftime('%A'))], 'Раціон': [data.get('food_description')], 'Кроки': [data.get('steps')], 'Спалено (ккал)': [data.get('kcal_burned')], 'Спожито (ккал)': [data.get('total_consumed_kcal')], 'Білки (г)': [data.get('total_protein')], 'Жири (г)': [data.get('total_fat')], 'Вуглеводи (г)': [data.get('total_carbs')], 'Баланс (ккал)': [data.get('total_consumed_kcal', 0) - data.get('kcal_burned', 0)]})
            df = pd.concat([df, new_row], ignore_index=True)
            
        df.to_excel(EXCEL_FILE, index=False)
        st.success('✅ Записано!')
    except Exception as e:
        st.error(f'Помилка: {e}')

# --- ВИВЕДЕННЯ ІНФОРМАЦІЇ ---
if os.path.exists(EXCEL_FILE):
    df_current = pd.read_excel(EXCEL_FILE)
    if not df_current.empty:
        latest = df_current.sort_values(by='Дата', ascending=False).iloc[0]
        
        st.markdown(f"**📅 {latest['Дата']} ({latest['День тижня']})**")

        consumed = float(latest.get('Спожито (ккал)', 0))
        burned = float(latest.get('Спалено (ккал)', 0))
        protein = float(latest.get('Білки (г)', 0))
        fat = float(latest.get('Жири (г)', 0))
        carbs = float(latest.get('Вуглеводи (г)', 0))

        p_kcal = protein * 4
        f_kcal = fat * 9
        c_kcal = carbs * 4
        total_macro_kcal = p_kcal + f_kcal + c_kcal

        if total_macro_kcal > 0:
            p_pct = round((p_kcal / total_macro_kcal) * 100)
            f_pct = round((f_kcal / total_macro_kcal) * 100)
            c_pct = 100 - p_pct - f_pct
            
            p_deg = int((p_pct / 100) * 360)
            f_deg = p_deg + int((f_pct / 100) * 360)
            
            gradient_style = f"background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg 360deg);"
        else:
            p_pct, f_pct, c_pct = 0, 0, 0
            gradient_style = "background: #333;"

        percent_target = min(100, int((consumed / BASE_CALORIE_TARGET) * 100))

        # Пончик без плутаних відсотків БЖУ, тільки грами
        st.markdown(f"""
            <div class="donut-container">
                <div class="donut-ring" style="{gradient_style}">
                    <div class="donut-hole">
                        <span style="font-size: 20px; font-weight: bold;">{int(consumed)}</span>
                        <span style="font-size: 11px; color: #aaa;">із {BASE_CALORIE_TARGET} ккал</span>
                        <span style="font-size: 12px; color: #4CAF50; margin-top: 2px;"><b>{percent_target}% від норми</b></span>
                    </div>
                </div>
                <div class="macros-row">
                    <span style="color:#36A2EB;">🥩 Білки: <b>{protein:.0f}г</b></span>
                    <span style="color:#FFCE56;">🥑 Жири: <b>{fat:.0f}г</b></span>
                    <span style="color:#FF6384;">🍞 Вугл: <b>{carbs:.0f}г</b></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        c1.metric("🍽️ З'їв за день", f"{int(consumed)} ккал")
        c2.metric("💪 Спалено на тренуванні", f"{int(burned)} ккал")
        
        st.markdown(f"""
            <div class="food-box">
                <b>📝 Що ти їв сьогодні:</b><br>{latest['Раціон']}
            </div>
        """, unsafe_allow_html=True)
