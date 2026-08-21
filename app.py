from datetime import datetime, timedelta, timezone
import json
import os
from google import genai
from google.genai import types
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import streamlit as st

# ============================================================
# 1. НАЛАШТУВАННЯ СТОРІНКИ ТА ЧАСОВОГО ПОЯСУ
# ============================================================
st.set_page_config(
    page_title="Мій Фітнес Трекер", page_icon="🏋️‍♂️", layout="centered"
)

try:
  from zoneinfo import ZoneInfo

  LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
  LOCAL_TZ = timezone(timedelta(hours=2))

# ============================================================
# 2. ПРОФІЛЬ
# ============================================================
profile = st.sidebar.selectbox("👤 Виберіть профіль", ["Я", "Дружина"])

# ============================================================
# 3. GEMINI API ПІДКТЮЧЕННЯ
# ============================================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
  st.error("⚠️ Не знайдено GEMINI_API_KEY у Secrets!")
  st.stop()

client = genai.Client(api_key=api_key)


# ============================================================
# 4. GOOGLE SHEETS ПІДКТЮЧЕННЯ
# ============================================================
@st.cache_resource
def init_gsheet():
  scope = [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive",
  ]
  creds = Credentials.from_service_account_info(
      st.secrets["gcp_service_account"], scopes=scope
  )
  return gspread.authorize(creds)


try:
  gs_client = init_gsheet()
  # Відкриваємо Google Таблицю з назвою "Мій Фітнес"
  spreadsheet = gs_client.open("Мій Фітнес")

  # Вибираємо або створюємо вкладку для відповідного профілю
  try:
    sheet = spreadsheet.worksheet(profile)
  except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(title=profile, rows=1000, cols=10)

  # Перевіряємо та створюємо заголовки колонок, якщо таблиця порожня
  headers = [
      "Дата",
      "Час",
      "Опис",
      "Тип",
      "Спожито",
      "Спалено",
      "Білки",
      "Жири",
      "Вуглеводи",
  ]
  if not sheet.get_all_values():
    sheet.append_row(headers)

except Exception as e:
  st.error(f"❌ Помилка підключення до Google Sheets: {e}")
  st.info(
      "Перевірте, чи надано доступ вашому сервісному акаунту до Google"
      " Таблиці 'Мій Фітнес'."
  )
  st.stop()

# ============================================================
# 5. ІНТЕРФЕЙС ТА КАЛЕНДАР
# ============================================================
st.title("🏋️‍♂️ Фітнес Трекер")

# Календар для вибору дати запису
selected_date = st.date_input("📅 Виберіть дату", value=datetime.now(LOCAL_TZ))

user_input = st.text_input("📝 Введіть опис (наприклад: 'Вівсянка з бананом 250г')")
photo = st.camera_input("📷 Зробити фото їжі або тренування")


def clean_text(val):
  return str(val).strip() if val is not None else ""


def clean_number(val):
  try:
    return float(val)
  except (ValueError, TypeError):
    return 0.0


# ============================================================
# 6. ОБРОБКА ТА ДОДАВАННЯ ЗАПИСУ
# ============================================================
if st.button("✅ Додати запис", type="primary", use_container_width=True):
  if not user_input and not photo:
    st.warning("Введіть текст або зробіть фото.")
  else:
    with st.spinner("Gemini аналізує дані..."):
      try:
        prompt = """
Ти аналізуєш запис для фітнес-трекера.
Потрібно визначити:
1. їжа це чи тренування;
2. калорії;
3. білки, жири, вуглеводи;
4. якщо це тренування — спалені калорії.

Поверни ТІЛЬКИ JSON такого формату:
{
  "description": "короткий опис",
  "type": "Їжа",
  "consumed_kcal": 0,
  "burned_kcal": 0,
  "protein": 0,
  "fat": 0,
  "carbs": 0
}

Для їжі: type = "Їжа", consumed_kcal > 0, burned_kcal = 0.
Для тренування: type = "Тренування", consumed_kcal = 0, burned_kcal > 0.
Усі числа мають бути числовими.
Поверни тільки JSON.
"""
        if photo:
          image_part = types.Part.from_bytes(
              data=photo.getvalue(), mime_type="image/jpeg"
          )
          response = client.models.generate_content(
              model="gemini-2.5-flash",
              contents=[image_part, prompt],
              config=types.GenerateContentConfig(
                  response_mime_type="application/json"
              ),
          )
        else:
          text_prompt = prompt + f"\n\nЗапис користувача: {user_input}"
          response = client.models.generate_content(
              model="gemini-2.5-flash",
              contents=text_prompt,
              config=types.GenerateContentConfig(
                  response_mime_type="application/json"
              ),
          )

        raw = (response.text or "").strip()
        if raw.startswith("```"):
          raw = raw.replace("```json", "").replace("```", "").strip()

        result = json.loads(raw)

        description = clean_text(
            result.get("description", user_input or "Запис")
        )
        entry_type = clean_text(result.get("type", "Їжа"))
        if entry_type not in ["Їжа", "Тренування"]:
          entry_type = "Їжа"

        consumed_kcal = (
            0.0
            if entry_type == "Тренування"
            else clean_number(result.get("consumed_kcal", 0))
        )
        burned_kcal = (
            clean_number(result.get("burned_kcal", 0))
            if entry_type == "Тренування"
            else 0.0
        )
        protein_val = clean_number(result.get("protein", 0))
        fat_val = clean_number(result.get("fat", 0))
        carbs_val = clean_number(result.get("carbs", 0))

        now_time = datetime.now(LOCAL_TZ).strftime("%H:%M")
        date_str = selected_date.strftime("%Y-%m-%d")

        # Формуємо новий рядок
        new_row = [
            date_str,
            now_time,
            description,
            entry_type,
            consumed_kcal,
            burned_kcal,
            protein_val,
            fat_val,
            carbs_val,
        ]

        # Додаємо у Google Таблицю
        sheet.append_row(new_row)
        st.success("✅ Запис успішно збережено в Google Таблицю!")
        st.rerun()

      except json.JSONDecodeError:
        st.error("❌ Не вдалося розпізнати JSON від Gemini.")
      except Exception as error:
        st.error(f"❌ Помилка: {error}")

# ============================================================
# 7. ВІДОБРАЖЕННЯ ТАБЛИЦІ ЗА ВИБРАНИЙ ДЕНЬ
# ============================================================
st.divider()
st.subheader(f"📊 Записи за {selected_date.strftime('%Y-%m-%d')}")

try:
  records = sheet.get_all_records()
  if records:
    df = pd.DataFrame(records)
    if "Дата" in df.columns:
      filtered_df = df[df["Дата"] == selected_date.strftime("%Y-%m-%d")]
      if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True)
      else:
        st.info("На цю дату записів немає.")
    else:
      st.dataframe(df, use_container_width=True)
  else:
    st.info("Таблиця поки що порожня.")
except Exception as e:
  st.warning(f"Неможливо відобразити дані: {e}")
