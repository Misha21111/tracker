import json
import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

EXCEL_FILE = 'fitness_tracker.xlsx'

# Ваші персональні норми (Цілі на день)
TARGETS = {
    'kcal': 2050,
    'protein': 170, # г
    'fat': 75,      # г
    'carbs': 190    # г
}

# ... (частина з ініціалізацією клієнта залишається такою ж)

# Оновлений промпт для ШІ, щоб він повертав і список їжі
prompt = f"""
    Проаналізуй текст: "{user_input}"
    Поверни JSON:
    {{
        "food_description": "короткий перелік їжі, наприклад: 'куряче філе 200г, рис 100г'",
        "steps": <число або null>,
        "kcal_burned": <число або null>,
        "total_consumed_kcal": <число>,
        "total_protein": <число>,
        "total_fat": <число>,
        "total_carbs": <число>
    }}
    """

# В блоці обробки додайте збереження тексту:
# df.loc[idx, 'Що з'їв'] = df.loc[idx, 'Що з'їв'] + "; " + data.get('food_description')

# В блоці відображення додайте діаграми або метрики для БЖВ:
col1, col2, col3, col4 = st.columns(4)
col1.metric('Калорії', f'{consumed}', delta=f'{consumed - TARGETS["kcal"]}')
col2.metric('Білки', f'{current_p}г', delta=f'{current_p - TARGETS["protein"]}г')
# ... і так далі для жирів та вуглеводів
