import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Мій Фітнес Трекер", page_icon="🏋️‍♂️", layout="wide")

# Ініціалізація історії дій для скасування (максимум 20)
if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []

# Підключення до Google Sheets
@st.cache_resource
def get_google_sheet():
    credentials = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(credentials)
    sh = gc.open_by_url(st.secrets["GSHEET_URL"])
    return sh.sheet1

try:
    sheet = get_google_sheet()
except Exception as e:
    st.error(f"Помилка підключення до Google Таблиці: {e}")
    st.stop()

st.title("🏋️‍♂️ Фітнес Трекер & Лог Калорій")

# 1. Форма додавання запису
st.subheader("➕ Додати новий запис")
with st.form("add_entry_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        entry_date = st.date_input("Дата", value=date.today())
        entry_time = st.time_input("Час", value=datetime.now().time()).strftime("%H:%M")
        entry_type = st.selectbox("Тип запису", ["Харчування", "Тренування", "Вага"])
        
    with col2:
        description = st.text_input("Опис / Назва вправи чи прийому їжі")
        consumed = st.number_input("Спожито (ккал)", min_value=0, value=0)
        burned = st.number_input("Спалено (ккал)", min_value=0, value=0)
        
    with col3:
        protein = st.number_input("Білки (г)", min_value=0.0, value=0.0, step=0.1)
        fat = st.number_input("Жири (г)", min_value=0.0, value=0.0, step=0.1)
        carbs = st.number_input("Вуглеводи (г)", min_value=0.0, value=0.0, step=0.1)
        
    products = st.text_area("Деталі / Продукти (необов'язково)")
    
    submit_button = st.form_submit_button("Зберегти запис")

if submit_button:
    new_row = [
        str(entry_date),
        str(entry_time),
        description,
        entry_type,
        consumed,
        burned,
        protein,
        fat,
        carbs,
        products
    ]
    sheet.append_row(new_row)
    
    # Додаємо мітку дії у стек скасувань (підтримуємо не більше 20 кроків)
    st.session_state.undo_stack.append(True)
    if len(st.session_state.undo_stack) > 20:
        st.session_state.undo_stack.pop(0)
        
    st.success("Запис успішно додано!")
    st.rerun()

st.divider()

# 2. Управління записувати та видалення
st.subheader("⚙️ Управління даними")

col_undo, col_delete = st.columns(2)

with col_undo:
    st.write(f"**Скасування дій у цій сесії** (доступно: **{len(st.session_state.undo_stack)}/20**)")
    if st.button("⏪ Скасувати останній запис"):
        if len(st.session_state.undo_stack) > 0:
            records = sheet.get_all_records()
            if records:
                # Видаляємо останній рядок у таблиці (індекс +1 враховує заголовок)
                sheet.delete_rows(len(records) + 1)
                st.session_state.undo_stack.pop()
                st.success("Останній запис скасовано!")
                st.rerun()
            else:
                st.warning("Таблиця порожня.")
        else:
            st.warning("Немає дій для скасування (ліміт 20 дій вичерпано або записів ще не додано).")

with col_delete:
    st.write("**Видалення цілого дня**")
    selected_date = st.date_input("Оберіть дату для видалення", value=date.today(), key="del_date_key")
    if st.button("🗑️ Видалити всі записи за день"):
        records = sheet.get_all_records()
        # Пошук усіх рядків з вибраною датою (+2 через наявність заголовка таблиці)
        rows_to_delete = [i + 2 for i, row in enumerate(records) if str(row.get("Дата")) == str(selected_date)]
        
        if rows_to_delete:
            # Видаляємо з кінця до початку, щоб не збивати індекси рядків
            for row_idx in reversed(rows_to_delete):
                sheet.delete_rows(row_idx)
            st.success(f"Усі записи за {selected_date} повністю видалено!")
            st.rerun()
        else:
            st.info("За вибрану дату записів не знайдено.")

st.divider()

# 3. Перегляд збережених даних
st.subheader("📊 Лог збережених записів")
try:
    records = sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Таблиця поки що порожня.")
except Exception as e:
    st.error(f"Помилка зчитування даних з Google Таблиці: {e}")
