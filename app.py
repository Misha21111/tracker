import pandas as pd
import streamlit as st
from datetime import datetime
import json
import os
from google.genai import client, types

st.set_page_config(page_title="Мій Фітнес", layout="centered")

IMAGE_URL = "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"

st.markdown(
    f"""
    <style>
    .stApp {{ background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), url("{IMAGE_URL}"); background-size: cover; background-position: center; }}
    div[data-testid="stMetric"], div[data-testid="stMarkdownContainer"], div[data-testid="stVerticalBlockBorderWrapper"] {{ background-color: rgba(20, 20, 20, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 10px; color: white; }}
    .stButton button {{ width: 100%; border-radius: 8px; border: 1px solid #444; background-color: #1e1e1e; color: white; }}
    .stButton button:hover {{ border-color: #36A2EB; }}
    </style>
    """, unsafe_allow_html=True,
)

EXCEL_FILE = "fitness_entries.xlsx"
WEIGHT_FILE = "weight_data.json"
SETTINGS_FILE = "user_settings.json"

if "edit_mode" not in st.session_state: st.session_state["edit_mode"] = False

client = client.Client(api_key=st.secrets["GEMINI_API_KEY"])

def load_data():
    return pd.read_excel(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

df_data = load_data()

st.title("🏋️ Мій фітнес")

# --- КНОПКИ (вирівняні) ---
col1, col2 = st.columns(2)
with col1:
    if st.button("⚙️ Налаштування"): st.session_state["edit_mode"] = not st.session_state["edit_mode"]
with col2:
    if st.button("↩️ Видалити останнє"):
        if not df_data.empty:
            df_data.iloc[:-1].to_excel(EXCEL_FILE, index=False)
            st.rerun()

if st.session_state["edit_mode"]:
    with st.container(border=True):
        st.subheader("Редагування")
        # Тут ваші поля для редагування...
        if st.button("💾 Зберегти"): st.session_state["edit_mode"] = False; st.rerun()

# --- ОСНОВНИЙ БЛОК ---
today_str = datetime.now().strftime("%Y-%m-%d")
selected_date = st.selectbox("📅 Вибрати день для перегляду:", [today_str] + sorted(df_data["Дата"].astype(str).unique().tolist(), reverse=True))

with st.container(border=True):
    user_input = st.text_input("📥 Що з'їв / тренування:", placeholder="Наприклад: з'їв 30г хліба")
    if st.button("Записати в лог", type="primary", use_container_width=True):
        # Логіка запису через Gemini...
        st.rerun()

# --- ВИВЕДЕННЯ ДАНИХ ---
day_df = df_data[df_data["Дата"].astype(str) == selected_date]
if not day_df.empty:
    st.markdown(f"**📅 {selected_date} | Вага: ~89.0 кг**")
    # ... графіки та метрики
 
