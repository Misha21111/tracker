import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date
import google.generativeai as genai

# --- 1. Конфігурація сторінки та стилі ---
st.set_page_config(page_title="Фітнес Трекер & Калорії", page_icon="🏋️‍♂️", layout="wide")

st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .metric-card { background-color: #1e222a; padding: 15px; border-radius: 10px; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# --- 2. Ініціалізація Session State ---
if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []  # Зберігає до 20 дій

# --- 3. Підключення до Google Sheets & Gemini ---
@st.cache_resource
def init_google_sheet():
    credentials = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(credentials)
    sh = gc.open_by_url(st.secrets["GSHEET_URL"])
    return sh.sheet1

try:
    sheet = init_google_sheet()
except Exception as e:
    st.error(f"Помилка підключення до Google Sheets: {e}")
    st.stop()

# Налаштування Gemini API (якщо додано в Secrets)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 4. Бокова панель: Вибір профілю та Налаштування ---
st.sidebar.title("👤 Профіль")
current_user = st.sidebar.selectbox("Оберіть користувача", ["Користувач 1", "Користувач 2"])

st.sidebar.divider()
st.sidebar.subheader("🎯 Денні цілі")
target_calories = st.sidebar.number_input("Ціль калорій (ккал)", value=2200, step=50)
target_protein = st.sidebar.number_input("Ціль білка (г)", value=160, step=5)

# --- 5. Основний інтерфейс ---
st.title(f"🏋️‍♂️ Фітнес Трекер — {current_user}")

tab_log, tab_stats, tab_ai, tab_manage = st.tabs([
    "📝 Ввід даних", 
    "📊 Статистика & Лог", 
    "🤖 Gemini AI Аналіз", 
    "⚙️ Управління (Undo/Видалення)"
])

# --- Вкладка 1: Ввід даних ---
with tab_log:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🍕 Додати їжу / Вправу")
        with st.form("add_log_form", clear_on_submit=True):
            entry_date = st.date_input("Дата", value=date.today())
            entry_time = st.time_input("Час", value=datetime.now().time()).strftime("%H:%M")
            entry_type = st.selectbox("Тип", ["Харчування", "Тренування"])
            desc = st.text_input("Опис (назва страви чи вправи)")
            
            c1, c2 = st.columns(2)
            consumed = c1.number_input("Спожито (ккал)", min_value=0, value=0)
            burned = c2.number_input("Спалено (ккал)", min_value=0, value=0)
            
            p1, p2, p3 = st.columns(3)
            protein = p1.number_input("Білки (г)", min_value=0.0, value=0.0, step=0.1)
            fat = p2.number_input("Жири (г)", min_value=0.0, value=0.0, step=0.1)
            carbs = p3.number_input("Вуглеводи (г)", min_value=0.0, value=0.0, step=0.1)
            
            details = st.text_area("Деталі / Склад продуктів")
            
            submit_log = st.form_submit_button("Зберегти запис")
            
            if submit_log:
                row = [
                    str(entry_date), str(entry_time), current_user, desc, 
                    entry_type, consumed, burned, protein, fat, carbs, details
                ]
                sheet.append_row(row)
                
                # Запис у стек скасування (ліміт 20)
                st.session_state.undo_stack.append({"type": "add_row", "date": str(entry_date)})
                if len(st.session_state.undo_stack) > 20:
                    st.session_state.undo_stack.pop(0)
                    
                st.success("Запис збережено!")
                st.rerun()

    with col_right:
        st.subheader("⚖️ Зафіксувати вагу")
        with st.form("weight_form", clear_on_submit=True):
            w_date = st.date_input("Дата заміру", value=date.today(), key="w_date")
            weight_val = st.number_input("Вага (кг)", min_value=30.0, max_value=200.0, value=90.0, step=0.1)
            submit_weight = st.form_submit_button("Зберегти вагу")
            
            if submit_weight:
                row = [str(w_date), datetime.now().strftime("%H:%M"), current_user, "Замір ваги", "Вага", 0, 0, 0, 0, 0, f"Вага: {weight_val} кг"]
                sheet.append_row(row)
                
                st.session_state.undo_stack.append({"type": "add_row", "date": str(w_date)})
                if len(st.session_state.undo_stack) > 20:
                    st.session_state.undo_stack.pop(0)
                    
                st.success("Вагу збережено!")
                st.rerun()

# --- Вкладка 2: Статистика & Лог ---
with tab_stats:
    st.subheader("📈 Лог записів")
    try:
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # Фільтрація по поточного користувачеві, якщо є колонка Профіль/Користувач
            if "Користувач" in df.columns:
                df_user = df[df["Користувач"] == current_user]
            else:
                df_user = df
                
            st.dataframe(df_user, use_container_width=True)
            
            # Підсумки за сьогодні
            today_str = str(date.today())
            df_today = df_user[df_user["Дата"] == today_str] if "Дата" in df_user.columns else pd.DataFrame()
            
            if not df_today.empty:
                st.divider()
                st.subheader("🎯 Денний підсумок за сьогодні")
                
                tot_consumed = pd.to_numeric(df_today.get("Спожито (ккал)", 0), errors="coerce").sum()
                tot_burned = pd.to_numeric(df_today.get("Спалено (ккал)", 0), errors="coerce").sum()
                tot_protein = pd.to_numeric(df_today.get("Білки (г)", 0), errors="coerce").sum()
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Спожито", f"{tot_consumed:.0f} ккал", delta=f"{tot_consumed - target_calories:.0f} від цілі")
                m2.metric("Спалено", f"{tot_burned:.0f} ккал")
                m3.metric("Баланс", f"{tot_consumed - tot_burned:.0f} ккал")
                m4.metric("Білок", f"{tot_protein:.1f} г", delta=f"{tot_protein - target_protein:.1f} г")
        else:
            st.info("Таблиця порожня.")
    except Exception as e:
        st.error(f"Помилка завантаження логу: {e}")

# --- Вкладка 3: AI Аналіз (Gemini) ---
with tab_ai:
    st.subheader("🤖 ШІ Консультант")
    user_prompt = st.text_area("Запитайте Gemini про раціон, дефіцит калорій або тренування:")
    if st.button("Проаналізувати раціон"):
        if "GEMINI_API_KEY" in st.secrets:
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(user_prompt)
                st.markdown("### Відповідь AI:")
                st.write(response.text)
            except Exception as e:
                st.error(f"Помилка Gemini API: {e}")
        else:
            st.warning("Ключ GEMINI_API_KEY не знайдено в st.secrets.")

# --- Вкладка 4: Управління (Undo 20 дій & Видалення дня) ---
with tab_manage:
    st.subheader("⚙️ Керування даними та історією")
    
    col_u, col_d = st.columns(2)
    
    with col_u:
        st.write("### ⏪ Скасування дій (Undo)")
        st.info(f"Доступно кроків для скасування: **{len(st.session_state.undo_stack)} / 20**")
        
        if st.button("Скасувати останній запис"):
            if len(st.session_state.undo_stack) > 0:
                records = sheet.get_all_records()
                if records:
                    sheet.delete_rows(len(records) + 1)
                    st.session_state.undo_stack.pop()
                    st.success("Останню дію скасовано!")
                    st.rerun()
                else:
                    st.warning("Таблиця вже порожня.")
            else:
                st.warning("Немає дій у черзі скасування (ліміт 20 вичерпано або записи відсутні).")

    with col_d:
        st.write("### 🗑️ Повне видалення дня")
        target_del_date = st.date_input("Оберіть дату для повного очищення", value=date.today())
        
        if st.button("Видалити ВСІ записи за обраний день"):
            records = sheet.get_all_records()
            if records:
                rows_to_delete = [
                    i + 2 for i, row in enumerate(records) 
                    if str(row.get("Дата")) == str(target_del_date)
                ]
                
                if rows_to_delete:
                    # Видаляємо з кінця в початок
                    for row_idx in reversed(rows_to_delete):
                        sheet.delete_rows(row_idx)
                    st.success(f"Усі записи за {target_del_date} видалено ({len(rows_to_delete)} рядків).")
                    st.rerun()
                else:
                    st.info(f"За дату {target_del_date} записів не знайдено.")
            else:
                st.warning("Таблиця порожня.")
