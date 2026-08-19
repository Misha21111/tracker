import streamlit as st
import pandas as pd
import requests
import re
import os

EXCEL_FILE = 'fitness_tracker.xlsx'

DAYS_UA = {
    'Monday': 'Понеділок', 'Tuesday': 'Вівторок', 'Wednesday': 'Середа',
    'Thursday': 'Четвер', 'Friday': 'П’ятниця', 'Saturday': 'Субота', 'Sunday': 'Неділя'
}

RECIPES = {
    'плов': [('рис варений', 0.50), ('куряче філе', 0.35), ('овочі', 0.15)],
    'йогурт з чіа і ківі': [('йогурт грецький', 0.70), ('насіння чіа', 0.10), ('ківі', 0.20)],
    'йогурт з чіа': [('йогурт грецький', 0.80), ('насіння чіа', 0.20)]
}

def get_product_from_api(query):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&lc=uk"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            for p in data.get('products', []):
                nutri = p.get('nutriments', {})
                kcal = nutri.get('energy-kcal_100g')
                if kcal is not None:
                    return {
                        'kcal': float(kcal),
                        'protein': float(nutri.get('proteins_100g', 0)),
                        'fat': float(nutri.get('fat_100g', 0)),
                        'carbs': float(nutri.get('carbohydrates_100g', 0))
                    }
    except Exception:
        pass
    return None

def process_food_item(name, grams):
    name_lower = name.lower()
    matched_recipe = None
    for key in RECIPES:
        if key in name_lower:
            matched_recipe = RECIPES[key]
            break
            
    if matched_recipe:
        items = []
        for ing_name, ratio in matched_recipe:
            items.append((ing_name, grams * ratio))
        return items
    else:
        return [(name, grams)]

st.set_page_config(page_title="Облік фітнесу", layout="wide")
st.title("🏋️ Облік фітнесу")

with st.container(border=True):
    st.markdown("### 📥 Введіть дані")
    user_input = st.text_input(
        "Рядок введення:", 
        placeholder="Наприклад: кроки 5000, спалено 400, яйця 100",
        label_visibility="collapsed"
    )
    submit_btn = st.button("Записати", type="primary", use_container_width=True)

if submit_btn and user_input:
    parts = [p.strip() for p in user_input.split(',')]
    input_steps = 0
    steps_mentioned = False
    
    input_kcal_burned = 0.0
    kcal_burned_mentioned = False

    add_kcal = add_p = add_f = add_c = 0.0

    for part in parts:
        part_lower = part.lower()
        if 'крок' in part_lower:
            nums = re.findall(r'\d+', part)
            if nums: 
                input_steps = int(nums[0])
                steps_mentioned = True
            continue
        if 'ккал' in part_lower or 'спалено' in part_lower or 'калор' in part_lower:
            nums = re.findall(r'\d+(?:\.\d+)?', part)
            if nums: 
                input_kcal_burned = float(nums[0])
                kcal_burned_mentioned = True
            continue
        
        match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?)$', part)
        if match:
            raw_name, grams = match.group(1).strip(), float(match.group(2))
        else:
            match_rev = re.search(r'^(\d+(?:\.\d+)?)\s+(.+)$', part)
            if match_rev:
                grams, raw_name = float(match_rev.group(1)), match_rev.group(2).strip()
            else:
                continue
        
        food_components = process_food_item(raw_name, grams)
        for ing_name, ing_grams in food_components:
            prod = get_product_from_api(ing_name)
            if prod:
                f = ing_grams / 100.0
                add_kcal += prod['kcal'] * f
                add_p += prod['protein'] * f
                add_f += prod['fat'] * f
                add_c += prod['carbs'] * f

    now = pd.Timestamp.today()
    date_str = now.strftime('%Y-%m-%d')
    day_name_ua = DAYS_UA.get(now.strftime('%A'), '')

    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
    else:
        df = pd.DataFrame(columns=[
            'Дата', 'День тижня', 'Кроки', 'Спалено (ккал)', 
            'Спожито (ккал)', 'Білки (г)', 'Жири (г)', 'Вуглеводи (г)', 'Баланс (ккал)'
        ])

    if date_str in df['Дата'].astype(str).values:
        idx = df[df['Дата'].astype(str) == date_str].index[0]
        
        # Замінюємо кроки та спалені калорії, якщо вони вказані у записі
        if steps_mentioned:
            df.loc[idx, 'Кроки'] = input_steps
        if kcal_burned_mentioned:
            df.loc[idx, 'Спалено (ккал)'] = input_kcal_burned
        
        # Спожиту їжу плюсуємо до існуючої
        df.loc[idx, 'Спожито (ккал)'] = round(df.loc[idx, 'Спожито (ккал)'] + add_kcal, 1)
        df.loc[idx, 'Білки (г)'] = round(df.loc[idx, 'Білки (г)'] + add_p, 1)
        df.loc[idx, 'Жири (г)'] = round(df.loc[idx, 'Жири (г)'] + add_f, 1)
        df.loc[idx, 'Вуглеводи (г)'] = round(df.loc[idx, 'Вуглеводи (г)'] + add_c, 1)
        df.loc[idx, 'Баланс (ккал)'] = round(df.loc[idx, 'Спожито (ккал)'] - df.loc[idx, 'Спалено (ккал)'], 1)
    else:
        new_row = pd.DataFrame({
            'Дата': [date_str],
            'День тижня': [day_name_ua],
            'Кроки': [input_steps],
            'Спалено (ккал)': [input_kcal_burned],
            'Спожито (ккал)': [round(add_kcal, 1)],
            'Білки (г)': [round(add_p, 1)],
            'Жири (г)': [round(add_f, 1)],
            'Вуглеводи (г)': [round(add_c, 1)],
            'Баланс (ккал)': [round(add_kcal - input_kcal_burned, 1)]
        })
        df = pd.concat([df, new_row], ignore_index=True)

    df = df.sort_values(by='Дата', ascending=False)
    df.to_excel(EXCEL_FILE, index=False)
    st.success("✅ Дані оновлено!")

if os.path.exists(EXCEL_FILE):
    df_current = pd.read_excel(EXCEL_FILE)
    
    st.divider()
    st.subheader("📅 Таблиця обліку")
    st.dataframe(df_current, use_container_width=True)

    if not df_current.empty:
        with st.expander("🗑️ Видалити конкретний день"):
            dates_list = df_current['Дата'].astype(str).tolist()
            selected_date = st.selectbox("Оберіть дату для видалення:", dates_list)
            if st.button("Видалити обраний день", type="secondary"):
                df_updated = df_current[df_current['Дата'].astype(str) != selected_date]
                df_updated.to_excel(EXCEL_FILE, index=False)
                st.success(f"🗑️ Запис за {selected_date} видалено!")
                st.rerun()
