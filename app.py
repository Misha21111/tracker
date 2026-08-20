import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# ============================================================
# ЧАСОВИЙ ПОЯС
# ============================================================

try:
  from zoneinfo import ZoneInfo

  LOCAL_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
  LOCAL_TZ = timezone(timedelta(hours=2))


# ============================================================
# НАЛАШТУВАННЯ STREAMLIT
# ============================================================

st.set_page_config(page_title="Мій Фітнес", page_icon="⚖️", layout="centered")


# ============================================================
# ПРОФІЛЬ ТА ФАЙЛИ
# ============================================================

user_profile = st.sidebar.selectbox(
    "👤 Профіль", ["Я", "Дружина"], key="user_profile_select"
)

profile_prefix = "user1" if user_profile == "Я" else "user2"

EXCEL_FILE = f"fitness_entries_{profile_prefix}.xlsx"
SETTINGS_FILE = f"user_settings_{profile_prefix}.json"
TRASH_FILE = f"fitness_trash_{profile_prefix}.json"
WATCH_FILE = f"watch_burned_{profile_prefix}.json"

IMAGE_URL = (
    "https://i.postimg.cc/kMS67m1J/Screenshot-20260819-175524-Facebook.jpg"
)


# ============================================================
# CSS СТИЛІ
# ============================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background:
            linear-gradient(
                rgba(0,0,0,.72),
                rgba(0,0,0,.88)
            ),
            url("{IMAGE_URL}") center / cover fixed;
    }}

    #MainMenu, footer {{ visibility: hidden; }}

    .block-container {{
        max-width: 760px;
        padding-top: 1rem;
        padding-bottom: 4rem;
    }}

    /* КНОПКИ */
    div.stButton > button {{
        border-radius: 16px !important;
        min-height: 48px !important;
        border: 1px solid rgba(255,255,255,.18) !important;
        background: rgba(30,32,40,.94) !important;
        color: white !important;
        font-weight: 700 !important;
        transition: transform .10s ease, background .10s ease, box-shadow .10s ease !important;
    }}

    div.stButton > button:hover {{
        border-color: rgba(255,255,255,.42) !important;
        background: rgba(45,48,59,.98) !important;
        transform: translateY(-1px);
    }}

    div.stButton > button:active {{
        transform: scale(.96) !important;
        background: rgba(70,73,88,1) !important;
        box-shadow: inset 0 3px 10px rgba(0,0,0,.55) !important;
    }}

    /* ПОЛЯ ВВОДУ */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {{
        background: rgba(32,33,43,.96) !important;
        border-radius: 15px !important;
        border-color: rgba(255,255,255,.10) !important;
    }}

    input {{
        color: white !important;
    }}

    /* СЕКЦІЇ ТА КРУЖОК */
    .section {{
        background: rgba(10,12,17,.68);
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 22px;
        padding: 18px;
        margin: 12px 0;
        backdrop-filter: blur(8px);
    }}

    .donut-wrap {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 12px 0 18px;
    }}

    .donut {{
        width: 230px;
        height: 230px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 30px rgba(0,0,0,.45);
    }}

    .donut-hole {{
        width: 164px;
        height: 164px;
        border-radius: 50%;
        background: #11131a;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        color: white;
        border: 1px solid rgba(255,255,255,.08);
    }}

    .balance {{
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 2px;
    }}

    .kcal-main {{
        font-size: 24px;
        font-weight: 900;
        line-height: 1.05;
    }}

    .kcal-sub {{
        color: #aeb3c2;
        font-size: 11px;
        margin-top: 2px;
    }}

    .weight-display {{
        margin-top: 6px;
        padding: 3px 8px;
        background: rgba(118, 199, 192, 0.15);
        border: 1px solid rgba(118, 199, 192, 0.3);
        border-radius: 10px;
        font-size: 13px;
        font-weight: 800;
        color: #76c7c0;
    }}

    /* МАКРОСИ БЖВ */
    .macros {{
        display: flex;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 14px;
    }}

    .macro {{
        border-radius: 14px;
        padding: 8px 11px;
        background: rgba(20,22,29,.92);
        border: 1px solid rgba(255,255,255,.10);
        font-size: 12px;
        font-weight: 700;
    }}

    .macro.p {{ color: #36A2EB; }}
    .macro.f {{ color: #FFCE56; }}
    .macro.c {{ color: #FF6384; }}

    /* КАРТКИ ЛОГУ */
    .log-card {{
        background: rgba(13,15,21,.80);
        border: 1px solid rgba(255,255,255,.13);
        border-radius: 18px;
        padding: 14px;
        margin: 12px 0;
    }}

    .log-head {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
    }}

    .log-title {{
        font-size: 16px;
        font-weight: 800;
    }}

    .log-kcal {{
        white-space: nowrap;
        font-size: 17px;
        font-weight: 900;
    }}

    .food-list {{
        margin-top: 10px;
        border-top: 1px solid rgba(255,255,255,.08);
        padding-top: 8px;
    }}

    .food-line {{
        display: flex;
        justify-content: space-between;
        gap: 10px;
        padding: 4px 0;
        font-size: 13px;
    }}

    .food-name {{ color: #e9ebf2; }}
    .food-cal {{ color: #8fd7ff; font-weight: 800; white-space: nowrap; }}

    .bju {{
        margin-top: 9px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        font-size: 12px;
        font-weight: 700;
    }}

    .bju span {{
        background: rgba(255,255,255,.06);
        border-radius: 10px;
        padding: 4px 8px;
    }}

    .status {{
        text-align: center;
        font-weight: 900;
        font-size: 17px;
        padding: 12px;
        border-radius: 16px;
        margin: 12px 0;
        line-height: 1.4;
    }}

    .deficit {{
        color: #5ee89a;
        background: rgba(20,120,65,.30);
        border: 1px solid rgba(94,232,154,.25);
    }}

    .surplus {{
        color: #ff7373;
        background: rgba(140,30,35,.30);
        border: 1px solid rgba(255,115,115,.25);
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# STATE ТА ІНІЦІАЛІЗАЦІЯ GEMINI
# ============================================================

if "edit_mode" not in st.session_state:
  st.session_state["edit_mode"] = False

if "selected_edit" not in st.session_state:
  st.session_state["selected_edit"] = None

if "undo_count" not in st.session_state:
  st.session_state["undo_count"] = 0

api_key = None
try:
  if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
  pass

if not api_key:
  api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
  st.error("⚠️ Не знайдено GEMINI_API_KEY у налаштуваннях.")
  st.stop()

client = genai.Client(api_key=api_key)
GEMINI_MODEL = "gemini-3.6-flash"

COLUMNS = [
    "Дата",
    "Час",
    "Опис",
    "Тип",
    "Спожито",
    "Спалено",
    "Білки",
    "Жири",
    "Вуглеводи",
    "Продукти",
]


# ============================================================
# ФУНКЦІЇ РОБОТИ З ДАНИМИ
# ============================================================


def load_settings():
  default = {
      "calories": 2000,
      "protein": 160,
      "fat": 70,
      "carbs": 180,
      "bmr_daily": 1850,
      "start_weight": 91.8,
  }
  if os.path.exists(SETTINGS_FILE):
    try:
      with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return {**default, **json.load(f)}
    except Exception:
      pass
  return default


def save_settings(s):
  with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
    json.dump(s, f, ensure_ascii=False, indent=2)


def load_data():
  empty = pd.DataFrame(columns=COLUMNS)
  if not os.path.exists(EXCEL_FILE):
    return empty
  try:
    df = pd.read_excel(EXCEL_FILE)
    for col in COLUMNS:
      if col not in df.columns:
        df[col] = "" if col in ["Опис", "Тип", "Продукти"] else 0
    df = df[COLUMNS]
    for col in ["Спожито", "Спалено", "Білки", "Жири", "Вуглеводи"]:
      df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["Дата"] = df["Дата"].astype(str)
    df["Час"] = df["Час"].astype(str).str[:5]
    df["Опис"] = df["Опис"].fillna("").astype(str)
    df["Тип"] = df["Тип"].fillna("Їжа").astype(str)
    df["Продукти"] = df["Продукти"].fillna("").astype(str)
    return df
  except Exception:
    return empty


def save_data(df):
  df.to_excel(EXCEL_FILE, index=False)


def load_watch():
  if not os.path.exists(WATCH_FILE):
    return {}
  try:
    with open(WATCH_FILE, "r", encoding="utf-8") as f:
      return {str(k): float(v) for k, v in json.load(f).items()}
  except Exception:
    return {}


def save_watch(d):
  with open(WATCH_FILE, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)


def normalize_products(products):
  res = []
  if not isinstance(products, list):
    return res
  for p in products:
    if isinstance(p, dict):
      name = str(p.get("name", "")).strip()
      if name and name.lower() != "nan":
        res.append({
            "name": name,
            "kcal": float(p.get("kcal", 0) or 0),
            "protein": float(p.get("protein", 0) or 0),
            "fat": float(p.get("fat", 0) or 0),
            "carbs": float(p.get("carbs", 0) or 0),
        })
  return res


def row_products(row):
  try:
    p = json.loads(row.get("Продукти", ""))
    if isinstance(p, list) and p:
      return normalize_products(p)
  except Exception:
    pass
  if str(row.get("Тип", "")) == "Їжа":
    desc = str(row.get("Опис", "")).strip()
    if desc and desc.lower() != "nan":
      return [{
          "name": desc,
          "kcal": float(row.get("Спожито", 0) or 0),
          "protein": float(row.get("Білки", 0) or 0),
          "fat": float(row.get("Жири", 0) or 0),
          "carbs": float(row.get("Вуглеводи", 0) or 0),
      }]
  return []


def today_bmr(settings, date_str):
  daily = float(settings.get("bmr_daily", 1850))
  today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
  if str(date_str) == today:
    now = datetime.now(LOCAL_TZ)
    hours = now.hour + now.minute / 60
    return daily * min(hours / 24, 1.0)
  return daily


def calculate_day(df, date_str, settings, watch_burned=0):
  day = df[df["Дата"].astype(str) == str(date_str)].copy()
  food = day[day["Тип"].astype(str) == "Їжа"]

  consumed = float(food["Спожито"].sum())
  protein = float(food["Білки"].sum())
  fat = float(food["Жири"].sum())
  carbs = float(food["Вуглеводи"].sum())

  exercise_df = day[
      (day["Тип"].astype(str) == "Тренування")
      & (~day["Опис"].str.contains("годинник", case=False, na=False))
  ]
  exercise = float(exercise_df["Спалено"].sum())
  watch = float(watch_burned or 0)

  burned = today_bmr(settings, date_str) + exercise + watch
  balance = burned - consumed

  return consumed, burned, balance, protein, fat, carbs, exercise, watch


def calculate_weight(df, settings, watch_dict):
  start_w = float(settings.get("start_weight", 91.8))
  if df.empty and not watch_dict:
    return start_w

  dates_df = set(df["Дата"].astype(str).unique()) if not df.empty else set()
  dates_watch = set(watch_dict.keys())
  all_dates = dates_df.union(dates_watch)

  if not all_dates:
    return start_w

  total_consumed = (
      float(df[df["Тип"] == "Їжа"]["Спожито"].sum()) if not df.empty else 0.0
  )
  total_exercise = (
      float(
          df[
              (df["Тип"] == "Тренування")
              & (~df["Опис"].str.contains("годинник", case=False, na=False))
          ]["Спалено"].sum()
      )
      if not df.empty
      else 0.0
  )
  total_watch = sum(float(v) for v in watch_dict.values())
  total_bmr = len(all_dates) * float(settings.get("bmr_daily", 1850))

  total_burned = total_bmr + total_exercise + total_watch
  net_balance = total_burned - total_consumed

  return start_w - (net_balance / 7700.0)


# ============================================================
# ЗАВАНТАЖЕННЯ ДАНИХ
# ============================================================

settings = load_settings()
df = load_data()
watch_by_date = load_watch()

st.title("⚖️ Мій Фітнес")
st.caption(f"Профіль: {user_profile}")


# ============================================================
# ФОРМА ДОДАВАННЯ
# ============================================================

st.markdown("### 🍽️ Додати запис")


def handle_add_click():
  st.session_state["pending_input"] = st.session_state.get("food_input", "")
  st.session_state["food_input"] = ""


st.text_input(
    "Що з'їв / яке тренування?",
    placeholder="Наприклад: плов з куркою 350 г, 2 яйця і хліб 60 г",
    key="food_input",
)

rem_undos = 10 - st.session_state["undo_count"]

col1, col2 = st.columns(2)
with col1:
  st.button(
      "✅ Додати в лог", use_container_width=True, on_click=handle_add_click
  )
with col2:
  undo_btn = st.button(
      f"↩️ Відмінити останній ({rem_undos}/10)",
      use_container_width=True,
      disabled=(rem_undos <= 0 or df.empty),
  )

if undo_btn and not df.empty and st.session_state["undo_count"] < 10:
  trash_row = df.tail(1).to_dict(orient="records")
  with open(TRASH_FILE, "w", encoding="utf-8") as f:
    json.dump(trash_row, f, ensure_ascii=False, indent=2, default=str)

  df = df.iloc[:-1].copy()
  save_data(df)
  st.session_state["undo_count"] += 1
  st.rerun()


# ============================================================
# АНАЛІЗ З GEMINI
# ============================================================

if "pending_input" in st.session_state:
  text = (st.session_state.pop("pending_input", "") or "").strip()
  if not text:
    st.warning("Введи текст запису.")
  else:
    prompt = f"""
        Ти харчовий трекер. Проаналізуй цей запис: "{text}"
        Поверни ТІЛЬКИ валідний JSON без markdown форматування.
        Формат:
        {{
          "type": "Їжа" або "Тренування",
          "description": "короткий опис",
          "total_kcal": число,
          "burned_kcal": число,
          "protein": число,
          "fat": число,
          "carbs": число,
          "products": [
            {{"name": "назва продукту", "kcal": число, "protein": число, "fat": число, "carbs": число}}
          ]
        }}
        Для "Їжа": products має містити кожен продукт окремо із його калоріями та БЖВ.
        Для "Тренування": total_kcal = 0, burned_kcal = значення.
        """
    try:
      response = client.models.generate_content(
          model=GEMINI_MODEL,
          contents=prompt,
          config=types.GenerateContentConfig(
              response_mime_type="application/json"
          ),
      )
      data = json.loads(response.text)
      entry_type = (
          "Тренування"
          if str(data.get("type", "")).lower().startswith("трен")
          else "Їжа"
      )
      products = normalize_products(data.get("products", []))

      if entry_type == "Їжа":
        total_kcal = (
            sum(p["kcal"] for p in products)
            if products
            else float(data.get("total_kcal", 0) or 0)
        )
        protein = (
            sum(p["protein"] for p in products)
            if products
            else float(data.get("protein", 0) or 0)
        )
        fat = (
            sum(p["fat"] for p in products)
            if products
            else float(data.get("fat", 0) or 0)
        )
        carbs = (
            sum(p["carbs"] for p in products)
            if products
            else float(data.get("carbs", 0) or 0)
        )
        burned = 0.0
      else:
        total_kcal = protein = fat = carbs = 0.0
        burned = float(data.get("burned_kcal", 0) or 0)

      now = datetime.now(LOCAL_TZ)
      new_row = {
          "Дата": now.strftime("%Y-%m-%d"),
          "Час": now.strftime("%H:%M"),
          "Опис": str(data.get("description") or text),
          "Тип": entry_type,
          "Спожито": total_kcal,
          "Спалено": burned,
          "Білки": protein,
          "Жири": fat,
          "Вуглеводи": carbs,
          "Продукти": json.dumps(products, ensure_ascii=False),
      }
      df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
      save_data(df)
      st.session_state["undo_count"] = 0
      st.success("✅ Запис додано")
      st.rerun()
    except Exception as e:
      st.error(f"Помилка обробки Gemini: {e}")


# ============================================================
# ВИБІР ДНЯ ТА ГОДИННИК
# ============================================================

today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
dates = [today]
if not df.empty:
  for d in sorted(df["Дата"].astype(str).unique(), reverse=True):
    if d not in dates:
      dates.append(d)

selected_date = st.selectbox("📅 День", dates)

st.markdown("### ⌚ Калорії з годинника")
watch_key = f"watch_{profile_prefix}_{selected_date}"

if watch_key not in st.session_state:
  st.session_state[watch_key] = float(watch_by_date.get(selected_date, 0))


def on_watch_change():
  val = float(st.session_state[watch_key])
  watch_by_date[selected_date] = val
  save_watch(watch_by_date)


st.number_input(
    "Замінити спалені калорії з годинника (ккал)",
    min_value=0.0,
    step=10.0,
    key=watch_key,
    on_change=on_watch_change,
)


# ============================================================
# РОЗРАХУНОК ТА РЕНДЕР КРУЖКА
# ============================================================

watch_now = float(st.session_state[watch_key])
consumed, burned, balance, protein, fat, carbs, exercise, watch = calculate_day(
    df, selected_date, settings, watch_now
)
target = float(settings["calories"])
current_weight = calculate_weight(df, settings, watch_by_date)

total_macros = protein + fat + carbs
if total_macros > 0:
  p_deg = protein / total_macros * 360
  f_deg = p_deg + (fat / total_macros * 360)
  c_deg = f_deg + (carbs / total_macros * 360)
  gradient = (
      f"conic-gradient(#36A2EB 0deg {p_deg}deg, #FFCE56 {p_deg}deg"
      f" {f_deg}deg, #FF6384 {f_deg}deg {c_deg}deg)"
  )
else:
  gradient = "conic-gradient(rgba(255,255,255,.14) 0deg 360deg)"

if balance >= 0:
  balance_label = f"📉 Дефіцит: {abs(balance):.0f} ккал"
  balance_class = "deficit"
else:
  balance_label = f"📈 Профіцит: {abs(balance):.0f} ккал"
  balance_class = "surplus"

donut_html = (
    f'<div class="section"><div class="donut-wrap"><div class="donut"'
    f' style="background:{gradient};"><div class="donut-hole"><div'
    f' class="balance">{balance_label}</div><div'
    f' class="kcal-main">{consumed:.0f}</div><div class="kcal-sub">з'
    f' {target:.0f} ккал</div><div class="weight-display">⚖️'
    f" {current_weight:.1f} кг</div></div></div><div class=\"macros\"><div"
    f' class="macro p">🥩 Білки {protein:.0f}/{settings["protein"]}'
    f' г</div><div class="macro f">🥑 Жири {fat:.0f}/{settings["fat"]}'
    f' г</div><div class="macro c">🍞 Вуглеводи'
    f' {carbs:.0f}/{settings["carbs"]} г</div></div></div></div>'
)
st.markdown(donut_html, unsafe_allow_html=True)

bmr_val = today_bmr(settings, selected_date)
st.markdown(
    f'<div class="status {balance_class}">'
    f"Загальний баланс за день: {abs(balance):.0f} ккал"
    f' ({("Дефіцит" if balance >= 0 else "Профіцит")})<br>'
    '<small style="font-size: 12px; opacity: 0.85;">🔥 Спалено всього:'
    f" {burned:.0f} ккал (BMR: {bmr_val:.0f} + Годинник: {watch:.0f} +"
    f" Тренування: {exercise:.0f})</small>"
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# AI ПІДКАЗКА: ЩО ДОЇСТИ ДО НОРМИ
# ============================================================

rem_kcal = max(0.0, target - consumed)
rem_p = max(0.0, float(settings["protein"]) - protein)
rem_f = max(0.0, float(settings["fat"]) - fat)
rem_c = max(0.0, float(settings["carbs"]) - carbs)

if rem_kcal > 50:
  if st.button("💡 Що доїсти до норми?", use_container_width=True):
    with st.spinner("Шукаю підходящі варіанти..."):
      prompt_advice = f"""
            Ти спортивний дієтолог. Користувачу за день залишилося добрати:
            - Калорії: {rem_kcal:.0f} ккал
            - Білки: {rem_p:.0f} г
            - Жири: {rem_f:.0f} г
            - Вуглеводи: {rem_c:.0f} г

            Запропонуй 2-3 конкретні й прості варіанти продуктів (з вказівкою назви та ваги в грамах), щоб закрити саме цей залишок БЖВ.
            Відповідь надай коротко, маркованим списком.
            """
      try:
        res_advice = client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt_advice
        )
        st.info(res_advice.text)
      except Exception as e:
        st.error(f"Помилка отримання підказки: {e}")
else:
  st.success("🎉 Денну норму калорій уже закрито!")


# ============================================================
# РЕДАКТОР ЦІЛЕЙ
# ============================================================

if st.button("⚙️ Редактор цілей", use_container_width=True):
  st.session_state["edit_mode"] = not st.session_state["edit_mode"]
  st.rerun()

if st.session_state["edit_mode"]:
  st.markdown("### ✏️ Налаштування цілей")
  e_cal = st.number_input(
      "Добова норма калорій", value=int(settings["calories"]), step=10
  )
  e_prot = st.number_input(
      "🥩 Білки, г", value=int(settings["protein"]), step=5
  )
  e_fat = st.number_input("🥑 Жири, г", value=int(settings["fat"]), step=5)
  e_carb = st.number_input(
      "🍞 Вуглеводи, г", value=int(settings["carbs"]), step=5
  )
  e_bmr = st.number_input(
      "Базові витрати BMR, ккал/добу",
      value=int(settings["bmr_daily"]),
      step=10,
  )
  e_start_weight = st.number_input(
      "Початкова вага, кг",
      value=float(settings.get("start_weight", 91.8)),
      step=0.1,
  )

  if st.button("💾 Зберегти", type="primary", use_container_width=True):
    save_settings({
        "calories": e_cal,
        "protein": e_prot,
        "fat": e_fat,
        "carbs": e_carb,
        "bmr_daily": e_bmr,
        "start_weight": e_start_weight,
    })
    st.session_state["edit_mode"] = False
    st.rerun()


# ============================================================
# ВЛОГ ЗА ДЕНЬ
# ============================================================

st.markdown(f"### 📝 Влог за {selected_date}")

if watch_now > 0:
  st.markdown(
      '<div class="log-card"><div class="log-head"><div'
      ' class="log-title">⌚ Калорії з годинника</div><div'
      f' class="log-kcal">+{watch_now:.0f} ккал</div></div></div>',
      unsafe_allow_html=True,
  )

day_df = df[df["Дата"].astype(str) == str(selected_date)].copy()

if not day_df.empty:
  day_df = day_df[(day_df["Спожито"] > 0) | (day_df["Спалено"] > 0)]
  day_df = day_df[
      ~day_df["Опис"].str.contains("годинник", case=False, na=False)
  ]

if day_df.empty and watch_now <= 0:
  st.info("За цей день інформативних записів немає.")
else:
  for idx, row in day_df.iloc[::-1].iterrows():
    entry_type = str(row["Тип"])
    icon = "🍽️" if entry_type == "Їжа" else "💪"
    kcal = float(row["Спожито"] if entry_type == "Їжа" else row["Спалено"])

    if kcal <= 0:
      continue

    desc = str(row["Опис"]).strip()
    if not desc or desc.lower() == "nan":
      desc = "Тренування" if entry_type == "Тренування" else "Прийом їжі"

    products = row_products(row)
    food_lines = ""
    if entry_type == "Їжа" and products:
      p_items = "".join([
          f'<div class="food-line"><span class="food-name">🍴'
          f' {p["name"]}</span><span class="food-cal">{p["kcal"]:.0f}'
          " ккал</span></div>"
          for p in products
          if p["kcal"] > 0 or p["name"].lower() != "nan"
      ])
      if p_items:
        food_lines = f'<div class="food-list">{p_items}</div>'

    bju = ""
    p_val, f_val, c_val = (
        float(row["Білки"]),
        float(row["Жири"]),
        float(row["Вуглеводи"]),
    )
    if entry_type == "Їжа" and (p_val > 0 or f_val > 0 or c_val > 0):
      bju = (
          '<div class="bju"><span>🥩'
          f" {p_val:.0f} г</span><span>🥑 {f_val:.0f} г</span><span>🍞"
          f" {c_val:.0f} г</span></div>"
      )

    html = (
        '<div class="log-card"><div class="log-head"><div'
        f' class="log-title">{str(row["Час"])[:5]} {icon} {desc}</div><div'
        f' class="log-kcal">{kcal:+.0f} ккал</div></div>{food_lines}{bju}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    if st.button("✏️ Редагувати", key=f"edit_{idx}", use_container_width=True):
      st.session_state["selected_edit"] = int(idx)
      st.rerun()

    if st.session_state["selected_edit"] == int(idx):
      st.markdown("**✏️ Редагування запису**")
      edit_desc = st.text_input("Опис", value=desc, key=f"desc_{idx}")
      edit_kcal = st.number_input(
          "Калорії",
          value=float(
              row["Спожито"] if entry_type == "Їжа" else row["Спалено"]
          ),
          min_value=0.0,
          step=1.0,
          key=f"kcal_{idx}",
      )

      ec1, ec2, ec3 = st.columns(3)
      with ec1:
        edit_p = st.number_input(
            "🥩 Білки",
            value=float(row["Білки"]),
            min_value=0.0,
            step=1.0,
            key=f"p_{idx}",
        )
      with ec2:
        edit_f = st.number_input(
            "🥑 Жири",
            value=float(row["Жири"]),
            min_value=0.0,
            step=1.0,
            key=f"f_{idx}",
        )
      with ec3:
        edit_c = st.number_input(
            "🍞 Вуглеводи",
            value=float(row["Вуглеводи"]),
            min_value=0.0,
            step=1.0,
            key=f"c_{idx}",
        )

      s1, s2 = st.columns(2)
      with s1:
        if st.button(
            "💾 Застосувати",
            key=f"save_edit_{idx}",
            type="primary",
            use_container_width=True,
        ):
          df.loc[idx, "Опис"] = edit_desc
          if entry_type == "Їжа":
            df.loc[idx, "Спожито"] = edit_kcal
            df.loc[idx, "Спалено"] = 0
          else:
            df.loc[idx, "Спожито"] = 0
            df.loc[idx, "Спалено"] = edit_kcal
          df.loc[idx, "Білки"] = edit_p
          df.loc[idx, "Жири"] = edit_f
          df.loc[idx, "Вуглеводи"] = edit_c
          save_data(df)
          st.session_state["selected_edit"] = None
          st.rerun()
      with s2:
        if st.button(
            "✖️ Скасувати", key=f"cancel_edit_{idx}", use_container_width=True
        ):
          st.session_state["selected_edit"] = None
          st.rerun()
