from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from datetime import datetime
from collections import Counter

from data import messages as msg
import keyboards.reply as reply_kb
import keyboards.inline as inline_kb

from utils import date
from utils import bot_logging as bot_log
from database import core as db

router = Router()
logger = bot_log.get_logger(__name__)


@router.message(Command('start'))
async def start_cmd(message: Message):
    if not await db.is_user_in_database(message):
        await db.add_user_to_database(message)
        logger.info(f"Пользователь "
                    f"{message.from_user.full_name} "
                    f"({message.from_user.id}) был добавлен в базу данных")

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
        return

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



async def states_statistics(user_id: int, target_day: datetime.date) -> dict:
    user_data = await db.get_user_states(tg_id=user_id)

    if not user_data:
        return {"status": "bad", "message": msg.FAILURE['no_states_today']}

    target_day_data = []
    for state in user_data:
        start_day = date.to_datetime(state['start_time']).date()
        if start_day == target_day:
            target_day_data.append(state)

    if not target_day_data:
        return {"status": "bad", "message": "📊 Нет завершенных состояний"}

    state_count = len(target_day_data)

    current_state_data = target_day_data[0]
    start_time = date.to_datetime(current_state_data['start_time'])
    if current_state_data.get('end_time'):
        end_time = date.to_datetime(current_state_data['end_time'])
    elif start_time.date() == datetime.now().date():
        end_time = datetime.now()
    else:
        end_time = datetime.combine(target_day, datetime.max.time())

    delta = end_time - start_time
    delta_dict = {
        'hours': delta.seconds // 3600,
        'minutes': (delta.seconds // 60) % 60,
        'seconds': delta.seconds % 60
    }

    chronology = ' → '.join([state['state_name'] for state in target_day_data[::-1]])

    total_time = 0
    state_durations = {}
    individual_sessions = []

    for state in target_day_data:
        state_name = state['state_name']

        if state['end_time'] is None:
            continue

        duration = int(state['duration_seconds'])

        if state_name in state_durations:
            state_durations[state_name] += duration
        else:
            state_durations[state_name] = duration

        total_time += duration

        individual_sessions.append({
            'name': state_name,
            'duration': duration
        })

    if not state_durations:
        return {"status": "bad", "message": "📊 Нет завершенных состояний"}

    longest_total_state = max(state_durations.items(), key=lambda x: x[1])
    shortest_total_state = min(state_durations.items(), key=lambda x: x[1])

    longest_session = max(individual_sessions, key=lambda x: x['duration'])
    shortest_session = min(individual_sessions, key=lambda x: x['duration'])

    productive_states = ['work', 'study']
    productivity_time = sum(
        duration for state, duration in state_durations.items()
        if state in productive_states
    )
    productivity = int((productivity_time / total_time) * 100) if total_time > 0 else 0

    states_in_percents = {}
    for state, duration in state_durations.items():
        percent = (duration / total_time) * 100 if total_time > 0 else 0
        states_in_percents[state] = [duration, round(percent, 1)]

    if individual_sessions:
        average_session_time = date.format_time(
            int(
                sum(
                    session['duration'] for session in individual_sessions
                ) / len(individual_sessions)
            )
        )
    else:
        average_session_time = "0с"

    return {
        "target_date": target_day.strftime("%d/%m/%Y"),
        "current_state_name": current_state_data['state_name'],
        "current_state_tag": current_state_data['tag'],
        "delta_time": delta_dict,
        "state_count": state_count,
        "chronology": chronology,
        "states_in_precents": states_in_percents,
        "productivity": productivity,
        "longest_total": {
            'name': longest_total_state[0],
            'duration': date.format_time(longest_total_state[1])
        },
        "shortest_total": {
            'name': shortest_total_state[0],
            'duration': date.format_time(shortest_total_state[1])
        },
        "longest_session": {
            'name': longest_session['name'],
            'duration': date.format_time(longest_session['duration'])
        },
        "shortest_session": {
            'name': shortest_session['name'],
            'duration': date.format_time(shortest_session['duration'])
        },
        "average_session": average_session_time
    }


async def send_day_statistics(
    tg_obj: Message | CallbackQuery,
    target_date: datetime.date
):
    data = await states_statistics(tg_obj.from_user.id, target_date)

    answer = data['message'] if 'status' in data \
        else msg.format_user_statistics(**data)

    keyboard = inline_kb.pagination_date_statistics(target_date).as_markup()

    if isinstance(tg_obj, Message):
        await tg_obj.answer(
            answer,
            reply_markup=keyboard
        )

    else:
        await tg_obj.message.edit_text(
            answer,
            reply_markup=keyboard
        )


@router.message(F.text == msg.REPLY_KB['start_kb']['statistics'])
@router.message(Command("stats"))
async def today_statistics(message: Message):
    await send_day_statistics(message, datetime.today().date())


@router.callback_query(F.data.startswith("date_statistics"))
async def date_statistics(callback: CallbackQuery):
    data = callback.data.split(":")[1]
    if data != "today":
        target_date = datetime.strptime(data,"%Y-%m-%d").date()

        await send_day_statistics(callback, target_date)

    await callback.answer()
