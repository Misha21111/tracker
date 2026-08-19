import json
import os
import pandas as pd
import streamlit as st
from datetime import datetime
from google import genai
from google.genai import types

# --- НАЛАШТУВАННЯ СТИЛЮ ---
st.set_page_config(page_title='Мій Фітнес', layout='centered')

st.markdown("""
    <style>
    .stApp {
        background-color: #0b0b0b;
    }
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(20, 20, 20, 0.95);
        border-radius: 12px;
        padding: 10px 14px;
        color: white;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .food-box {
        background-color: rgba(20, 20, 20, 0.95);
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
        box-shadow: 0 0 15px rgba(0,0,0,0.8);
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
        background-color: rgba(20, 20, 20, 0.95);
        padding: 10px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

EXCEL_FILE = 'fitness_entries.xlsx'
BASE_CALORIE_TARGET = 2050
DAYS_UA = {'Monday': 'Понеділок', 'Tuesday': 'Вівторок', 'Wednesday': 'Середа', 'Thursday': 'Четвер', 'Friday': 'П’ятниця', 'Saturday': 'Субота', 'Sunday': 'Неділя'}

api_key = st.secrets.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
if not api_key:
    st.error('⚠️ Не знайдено API ключ!')
    st.stop()

client = genai.Client(api_key=api_key)

st.title("🏋️ Мій фітнес")

with st.container(border=True):
    user_input = st.text_input('📥 Введи, що зїв / тренування:', placeholder="Наприклад: з'їв 30г хліба, спалено 300 ккал або Калорії 161")
    submit_btn = st.button('Записати', type='primary', use_container_width=True)

now = datetime.now()
date_str = now.strftime('%Y-%m-%d')
time_str = now.strftime('%H:%M')

# Функція завантаження або створення датафрейму
def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    return pd.DataFrame(columns=['Дата', 'Час', 'Опис', 'Тип', 'Спожито', 'Спалено', 'Білки', 'Жири', 'Вуглеводи'])

df_data = load_data()

if submit_btn and user_input:
    prompt = f"""Аналізуй текст: "{user_input}". 
    Визнач, чи це їжа/калорії які людина спожила, чи це спалені калорії на тренуванні/активності.
    Якщо в тексті є слова "спалено", "тренування", "калорії" у контексті витрати чи просто цифра тренування — записуй їх у kcal_burned. Якщо це їжа — у total_consumed_kcal.
    Поверни JSON із полями: 
    food_description (опис), 
    kcal_burned (спалені калорії або 0), 
    total_consumed_kcal (спожиті калорії або 0), 
    total_protein (0), total_fat (0), total_carbs (0)."""
    
    try:
        response = client.models.generate_content(model='gemini-3.6-flash', contents=prompt, config=types.GenerateContentConfig(response_mime_type='application/json'))
        data = json.loads(response.text)
        
        c_consumed = float(data.get('total_consumed_kcal') or 0)
        c_burned = float(data.get('kcal_burned') or 0)
        c_protein = float(data.get('total_protein') or 0)
        c_fat = float(data.get('total_fat') or 0)
        c_carbs = float(data.get('total_carbs') or 0)
        c_desc = str(data.get('food_description') or user_input)

        entry_type = 'Тренування' if c_burned > 0 else 'Їжа'
        if c_burned > 0 and c_consumed == 0:
            c_desc = f"Тренування ({c_burned} ккал)"

        new_entry = pd.DataFrame([{
            'Дата': date_str,
            'Час': time_str,
            'Опис': c_desc,
            'Тип': entry_type,
            'Спожито': c_consumed,
            'Спалено': c_burned,
            'Білки': c_protein,
            'Жири': c_fat,
            'Вуглеводи': c_carbs
        }])

        df_data = pd.concat([df_data, new_entry], ignore_index=True)
        df_data.to_excel(EXCEL_FILE, index=False)
        st.success('✅ Записано!')
        st.rerun()
    except Exception as e:
        st.error(f'Помилка: {e}')

# --- РОЗРАХУНОК СУМ ЗА СЬОГОДНІ ---
today_df = df_data[df_data['Дата'].astype(str) == date_str]

consumed = today_df['Спожито'].sum()
burned = today_df['Спалено'].sum()
protein = today_df['Білки'].sum()
fat = today_df['Жири'].sum()
carbs = today_df['Вуглеводи'].sum()

# --- ВІДОБРАЖЕННЯ ПРОГРЕСУ ---
if not today_df.empty:
    st.markdown(f"**📅 {date_str} ({DAYS_UA.get(now.strftime('%A'))})**")

    p_kcal = protein * 4
    f_kcal = fat * 9
    c_kcal = carbs * 4
    total_macro_kcal = p_kcal + f_kcal + c_kcal

    if total_macro_kcal > 0:
        p_pct = round((p_kcal / total_macro_kcal) * 100)
        f_pct = round((f_kcal / total_macro_kcal) * 100)
        p_deg = int((p_pct / 100) * 360)
        f_deg = p_deg + int((f_pct / 100) * 360)
        gradient_style = f"background: conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg {f_deg}deg, #FF6384 {f_deg}deg 360deg);"
    else:
        gradient_style = "background: #333;"

    percent_target = min(100, int((consumed / BASE_CALORIE_TARGET) * 100))

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

    # Відображення списку всіх записів за сьогодні
    log_lines = []
    for _, row in today_df.iterrows():
        icon = "💪" if row['Тип'] == 'Тренування' else "🍽️"
        kcal_val = row['Спалено'] if row['Тип'] == 'Тренування' else row['Спожито']
        log_lines.append(f"• {row['Час']} {icon} {row['Опис']} — <b>{int(kcal_val)} ккал</b>")

    st.markdown(f"""
        <div class="food-box">
            <b>📝 Лог за сьогодні:</b><br>
            {"<br>".join(log_lines)}
        </div>
    """, unsafe_allow_html=True)

    # --- КНОПКИ ВИДАЛЕННЯ (ЗАПИС/ДЕНЬ) ---
    st.markdown("---")
    st.markdown("### 🗑️ Видалення записів")
    
    # Випадаючий список конкретних записів
    options = {}
    for idx, row in today_df.iterrows():
        icon = "💪" if row['Тип'] == 'Тренування' else "🍽️"
        kcal_val = row['Спалено'] if row['Тип'] == 'Тренування' else row['Спожито']
        label = f"[{row['Час']}] {icon} {row['Опис']} ({int(kcal_val)} ккал)"
        options[label] = idx

    selected_entry = st.selectbox("Вибери конкретний запис, який хочеш стерти:", list(options.keys()))

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Видалити вибраний запис", type='secondary', use_container_width=True):
            target_idx = options[selected_entry]
            df_data = df_data.drop(target_idx)
            df_data.to_excel(EXCEL_FILE, index=False)
            st.success("Запис видалено!")
            st.rerun()

    with col_btn2:
        if st.button("⚠️ Очистити весь день", type='primary', use_container_width=True):
            df_data = df_data[df_data['Дата'].astype(str) != date_str]
            df_data.to_excel(EXCEL_FILE, index=False)
            st.success("Весь день очищено!")
            st.rerun()
