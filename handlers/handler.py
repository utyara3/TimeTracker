from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from datetime import datetime
from collections import Counter

import utils.date
from data import messages as msg
import keyboards.reply as reply_kb
import keyboards.inline as inline_kb

from utils import date

from database import core as db

router = Router()


@router.message(Command('start'))
async def start_cmd(message: Message):
    if not await db.is_user_in_database(message):
        await db.add_user_to_database(message)

    await message.answer(
        msg.COMMON['start_cmd'],
        reply_markup=reply_kb.start_kb().as_markup(resize_keyboard=True)
    )


@router.message(Command('cancel'))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(msg.COMMON['cancel_cmd'])


@router.message(Command('help'))
async def help_cmd(message: Message):
    await message.answer(msg.COMMON['help_cmd'])


@router.message(Command("my_tags"))
async def user_tags(message: Message) -> None:
    tags = await db.get_user_tags(message=message)

    if len(tags) == 0:
        await message.answer(msg.FAILURE['have_not_tags'])
        return

    cnt = Counter(tags)
    sorted_count = sorted(cnt.items(), key=lambda item: item[1], reverse=True)

    text = f"<b>Топ {min(len(cnt.keys()), 20)} ваших самых часто повторяющихся тегов:</b>\n\n"
    num = 0
    for tag, count in sorted_count:
        if num == 20:
            break

        text += f"{num+1}.  <code>{tag}</code> - {count}\n"
        num += 1

    await message.answer(text)


async def send_rate_message(message: Message, time_session_id: int) -> None:
    kb = inline_kb.rate_keyboard(time_session_id)

    await message.answer(msg.COMMON['rate_state'], reply_markup=kb.as_markup())


