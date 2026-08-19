import json
import os
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

EXCEL_FILE = 'fitness_tracker.xlsx'

# Базова цільова норма калорій для схуднення (при вазі 89 кг)
BASE_CALORIE_TARGET = 2050

TARGETS = {'kcal': BASE_CALORIE_TARGET, 'protein': 170, 'fat': 75, 'carbs': 190}

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
          "Наприклад: з'їв 30г чорного хліба, пройшов 8500 кроків, спалено 450"
          ' ккал'
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
        "food_description": <короткий опис з'їденої їжі рядком, наприклад "хліб чорний, ковбаса", якщо їжі немає - пустий рядок "">,
        "steps": <ціле число кроків з тексту, якщо вказано, інакше null>,
        "kcal_burned": <число спалених ккал/калорій за активність з тексту, якщо вказано, інакше null>,
        "total_consumed_kcal": <загальна калорійність всієї спожитої їжі (ккал)>,
        "total_protein": <загальна кількість білків у грамах>,
        "total_fat": <загальна кількість жирів у грамах>,
        "total_carbs": <загальна кількість вуглеводів у грамах>
    }}

    Правила розрахунку:
    - Чітко шукай в тексті спалені калорії (наприклад, "спалено 450 ккал", "активність 300 ккал") і запиши їх у kcal_burned.
    - Якщо їжа не згадується, поверни 0 для калорій/БЖВ та порожній рядок для food_description.
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

      food_desc = data.get('food_description', '')
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
              'Раціон',
              'Кроки',
              'Спалено (ккал)',
              'Спожито (ккал)',
              'Білки (г)',
              'Жири (г)',
              'Вуглеводи (г)',
              'Баланс (ккал)',
          ]
      )

    if 'Раціон' not in df.columns:
      df.insert(2, 'Раціон', '')

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

      if food_desc:
        existing_food = str(df.loc[idx, 'Раціон'])
        if existing_food and existing_food != 'nan':
          df.loc[idx, 'Раціон'] = existing_food + '; ' + food_desc
        else:
          df.loc[idx, 'Раціон'] = food_desc

      if input_steps is not None and float(input_steps) > 0:
        df.loc[idx, 'Кроки'] = float(input_steps)

      if input_kcal_burned is not None and float(input_kcal_burned) > 0:
        current_burned = (
            float(df.loc[idx, 'Спалено (ккал)'])
            if pd.notna(df.loc[idx, 'Спалено (ккал)'])
            else 0.0
        )
        df.loc[idx, 'Спалено (ккал)'] = current_burned + float(input_kcal_burned)

      df.loc[idx, 'Спожито (ккал)'] = round(
          df.loc[idx, 'Спожито (ккал)'] + add_kcal, 1
      )
      df.loc[idx, 'Білки (г)'] = round(df.loc[idx, 'Білки (г)'] + add_p, 1)
      df.loc[idx, 'Жири (г)'] = round(df.loc[idx, 'Жири (г)'] + add_f, 1)
      df.loc[idx, 'Вуглеводи (г)'] = round(df.loc[idx, 'Вуглеводи (г)'] + add_c, 1)

      total_burned = float(df.loc[idx, 'Спалено (ккал)'])
      total_consumed = float(df.loc[idx, 'Спожито (ккал)'])
      df.loc[idx, 'Баланс (ккал)'] = round(total_consumed - total_burned, 1)
    else:
      burned_val = (
          float(input_kcal_burned) if input_kcal_burned is not None else 0.0
      )
      steps_val = float(input_steps) if input_steps is not None else 0.0
      new_row = pd.DataFrame({
          'Дата': [date_str],
          'День тижня': [day_name_ua],
          'Раціон': [food_desc],
          'Кроки': [steps_val],
          'Спалено (ккал)': [burned_val],
          'Спожито (ккал)': [round(add_kcal, 1)],
          'Білки (г)': [round(add_p, 1)],
          'Жири (г)': [round(add_f, 1)],
          'Вуглеводи (г)': [round(add_c, 1)],
          'Баланс (ккал)': [round(add_kcal - burned_val, 1)],
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
  st.subheader('🎯 Прогрес і БЖВ за сьогодні')

  if not today_row.empty:
    r = today_row.iloc[0]
    consumed = float(r['Спожито (ккал)'])
    burned = float(r['Спалено (ккал)'])
    p_val = float(r['Білки (г)'])
    f_val = float(r['Жири (г)'])
    c_val = float(r['Вуглеводи (г)'])

    # Головна формула: Залишок = (Ціль 2050 + Спалено з годинника) - Спожито з їжі
    remaining_kcal = (TARGETS['kcal'] + burned) - consumed

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        'Залишок (ккал)',
        f'{int(remaining_kcal)}',
        help='Ціль (2050) + Спалено - Спожито',
        delta=f'Спожито: {consumed} | Спалено: {burned}',
    )
    col2.metric(
        'Білки',
        f'{p_val} г',
        delta=f'{p_val - TARGETS["protein"]:.1f} г',
    )
    col3.metric(
        'Жири',
        f'{f_val} г',
        delta=f'{f_val - TARGETS["fat"]:.1f} г',
    )
    col4.metric(
        'Вуглеводи',
        f'{c_val} г',
        delta=f'{c_val - TARGETS["carbs"]:.1f} г',
    )

    if remaining_kcal >= 0:
      st.success(
          f'✅ Ви в дефіциті. Можете спожити ще {int(remaining_kcal)} ккал.'
      )
    else:
      st.error(f'❌ Ви перевищили ліміт на {abs(int(remaining_kcal))} ккал!')
  else:
    st.info('Сьогодні ще немає записів. Введіть щось вище!')

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
