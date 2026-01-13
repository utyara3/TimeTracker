import pandas as pd

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command

from datetime import datetime

from data import messages as msg

import keyboards.inline as inline_kb

from utils import date
from utils import bot_logging as bot_log
from utils.base_utils import answer_or_edit
from utils import statistics as ustats

from database import core as db

router = Router()
logger = bot_log.get_logger(__name__)


@router.message(F.text == msg.REPLY_KB['start_kb']['statistics'])
@router.message(Command("stats"))
async def today_statistics(message: Message):
    await send_day_statistics(message, date.get_now().date())


@router.callback_query(F.data.startswith("date_statistics"))
async def date_statistics(callback: CallbackQuery):
    parts = callback.data.split(":")
    data = parts[1]
    
    # no handle date_statistics:date:edit (current day button that using in user_history)
    if len(parts) == 2:
        target_date = datetime.strptime(data,"%Y-%m-%d").date()

        await send_day_statistics(callback, target_date)

    await callback.answer()


async def send_day_statistics(
    tg_obj: Message | CallbackQuery,
    target_date: datetime.date
):
    data = await states_statistics(tg_obj.from_user.id, target_date)

    answer = data['message'] if 'status' in data \
        else msg.format_user_statistics(**data)

    keyboard = inline_kb.pagination_date_kb("date_statistics", target_date)
    keyboard.row(
        InlineKeyboardButton(
            text="📊 Посмотреть полную статистику",
            callback_data="view_full_stats"
        )
    )

    await answer_or_edit(tg_obj, answer, keyboard=keyboard.as_markup())


