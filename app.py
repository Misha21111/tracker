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

# Словник складних страв: як автоматично розбивати на інгредієнти
RECIPES = {
    'плов': [
        ('рис варений', 0.50),       # 50% від ваги
        ('куряче філе', 0.35),      # 35% від ваги
        ('овочі', 0.15)              # 15% від ваги (морква, цибуля)
    ],
    'йогурт з чіа і ківі': [
        ('йогурт грецький', 0.70),   # 70% від ваги
        ('насіння чіа', 0.10),      # 10% від ваги
        ('ківі', 0.20)               # 20% від ваги
    ],
    'йогурт з чіа': [
        ('йогурт грецький', 0.80),
        ('насіння чіа', 0.20)
    ]
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
    
    # Перевірка чи це складна страва з рецептів
    matched_recipe = None
    for key in RECIPES:
        if key in name_lower:
            matched_recipe = RECIPES[key]
            break
            
    if matched_recipe:
        # Розбиваємо страву на інгредієнти відповідно до відсотків
        items = []
        for ing_name, ratio in matched_recipe:
            items.append((ing_name, grams * ratio))
        return items
    else:
        return [(name, grams)]

st.set_page_config(page_title="Облік фітнесу", layout="wide")
st.title("🏋️ Облік фітнесу")

with st.container(border=True):
    st.markdown("### 📥 Введіть дані за сьогодні")
    user_input = st.text_input(
        "Рядок введення:", 
        placeholder="Наприклад: кроки 10000, 450 ккал, плов з куркою 300, йогурт з чіа і ківі 200",
        label_visibility="collapsed"
    )
    submit_btn = st.button("Записати в таблицю", type="primary")

if submit_btn and user_input:
    parts = [p.strip() for p in user_input.split(',')]
    steps = 0
    kcal_burned = 0.0
    total_kcal = total_p = total_f = total_c = 0.0

    for part in parts:
        part_lower = part.lower()
        if 'крок' in part_lower:
            nums = re.findall(r'\d+', part)
            if nums: steps = int(nums[0])
            continue
        if 'ккал' in part_lower or 'спалено' in part_lower or 'калор' in part_lower:
            nums = re.findall(r'\d+(?:\.\d+)?', part)
            if nums: kcal_burned = float(nums[0])
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
        
        # Автоматичний розбір складної страви на компоненти
        food_components = process_food_item(raw_name, grams)
        
        for ing_name, ing_grams in food_components:
            prod = get_product_from_api(ing_name)
            if prod:
                f = ing_grams / 100.0
                total_kcal += prod['kcal'] * f
                total_p += prod['protein'] * f
                total_f += prod['fat'] * f
                total_c += prod['carbs'] * f

    balance = total_kcal - kcal_burned
    now = pd.Timestamp.today()
    date_str = now.strftime('%Y-%m-%d')
    day_name_ua = DAYS_UA.get(now.strftime('%A'), '')

    new_row = pd.DataFrame({
        'Дата': [date_str],
        'День тижня': [day_name_ua],
        'Кроки': [steps],
        'Спалено (ккал)': [kcal_burned],
        'Спожито (ккал)': [round(total_kcal, 1)],
        'Білки (г)': [round(total_p, 1)],
        'Жири (г)': [round(total_f, 1)],
        'Вуглеводи (г)': [round(total_c, 1)],
        'Баланс (ккал)': [round(balance, 1)]
    })

    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df = df[df['Дата'] != date_str]
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    
    df = df.sort_values(by='Дата', ascending=False)
    df.to_excel(EXCEL_FILE, index=False)
    st.success("✅ Запис успішно додано до таблиці!")

if os.path.exists(EXCEL_FILE):
    st.divider()
    st.subheader("📅 Таблиця обліку")
    st.dataframe(pd.read_excel(EXCEL_FILE), use_container_width=True)
