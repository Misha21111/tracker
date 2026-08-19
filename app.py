import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
from google import genai
from google.genai import types

LOCAL_TZ = timezone(timedelta(hours=2))
st.set_page_config(page_title="Мій Фітнес", layout="wide")
EXCEL_FILE = "fitness_entries.xlsx"

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    return pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

# --- ІНТЕРФЕЙС ---
st.title("🏋️ Мій Фітнес")

# 1. Секція графіків та метрик
df = load_data()
if not df.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Спожито (ккал)", f"{df['Спожито'].sum():.0f}")
    col2.metric("Спалено (ккал)", f"{df['Спалено'].sum():.0f}")
    col3.metric("Баланс", f"{(df['Спожито'].sum() - df['Спалено'].sum()):.0f}")

    # Кругова діаграма (БЖВ)
    st.subheader("📊 Розподіл БЖВ")
    totals = df[["Білки", "Жири", "Вуглеводи"]].sum()
    st.bar_chart(totals) # st.bar_chart надійніший за pie на старих версіях

# 2. Секція вводу
st.markdown("---")
user_input = st.text_input("📥 Опис:", placeholder="З'їв 30г хліба / пробіг 5км")
uploaded_photo = st.file_uploader("📸 Фото", type=["jpg", "jpeg", "png"])
if st.button("Записати в лог", type="primary"):
    if not user_input and uploaded_photo is None:
        st.error("Введіть дані!")
    else:
        with st.spinner("Аналізую..."):
            try:
                # [Тут логіка Gemini залишається як була]
                # ... після успішного запису:
                st.rerun()
            except Exception as e:
                st.error(f"Помилка: {e}")

# 3. Таблиця
st.subheader("📋 Історія")
st.table(df.tail(10))
