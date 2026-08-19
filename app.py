import json
import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

EXCEL_FILE = 'fitness_tracker.xlsx'
DAILY_CALORIE_TARGET = (
    2050  # Цільова норма калорій на день для схуднення (при вазі 89 кг)
)

DAYS_UA = {
    'Monday': 'Понеділок',
    'Tuesday': 'Вівторок',
    'Wednesday': 'Середа',
    'Thursday': 'Четвер',
    'Friday': 'П’ятниця',
    'Saturday': 'Субота',
    'Sunday': 'Неділя',
}

st.set_page_config(page_title='Облік фітнесу з ШІ', layout='wide')
st.title('🏋️ Облік фітнесу з ШІ')

api_key = st.secrets.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')

if not api_key:
  st.error(
      '⚠️ Не знайдено GEMINI_API_KEY у Secrets Streamlit! Додайте ключ у'
      ' налаштуваннях додатка (Manage app -> Settings -> Secrets).'
  )
  st.stop()

client = genai.Client(api_key=api_key)

with st.container(border=True):
  st.markdown('### 📥 Введіть дані у довільній формі')
  user_input = st.text_input(
      'Рядок введення:',
      placeholder=(
          "Наприклад: з'їв 30г чорного хліба з 10г індичої ковбаси, пройшов 8500"
          ' кроків, спалено 450 ккал'
      ),
      label_visibility='collapsed',
  )
  submit_btn = st.button('Записати', type='primary', use_container_width=True)

if submit_btn and user_input:
  prompt = f"""
    Проаналізуй наступний текст українською мовою та вилучи дані про фізичну активність і спожиту їжу:
    "{user_input}"

    Поверни відповідь СУВОРO у форматі JSON із такими полями:
    {{
        "steps": <ціле число кроків, якщо вказано, інакше null>,
        "kcal_burned": <число спалених ккал/калорій за активність, якщо вказано, інакше null>,
        "total_consumed_kcal": <загальна калорійність всієї спожитої їжі (ккал)>,
        "total_protein": <загальна кількість білків у грамах>,
        "total_fat": <загальна кількість жирів у грамах>,
        "total_carbs": <загальна кількість вуглеводів у грамах>
    }}

    Правила розрахунку:
    - Враховуй точну калорійність і БЖВ для конкретного типу продукту (наприклад, чорний/білий хліб, індича/свиняча ковбаса, куряче/свиняче м'ясо).
    - Якщо вагу вказано приблизно ("шматочок", "порція"), зроби максимально реалістичну оцінку ваги та БЖВ.
    - Якщо їжа не згадується, поверни 0 для всіх показників харчування.
    - Відповідь має бути ЛИШЕ чистим JSON-об'єктом без markdown чи додаткового тексту.
    """

  try:
    with st.spinner('Штучний інтелект аналізує запис...'):
      response = client.models.generate_content(
          model='gemini-3.6-flash',
          contents=prompt,
          config=types.GenerateContentConfig(
              response_mime_type='application/json'
          ),
      )

      data = json.loads(response.text)

      input_steps = data.get('steps')
      input_kcal_burned = data.get('kcal_burned')
      add_kcal = float(data.get('total_consumed_kcal', 0.0))
      add_p = float(data.get('total_protein', 0.0))
      add_f = float(data.get('total_fat', 0.0))
      add_c = float(data.get('total_carbs', 0.0))

    now = pd.Timestamp.today()
    date_str = now.strftime('%Y-%m-%d')
    day_name_ua = DAYS_UA.get(now.strftime('%A'), '')

    if os.path.exists(EXCEL_FILE):
      df = pd.read_excel(EXCEL_FILE)
    else:
      df = pd.DataFrame(
          columns=[
              'Дата',
              'День тижня',
              'Кроки',
              'Спалено (ккал)',
              'Спожито (ккал)',
              'Білки (г)',
              'Жири (г)',
              'Вуглеводи (г)',
              'Баланс (ккал)',
          ]
      )

    numeric_cols = [
        'Кроки',
        'Спалено (ккал)',
        'Спожито (ккал)',
        'Білки (г)',
        'Жири (г)',
        'Вуглеводи (г)',
        'Баланс (ккал)',
    ]
    for col in numeric_cols:
      if col in df.columns:
        df[col] = df[col].astype(float)

    if date_str in df['Дата'].astype(str).values:
      idx = df[df['Дата'].astype(str) == date_str].index[0]

      if input_steps is not None:
        df.loc[idx, 'Кроки'] = float(input_steps)
      if input_kcal_burned is not None:
        df.loc[idx, 'Спалено (ккал)'] = float(input_kcal_burned)

      df.loc[idx, 'Спожито (ккал)'] = round(
          df.loc[idx, 'Спожито (ккал)'] + add_kcal, 1
      )
      df.loc[idx, 'Білки (г)'] = round(df.loc[idx, 'Білки (г)'] + add_p, 1)
      df.loc[idx, 'Жири (г)'] = round(df.loc[idx, 'Жири (г)'] + add_f, 1)
      df.loc[idx, 'Вуглеводи (г)'] = round(df.loc[idx, 'Вуглеводи (г)'] + add_c, 1)
      df.loc[idx, 'Баланс (ккал)'] = round(
          df.loc[idx, 'Спожито (ккал)'] - df.loc[idx, 'Спалено (ккал)'], 1
      )
    else:
      new_row = pd.DataFrame({
          'Дата': [date_str],
          'День тижня': [day_name_ua],
          'Кроки': [float(input_steps) if input_steps is not None else 0.0],
          'Спалено (ккал)': [
              float(input_kcal_burned)
              if input_kcal_burned is not None
              else 0.0
          ],
          'Спожито (ккал)': [round(add_kcal, 1)],
          'Білки (г)': [round(add_p, 1)],
          'Жири (г)': [round(add_f, 1)],
          'Вуглеводи (г)': [round(add_c, 1)],
          'Баланс (ккал)': [
              round(
                  add_kcal
                  - (
                      float(input_kcal_burned)
                      if input_kcal_burned is not None
                      else 0.0
                  ),
                  1,
              )
          ],
      })
      df = pd.concat([df, new_row], ignore_index=True)

    df = df.sort_values(by='Дата', ascending=False)
    df.to_excel(EXCEL_FILE, index=False)
    st.success('✅ Дані успішно розпізнано та додано!')

  except Exception as e:
    st.error(f'Помилка обробки: {e}')