async def states_statistics(user_id: int, target_day: datetime.date) -> dict:
    """
    Calculate statistics for user states on a target day using pandas.
    """
    user_data = await db.get_user_states(tg_id=user_id)

    if not user_data:
        return {"status": "bad", "message": msg.FAILURE['no_states_today']}

    # Convert to DataFrame
    df = pd.DataFrame(user_data)
    
    # Convert start_time to datetime and filter by target day
    df['start_time_dt'] = pd.to_datetime(df['start_time'])
    df['start_date'] = df['start_time_dt'].dt.date
    target_day_data = df[df['start_date'] == target_day].copy()

    if target_day_data.empty:
        return {"status": "bad", "message": "📊 Нет завершенных состояний"}

    state_count = len(target_day_data)

    # Get current state data (first row, which is the most recent)
    current_state_data = target_day_data.iloc[0]
    start_time = date.to_datetime(current_state_data['start_time'])
    
    end_time_val = current_state_data['end_time']
    if pd.notna(end_time_val) and end_time_val:
        end_time = date.to_datetime(end_time_val)
    elif start_time.date() == date.get_now().date():
        end_time = date.get_now()
    else:
        end_time = datetime.combine(
            target_day,
            datetime.max.time()
        )

    delta = end_time - start_time
    delta_dict = {
        'hours': delta.seconds // 3600,
        'minutes': (delta.seconds // 60) % 60,
        'seconds': delta.seconds % 60
    }

    # Create chronology (reverse order for display)
    chronology = ' → '.join(target_day_data['state_name'].iloc[::-1].tolist())

    # Calculate durations
    def calculate_duration(row):
        return date.calculate_duration_seconds(
            start_time=row['start_time'],
            end_time=row.get('end_time') if pd.notna(row.get('end_time')) else None,
            duration_seconds=int(row['duration_seconds']) if pd.notna(row['duration_seconds']) else None
        )
    
    target_day_data['duration'] = target_day_data.apply(calculate_duration, axis=1)

    # All states statistics (including sleep)
    state_durations = target_day_data.groupby('state_name')['duration'].sum().to_dict()
    total_time = target_day_data['duration'].sum()

    if not state_durations:
        return {"status": "bad", "message": "📊 Нет завершенных состояний"}

    # Calculate percentages for all states
    states_in_percents = {
        state: [duration, round((duration / total_time) * 100, 1) if total_time > 0 else 0]
        for state, duration in state_durations.items()
    }

    # Filter out sleep for special statistics
    no_sleep_data = target_day_data[target_day_data['state_name'] != 'sleep'].copy()
    
    if not no_sleep_data.empty:
        # State totals (without sleep)
        state_durations_no_sleep = no_sleep_data.groupby('state_name')['duration'].sum().to_dict()
        # Longest and shortest total states
        longest_total_state = max(state_durations_no_sleep.items(), key=lambda x: x[1])
        shortest_total_state = min(state_durations_no_sleep.items(), key=lambda x: x[1])

        # Individual sessions (without sleep)
        individual_sessions = no_sleep_data[['state_name', 'duration']].copy()
        individual_sessions.columns = ['name', 'duration']
        
        longest_session = individual_sessions.loc[individual_sessions['duration'].idxmax()].to_dict()
        shortest_session = individual_sessions.loc[individual_sessions['duration'].idxmin()].to_dict()

        # Productivity calculation: (study + work) / chill
        productive_states = ['work', 'study']
        productivity_time = no_sleep_data[
            no_sleep_data['state_name'].isin(productive_states)
        ]['duration'].sum()
        chill_time = no_sleep_data[
            no_sleep_data['state_name'] == 'chill'
        ]['duration'].sum()
        productivity = int((productivity_time / (productivity_time + chill_time)) * 100) if chill_time > 0 else 0

        # Average session time
        average_session_time = date.format_time(
            int(individual_sessions['duration'].mean())
        )
    else:
        # If only sleep or no non-sleep states
        longest_total_state = ('—', 0)
        shortest_total_state = ('—', 0)
        longest_session = {'name': '—', 'duration': 0}
        shortest_session = {'name': '—', 'duration': 0}
        productivity = 0
        average_session_time = "0с"

    return {
        "target_date": target_day.strftime("%d/%m/%Y"),
        "current_state_name": current_state_data['state_name'],
        "current_state_tag": current_state_data['tag'],
        "delta_time": delta_dict,
        "state_count": state_count,
        "chronology": chronology,
        "states_in_precents": states_in_percents,  # All states including sleep
        "productivity": productivity,  # Without sleep
        "longest_total": {
            'name': longest_total_state[0],
            'duration': date.format_time(longest_total_state[1]) if longest_total_state[1] > 0 else "—"
        },  # Without sleep
        "shortest_total": {
            'name': shortest_total_state[0],
            'duration': date.format_time(shortest_total_state[1]) if shortest_total_state[1] > 0 else "—"
        },  # Without sleep
        "longest_session": {
            'name': longest_session['name'],
            'duration': date.format_time(longest_session['duration']) if longest_session['duration'] > 0 else "—"
        },  # Without sleep
        "shortest_session": {
            'name': shortest_session['name'],
            'duration': date.format_time(shortest_session['duration']) if shortest_session['duration'] > 0 else "—"
        },  # Without sleep
        "average_session": average_session_time  # Without sleep
    }


@router.message(Command("predict"))
async def predict_user_next_state(message: Message) -> None:
    states: list = await db.get_user_states(tg_obj=message)
    
    month_days = set(
        [date.to_datetime(state['start_time']).date().day for state in states]
    )
    
    if len(month_days) <= 7:
        await message.answer(msg.FAILURE['few_days'])
        return

    all_sessions = states.copy()
    
    now_str = date.get_now().strftime("%Y-%m-%d %H:%M:%S")
    for session in all_sessions:
        if session['end_time'] is None:
            session['end_time'] = now_str
    
    df = pd.DataFrame(all_sessions)
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    df = df.sort_values('start_time')
    
    df['prev_state'] = df['state_name'].shift(1)
    df = df[df['state_name'] != df['prev_state']].copy()
    
    df['next_state'] = df['state_name'].shift(-1)
    df = df.dropna(subset=['next_state'])
    
    df['weekday'] = df['start_time'].dt.weekday
    df['time_bin'] = df['start_time'].dt.hour // 4
    
    current_session = all_sessions[0]  
    current_state = current_session['state_name']
    current_start = pd.to_datetime(current_session['start_time'])
    today = current_start.weekday()
    current_time_bin = current_start.hour // 4
    transitions_by_day = df.groupby(['weekday', 'time_bin']).apply(ustats.build_transition_matrix, include_groups=False)
    try:
        # Пробуем предсказать по паттернам недели и дневным бинам
        next_state_probabilities = transitions_by_day.loc[
            (today, current_time_bin, current_state)
        ]
        predict_by = "День недели и время начала сессии"
    except KeyError:
        try:
            # У пользователя недостаточное разнообразие сессий, пробуем предсказать только по паттернам недели
            transitions_by_weekday = df.groupby('weekday').apply(ustats.build_transition_matrix, include_groups=False)
            next_state_probabilities = transitions_by_weekday.loc[(today, current_state)]
            
            predict_by = "День недели"

        except KeyError:
            try:
                # У пользователя еще меньше данных, в теории этот блок не должен выполниться, но на всякий случай лучше тоже обработать. Смотрим глобально по состоянию
                global_transitions = ustats.build_transition_matrix(df)
                next_state_probabilities = global_transitions.loc[current_state]
                
                predict_by = "Глобальные переходы состояний"

            except KeyError:
                await message.answer("У вас слишком мало состояний, попробуйте позже...")
                return


    sorted_probs = next_state_probabilities.sort_values(ascending=False) 
    next_state = [(sorted_probs.index[0], round(sorted_probs.iloc[0]*100, 2))]

    if len(sorted_probs) > 1:
        for prob in range(1, len(sorted_probs)-1):
            if sorted_probs.iloc[prob] > 0.01:
                next_state.append((sorted_probs.index[prob], round(sorted_probs.iloc[prob]*100, 2)))

    await message.answer(msg.format_predict_next_state(next_state, predict_by))

