import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
import plotly.graph_objects as go
from google import genai
from google.genai import types

LOCAL_TZ = timezone(timedelta(hours=2))
st.set_page_config(page_title="Мій Фітнес", layout="centered")
EXCEL_FILE = "fitness_entries.xlsx"

api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    return pd.DataFrame(columns=["Дата", "Час", "Опис", "Тип", "Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"])

def clean_float(val):
    try: return float(val)
    except: return 0.0

st.title("🏋️ Мій Фітнес")

# Форма вводу (зверху)
user_input = st.text_input("📥 Що з'їв або тренування:", placeholder="Наприклад: з'їв 30г хліба")
uploaded_photo = st.file_uploader("📸 Додати фото їжі", type=["jpg", "jpeg", "png"])
if st.button("Записати в лог", type="primary", use_container_width=True):
    if not user_input and uploaded_photo is None:
        st.error("⚠️ Введіть опис або завантажте фото!")
    else:
        with st.spinner("🧠 Gemini аналізує..."):
            try:
                if uploaded_photo:
                    image_bytes = uploaded_photo.getvalue()
                    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                    prompt = "Проаналізуй страву. Поверни JSON з ключами: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs."
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=[image_part, prompt], config=types.GenerateContentConfig(response_mime_type="application/json"))
                else:
                    prompt = f'Аналізуй: "{user_input}". Поверни JSON з ключами: food_description, kcal_burned, total_consumed_kcal, total_protein, total_fat, total_carbs.'
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
                
                data = json.loads(response.text)
                new_entry = pd.DataFrame([{
                    "Дата": datetime.now(LOCAL_TZ).strftime("%Y-%m-%d"),
                    "Час": datetime.now(LOCAL_TZ).strftime("%H:%M"),
                    "Опис": data.get("food_description", user_input or "Їжа/Тренування"),
                    "Тип": "Тренування" if clean_float(data.get("kcal_burned")) > 0 else "Їжа",
                    "Спожито": clean_float(data.get("total_consumed_kcal")),
                    "Спалено": clean_float(data.get("kcal_burned")),
                    "Білки": clean_float(data.get("total_protein")),
                    "Жири": clean_float(data.get("total_fat")),
                    "Вуглеводи": clean_float(data.get("total_carbs"))
                }])
                
                df = load_data()
                df = pd.concat([df, new_entry], ignore_index=True)
                df.to_excel(EXCEL_FILE, index=False)
                st.success("✅ Записано!")
                st.rerun()
            except Exception as e:
                st.error(f"Помилка: {e}")

st.markdown("---")

# Завантажуємо дані для блоків
df = load_data()
today_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

# Фільтруємо за сьогодні, якщо є колонка дат, або беремо всі
if not df.empty and "Дата" in df.columns:
    df_today = df[df["Дата"] == today_str]
else:
    df_today = df

consumed_today = df_today["Спожито"].sum() if not df_today.empty else 0
burned_today = df_today["Спалено"].sum() if not df_today.empty else 0
protein_today = df_today["Білки"].sum() if not df_today.empty else 0
fat_today = df_today["Жири"].sum() if not df_today.empty else 0
carbs_today = df_today["Вуглеводи"].sum() if not df_today.empty else 0

GOAL_KCAL = 2000
GOAL_P, GOAL_F, GOAL_C = 160, 70, 180

# 1. Кругова діаграма (як на скріншоті)
fig = go.Figure(data=[go.Pie(
    values=[consumed_today, max(0, GOAL_KCAL - consumed_today)],
    hole=0.65,
    marker_colors=['#ff5252', '#333333'],
    textinfo='none',
    hoverinfo='none'
)])
fig.update_layout(
    showlegend=False,
    annotations=[{
        'text': f"<b>{consumed_today:.0f}</b><br>із {GOAL_KCAL} ккал<br>{int((consumed_today/GOAL_KCAL)*100)}%",
        'x': 0.5, 'y': 0.5, 'font_size': 16, 'showarrow': False, 'font_color': 'white'
    }],
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(t=10, b=10, l=10, r=10),
    height=250
)
st.plotly_chart(fig, use_container_width=True)

# Прогрес БЖВ під кільцем
st.markdown(f"<p style='text-align: center;'>🥩 {protein_today:.0f}/{GOAL_P}г &nbsp;&nbsp;&nbsp; 🥑 {fat_today:.0f}/{GOAL_F}г &nbsp;&nbsp;&nbsp; 🍞 {carbs_today:.0f}/{GOAL_C}г</p>", unsafe_allow_html=True)

# 2. Блоки Спожито та Спалено
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333;">
        <p style="color: #888; margin: 0;">🍽️ З'їв</p>
        <h2 style="margin: 5px 0 0 0; color: white;">{consumed_today:.0f} ккал</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333;">
        <p style="color: #888; margin: 0;">🔥 Спалено</p>
        <h2 style="margin: 5px 0 0 0; color: white;">{burned_today:.0f} ккал</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 3. Лог (історія)
st.subheader("📋 Лог:")
if not df.empty:
    for idx, row in df.tail(10).iloc[::-1].iterrows():
        icon = "💪" if row['Тип'] == "Тренування" else "🍽️"
        st.markdown(f"""
        <div style="background-color: #1a1a1a; padding: 10px 15px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">
            <span>{row['Час']} {icon} {row['Опис']}</span>
            <span style="color: #00bcd4; font-weight: bold;">{row['Спожито'] if row['Тип'] != 'Тренування' else row['Спалено']} ккал</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Поки що немає записів.")