if os.path.exists(EXCEL_FILE):
  df_current = pd.read_excel(EXCEL_FILE)

  today_str = pd.Timestamp.today().strftime('%Y-%m-%d')
  today_row = df_current[df_current['Дата'].astype(str) == today_str]

  st.divider()
  st.subheader('🎯 Статус схуднення за сьогодні')

  if not today_row.empty:
    consumed = today_row.iloc[0]['Спожито (ккал)']
    diff_from_target = consumed - DAILY_CALORIE_TARGET

    col1, col2, col3 = st.columns(3)
    col1.metric('Спожито ккал', f'{consumed}')
    col2.metric('Ціль для схуднення', f'{DAILY_CALORIE_TARGET} ккал')

    if consumed <= DAILY_CALORIE_TARGET:
      col3.metric(
          'Статус',
          '📉 У дефіциті',
          delta=f'{diff_from_target} ккал',
          delta_color='inverse',
      )
      st.success(
          '🔥 Чудово! Ви в межах норми схуднення (дефіцит калорій дотримується).'
      )
    else:
      col3.metric(
          'Статус',
          '📈 Перевищено норму',
          delta=f'+{diff_from_target} ккал',
          delta_color='normal',
      )
      st.warning(
          '⚠️ Ви перевищили ціль для схуднення. Спробуйте вписатися в ліміт'
          f' {DAILY_CALORIE_TARGET} ккал.'
      )
  else:
    st.info('Сьогодні ще немає записів. Введіть щось вище, щоб побачити статус!')

  st.subheader('📅 Таблиця обліку')
  st.dataframe(df_current, use_container_width=True)

  if not df_current.empty:
    with st.expander('🗑️ Видалити конкретний день'):
      dates_list = df_current['Дата'].astype(str).tolist()
      selected_date = st.selectbox('Оберіть дату для видалення:', dates_list)
      if st.button('Видалити обраний день', type='secondary'):
        df_updated = df_current[df_current['Дата'].astype(str) != selected_date]
        df_updated.to_excel(EXCEL_FILE, index=False)
        st.success(f'🗑️ Запис за {selected_date} видалено!')
        st.rerun()