@router.message(Command(*msg.DEFAULT_STATES.keys()))
async def change_state_cmd(message: Message):
    text = message.text
    parted = text.split()
    tag = ''

    if len(parted) > 1:
        tag = ' '.join(parted[1:])

    selected_state = parted[0]
    if selected_state.startswith('/'):
        selected_state = selected_state[1:]

    switch = await db.switch_state(message=message, new_state=selected_state, tag=tag)
    prev_state = switch['previous_state']
    start_time = switch['start_time']
    new_state = switch['new_state']
    prev_tag = switch['prev_tag']
    new_tag = switch['new_tag']
    time_session_id = switch['time_session_id']
    if time_session_id is not None:
        time_session_id = int(time_session_id)

    if start_time is None:
        delta_time_str = "None"
    else:
        delta_time = datetime.now() - datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        hours = delta_time.seconds // 3600
        minutes = (delta_time.seconds // 60) % 60
        seconds = delta_time.seconds % 60

        delta_time_str = ''
        if hours >= 1:
            delta_time_str += f'{hours}ч '
        if minutes >= 1:
            delta_time_str += f'{minutes}м '

        delta_time_str += f'{seconds}с'

    if switch:
        await message.answer(
            msg.format_switch_state_message(
                prev_state=prev_state,
                new_state=new_state,
                prev_tag=prev_tag,
                new_tag=new_tag,
                delta_time=delta_time_str
            )
        )
        if prev_state is not None:
            await send_rate_message(message, time_session_id)
    else:
        await message.answer(msg.FAILURE['state_change'])


@router.callback_query(F.data.startswith("rate_time_session"))
async def rate_time_session(callback_query: CallbackQuery):
    data = callback_query.data
    time_session, mood = map(int, data.split(":")[1:])

    await db.rate_state(time_session_id=time_session, mood=mood)

    await callback_query.message.edit_text(msg.SUCCESS['state_rated'])


@router.message(F.text == msg.REPLY_KB['start_kb']['set_state'])
@router.message(Command("set_state"))
async def states_message(message: Message) -> None:
    await message.answer(msg.COMMON['states_message'])


@router.message(F.text == msg.REPLY_KB['start_kb']['history'])
@router.message(Command("history"))
async def states_history(message: Message) -> None:
    states = await db.get_user_states(message=message, limit=5)
    if not states:
        await message.answer(msg.FAILURE['no_states_today'])

    today = datetime.today().date()

    states_today = []
    for state in states:
        start_day = date.to_datetime(state['start_time']).date()
        if start_day == today:
            states_today.append(state)

    if not states_today:
        await message.answer(msg.FAILURE['no_states_today'])
        return

    await message.answer(msg.format_states_history(states=states_today))


@router.message(F.text == msg.REPLY_KB['start_kb']['statistics'])
@router.message(Command("stats"))
async def states_statistics(message: Message) -> None:
    user_data = await db.get_user_states(message=message)

    if not user_data:
        await message.answer(msg.FAILURE['no_states_today'])

    # TODAY STATISTICS
    today = datetime.today().date()
    data_today = []
    for state in user_data:
        start_day = date.to_datetime(state['start_time']).date()
        if start_day == today:
            data_today.append(state)

    if not data_today:
        await message.answer("📊 За сегодня еще нет завершенных состояний")
        return

    state_count_today = len(data_today)

    current_state_data = data_today[0]
    now = datetime.now()

    delta_today = now - date.to_datetime(current_state_data['start_time'])
    delta_today_dict = {
        'hours': delta_today.seconds // 3600,
        'minutes': (delta_today.seconds // 60) % 60,
        'seconds': delta_today.seconds % 60
    }

    chronology = ' → '.join([state['state_name'] for state in data_today])

    total_time_today = 0
    state_durations = {}
    individual_sessions = []

    for state in data_today:
        state_name = state['state_name']

        if state['end_time'] is None:
            continue

        duration = int(state['duration_seconds'])

        if state_name in state_durations:
            state_durations[state_name] += duration
        else:
            state_durations[state_name] = duration

        total_time_today += duration

        individual_sessions.append({
            'name': state_name,
            'duration': duration
        })

    if not state_durations:
        await message.answer("📊 Нет завершенных состояний для статистики")
        return

    longest_total_state = max(state_durations.items(), key=lambda x: x[1])
    shortest_total_state = min(state_durations.items(), key=lambda x: x[1])

    longest_session = max(individual_sessions, key=lambda x: x['duration'])
    shortest_session = min(individual_sessions, key=lambda x: x['duration'])

    sorted_states = sorted(state_durations.items(), key=lambda x: x[1], reverse=True)
    top3_time = sum(duration for _, duration in sorted_states[:3])
    focus_percent = int((top3_time / total_time_today) * 100) if total_time_today > 0 else 0

    productive_states = ['work', 'study']
    productivity_time = sum(
        duration for state, duration in state_durations.items()
        if state in productive_states
    )
    productivity = int((productivity_time / total_time_today) * 100) if total_time_today > 0 else 0

    states_in_percents = {}
    for state, duration in state_durations.items():
        percent = (duration / total_time_today) * 100 if total_time_today > 0 else 0
        states_in_percents[state] = [duration, round(percent, 1)]

    if individual_sessions:
        average_session_time = date.format_time(
            int(
                sum(
                    session['duration'] for session in individual_sessions
                ) / len(state_durations)
            )
        )
    else:
        average_session_time = "0с"

    await message.answer(msg.format_user_statistics(
        current_state_name=current_state_data['state_name'],
        current_state_tag=current_state_data['tag'],
        delta_today_dict=delta_today_dict,
        state_count_today=state_count_today,
        chronology=chronology,
        states_in_precents=states_in_percents,
        productivity=productivity,
        focus=focus_percent,
        longest_total={
            'name': longest_total_state[0],
            'duration': date.format_time(longest_total_state[1])
        },
        shortest_total={
            'name': shortest_total_state[0],
            'duration': date.format_time(shortest_total_state[1])
        },
        longest_session={
            'name': longest_session['name'],
            'duration': date.format_time(longest_session['duration'])
        },
        shortest_session={
            'name': shortest_session['name'],
            'duration': date.format_time(shortest_session['duration'])
        },
        average_session=average_session_time
    ))


    # GENERAL STATISTICS
    # coming soon...

    #await message.answer(msg.format_user_statistics())
