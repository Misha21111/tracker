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
    user_input = st.text_input('📥 Введи, що зїв / тренування:', placeholder="Наприклад: з'їв 30г хліба, спалено 300 ккал або Калорії 161")
    submit_btn = st.button('Записати', type='primary', use_container_width=True)

now = pd.Timestamp.today()
date_str = now.strftime('%Y-%m-%d')
log_file = 'fitness_logs.xlsx' # Окремий файл для детальної історії записів за день

if submit_btn and user_input:
    prompt = f"""Аналізуй текст: "{user_input}". 
    Визнач, чи це їжа/калорії які людина спожила, чи це спалені калорії на тренуванні/активності.
    Якщо в тексті є слова "спалено", "тренування", "калорії" у контексті витрати чи просто цифра тренування — записуй їх у kcal_burned. Якщо це їжа — у total_consumed_kcal.
    Поверни JSON із полями: 
    food_description (опис), 
    steps (число кроків або 0), 
    kcal_burned (спалені калорії або 0), 
    total_consumed_kcal (спожиті калорії або 0), 
    total_protein (0), total_fat (0), total_carbs (0)."""
    
    try:
        response = client.models.generate_content(model='gemini-3.6-flash', contents=prompt, config=types.GenerateContentConfig(response_mime_type='application/json'))
        data = json.loads(response.text)
        
        # 1. Зберігаємо детальний запис в історію логів
        if os.path.exists(log_file): df_logs = pd.read_excel(log_file)
        else: df_logs = pd.DataFrame(columns=['Дата', 'Опис', 'Тип', 'Калорії', 'Білки', 'Жири', 'Вуглеводи'])

        c_consumed = float(data.get('total_consumed_kcal') or 0)
        c_burned = float(data.get('kcal_burned') or 0)
        c_protein = float(data.get('total_protein') or 0)
        c_fat = float(data.get('total_fat') or 0)
        c_carbs = float(data.get('total_carbs') or 0)
        c_desc = str(data.get('food_description') or user_input)

        if c_consumed > 0:
            new_log = pd.DataFrame({'Дата': [date_str], 'Опис': [c_desc], 'Тип': ['Їжа'], 'Калорії': [c_consumed], 'Білки': [c_protein], 'Жири': [c_fat], 'Вуглеводи': [c_carbs]})
            df_logs = pd.concat([df_logs, new_log], ignore_index=True)
        elif c_burned > 0:
            new_log = pd.DataFrame({'Дата': [date_str], 'Опис': [f"Тренування: {c_burned} ккал"], 'Тип': ['Тренування'], 'Калорії': [c_burned], 'Білки': [0], 'Жири': [0], 'Вуглеводи': [0]})
            df_logs = pd.concat([df_logs, new_log], ignore_index=True)
        else:
            new_log = pd.DataFrame({'Дата': [date_str], 'Опис': [c_desc], 'Тип': ['Їжа'], 'Калорії': [0], 'Білки': [0], 'Жири': [0], 'Вуглеводи': [0]})
            df_logs = pd.concat([df_logs, new_log], ignore_index=True)
            
        df_logs.to_excel(log_file, index=False)

        # 2. Перераховуємо загальний звіт за день та зберігаємо в EXCEL_FILE
        df_day_logs = df_logs[df_logs['Дата'].astype(str) == date_str]
        total_cons = df_day_logs[df_day_logs['Тип'] == 'Їжа']['Калорії'].sum()
        total_burn = df_day_logs[df_day_logs['Тип'] == 'Тренування']['Калорії'].sum()
        total_prot = df_day_logs['Білки'].sum()
        total_fat_val = df_day_logs['Жири'].sum()
        total_carb = df_day_logs['Вуглеводи'].sum()
        all_descs = "; ".join(df_day_logs['Опис'].astype(str).tolist())

        if os.path.exists(EXCEL_FILE): df = pd.read_excel(EXCEL_FILE)
        else: df = pd.DataFrame(columns=['Дата', 'День тижня', 'Раціон', 'Кроки', 'Спалено (ккал)', 'Спожито (ккал)', 'Білки (г)', 'Жири (г)', 'Вуглеводи (г)', 'Баланс (ккал)'])

        if date_str in df['Дата'].astype(str).values:
            idx = df[df['Дата'].astype(str) == date_str].index[0]
            df.loc[idx, 'Раціон'] = all_descs
            df.loc[idx, 'Спожито (ккал)'] = total_cons
            df.loc[idx, 'Спалено (ккал)'] = total_burn
            df.loc[idx, 'Білки (г)'] = total_prot
            df.loc[idx, 'Жири (г)'] = total_fat_val
            df.loc[idx, 'Вуглеводи (г)'] = total_carb
            df.loc[idx, 'Баланс (ккал)'] = total_cons - total_burn
        else:
            new_row = pd.DataFrame({
                'Дата': [date_str], 'День тижня': [DAYS_UA.get(now.strftime('%A'))], 
                'Раціон': [all_descs], 'Кроки': [0], 'Спалено (ккал)': [total_burn], 
                'Спожито (ккал)': [total_cons], 'Білки (г)': [total_prot], 
                'Жири (г)': [total_fat_val], 'Вуглеводи (г)': [total_carb], 'Баланс (ккал)': [total_cons - total_burn]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            
        df.to_excel(EXCEL_FILE, index=False)
        st.success('✅ Записано!')
        st.rerun()
    except Exception as e:
        st.error(f'Помилка: {e}')

# --- БЛОК ВИДАЛЕННЯ ТА ОЧИЩЕННЯ ---
if os.path.exists(log_file):
    df_logs_check = pd.read_excel(log_file)
    today_logs = df_logs_check[df_logs_check['Дата'].astype(str) == date_str]
    
    if not today_logs.empty:
        st.markdown("### 🗑️ Керування записами")
        col_del1, col_del2 = st.columns([2, 1])
        
        with col_del1:
            # Випадаючий список для вибору конкретного запису
            options = {f"{row['Тип']}: {row['Опис']} ({row['Калорії']} ккал) [ID: {idx}]": idx for idx, row in today_logs.iterrows()}
            selected_option = st.selectbox("Вибери запис для видалення:", options=list(options.keys()))
            
        with col_del2:
            st.write("") # відступ
            st.write("")
            if st.button("🗑️ Видалити вибране", use_container_width=True):
                target_idx = options[selected_option]
                df_logs_check = df_logs_check.drop(target_idx)
                df_logs_check.to_excel(log_file, index=False)
                
                # Перераховуємо підсумки дня після видалення
                df_day_logs = df_logs_check[df_logs_check['Дата'].astype(str) == date_str]
                total_cons = df_day_logs[df_day_logs['Тип'] == 'Їжа']['Калорії'].sum()
                total_burn = df_day_logs[df_day_logs['Тип'] == 'Тренування']['Калорії'].sum()
                total_prot = df_day_logs['Білки'].sum()
                total_fat_val = df_day_logs['Жири'].sum()
                total_carb = df_day_logs['Вуглеводи'].sum()
                all_descs = "; ".join(df_day_logs['Опис'].astype(str).tolist())
                
                df_main = pd.read_excel(EXCEL_FILE)
                idx_main = df_main[df_main['Дата'].astype(str) == date_str].index[0]
                
                if df_day_logs.empty:
                    df_main = df_main[df_main['Дата'].astype(str) != date_str]
                else:
                    df_main.loc[idx_main, 'Раціон'] = all_descs
                    df_main.loc[idx_main, 'Спожито (ккал)'] = total_cons
                    df_main.loc[idx_main, 'Спалено (ккал)'] = total_burn
                    df_main.loc[idx_main, 'Білки (г)'] = total_prot
                    df_main.loc[idx_main, 'Жири (г)'] = total_fat_val
                    df_main.loc[idx_main, 'Вуглеводи (г)'] = total_carb
                    df_main.loc[idx_main, 'Баланс (ккал)'] = total_cons - total_burn
                    
                df_main.to_excel(EXCEL_FILE, index=False)
                st.success("Вибраний запис видалено!")
                st.rerun()

        if st.button("🗑️ Очистити весь день повністю", use_container_width=True):
            df_logs_check = df_logs_check[df_logs_check['Дата'].astype(str) != date_str]
            df_logs_check.to_excel(log_file, index=False)
            
            df_main = pd.read_excel(EXCEL_FILE)
            df_main = df_main[df_main['Дата'].astype(str) != date_str]
            df_main.to_excel(EXCEL_FILE, index=False)
            st.success("День повністю очищено!")
            st.rerun()

# --- ВІДОБРАЖЕННЯ ІНФОРМАЦІЇ ---
if os.path.exists(EXCEL_FILE):
    df_current = pd.read_excel(EXCEL_FILE)
    if not df_current.empty and date_str in df_current['Дата'].astype(str).values:
        latest = df_current[df_current['Дата'].astype(str) == date_str].iloc[0]
        
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
                <b>📝 Лог за сьогодні:</b><br>{latest['Раціон']}
            </div>
        """, unsafe_allow_html=True)
