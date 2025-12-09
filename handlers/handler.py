import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from datetime import datetime, timedelta
from collections import Counter

from data import messages as msg
import keyboards.reply as reply_kb
import keyboards.inline as inline_kb

from utils import date
from utils import bot_logging as bot_log
from database import core as db

router = Router()
logger = bot_log.get_logger(__name__)


async def answer_or_edit(
    tg_obj: Message | CallbackQuery,
    text: str,
    keyboard = None
) -> None:
    if isinstance(tg_obj, Message):
        if keyboard:
            await tg_obj.answer(
                text,
                reply_markup=keyboard
            )
        else:
            await tg_obj.answer(text)
    else:
        if keyboard:
            await tg_obj.message.edit_text(
                text,
                reply_markup=keyboard
            )
        else:
            await tg_obj.message.edit_text(text)


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


@router.message(Command("fix"))
async def fix_cmd(message: Message, command: CommandObject) -> None:
    args = command.args

    if not args:
        await message.answer(msg.FAILURE['wrong_args'])
        logger.info("fix no args")
        return

    parts = args.split()

    time_parts = []
    state_and_tag = []

    for part in parts:
        if re.search(r'\d+\s*[hmчм]', part):
            time_parts.append(part)
        else:
            state_and_tag = parts[len(time_parts):]
            break

    if not time_parts or not state_and_tag:
        await message.answer(msg.FAILURE['wrong_args'])
        return

    states = await db.get_user_states(message=message, limit=2)
    if not states or len(states) < 1:
        await message.answer(msg.FAILURE['no_states_today'])
        return

    current_state = states[0]
    state_start_time = date.to_datetime(current_state['start_time'])

    dur_sec_args = date.duration_seconds_from_string(' '.join(time_parts))
    total_duration = (date.get_now() - state_start_time).total_seconds()
    if dur_sec_args > total_duration:
        await message.answer(msg.FAILURE['fix_wrong_time'])
        return

    first_state_duration_seconds = int(total_duration - timedelta(seconds=dur_sec_args).total_seconds())
    first_state_end_time = state_start_time + timedelta(seconds=first_state_duration_seconds)

    new_state = state_and_tag[0]
    new_tag = ' '.join(state_and_tag[1:])

    fix_state = await db.fix_states(
        message=message,
        first_state_end_time=first_state_end_time,
        first_state_duration_seconds=first_state_duration_seconds,
        new_state=new_state,
        new_tag=new_tag
    )

    if not fix_state:
        await message.answer(msg.FAILURE['state_change'])
        return

    await message.answer(
        msg.format_fix_cmd(
            state_name=current_state['state_name'],
            state_start_time=date.format_without_date(
                date.to_datetime(current_state['start_time'])
            ),
            new_state=new_state,
            prev_state_end_time=date.format_without_date(first_state_end_time)
        )
    )

    await send_rate_message(message, int(current_state['id']))


async def send_rate_message(message: Message, time_session_id: int) -> None:
    kb = inline_kb.rate_keyboard(time_session_id)

    await message.answer(msg.COMMON['rate_state'], reply_markup=kb.as_markup())


@router.message(Command(*msg.DEFAULT_STATES.keys()))
async def change_state_cmd(message: Message):
    text = message.text.lower()
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
        delta_time = date.get_now() - datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
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

        logger.info(f"Пользователь {message.from_user.full_name} ({message.from_user.id}) "
                    f"изменил состояние с {prev_state} ({prev_tag}) на {new_state} ({new_tag})")
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
async def states_history_today(message: Message) -> None:
    today = date.get_now().date()

    await send_day_history(message, today)


async def send_day_history(
    tg_obj: Message | CallbackQuery,
    target_day: datetime.date
) -> None:
    states = await db.get_user_states(tg_obj=tg_obj)

    keyboard = inline_kb.pagination_date_kb("date_history", target_day).as_markup()

    if not states:
        await answer_or_edit(tg_obj, msg.FAILURE['no_states_today'], keyboard=keyboard)
        return

    states_date = []
    for state in states:
        start_day = date.to_datetime(state['start_time']).date()
        if start_day == target_day:
            states_date.append(state)

    if not states_date:
        await answer_or_edit(tg_obj, msg.FAILURE['no_states_today'], keyboard=keyboard)
        return

    await answer_or_edit(
        tg_obj,
        msg.format_states_history(states=states_date),
        keyboard=keyboard
    )


@router.callback_query(F.data.startswith("date_history"))
async def date_statistics(callback: CallbackQuery):
    data = callback.data.split(":")[1]
    if data != "today":
        target_date = datetime.strptime(data,"%Y-%m-%d").date()

        await send_day_history(callback, target_date)

    await callback.answer()


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

    chronology = ' → '.join([state['state_name'] for state in target_day_data[::-1]])

    total_time = 0
    state_durations = {}
    individual_sessions = []

    # Отдельные переменные для данных без sleep
    state_durations_no_sleep = {}
    individual_sessions_no_sleep = []
    total_time_no_sleep = 0

    for state in target_day_data:
        state_name = state['state_name']

        if state['end_time'] is None:
            continue

        duration = int(state['duration_seconds'])

        # Все состояния (включая sleep) для общей статистики
        if state_name in state_durations:
            state_durations[state_name] += duration
        else:
            state_durations[state_name] = duration

        total_time += duration

        individual_sessions.append({
            'name': state_name,
            'duration': duration
        })

        # Только не-sleep состояния для специальной статистики
        if state_name != 'sleep':
            if state_name in state_durations_no_sleep:
                state_durations_no_sleep[state_name] += duration
            else:
                state_durations_no_sleep[state_name] = duration

            total_time_no_sleep += duration

            individual_sessions_no_sleep.append({
                'name': state_name,
                'duration': duration
            })

    if not state_durations:
        return {"status": "bad", "message": "📊 Нет завершенных состояний"}

    # Расчеты для всех состояний (включая sleep)
    states_in_percents = {}
    for state, duration in state_durations.items():
        percent = (duration / total_time) * 100 if total_time > 0 else 0
        states_in_percents[state] = [duration, round(percent, 1)]

    # Расчеты только для не-sleep состояний
    if state_durations_no_sleep:
        longest_total_state = max(state_durations_no_sleep.items(), key=lambda x: x[1])
        shortest_total_state = min(state_durations_no_sleep.items(), key=lambda x: x[1])

        longest_session = max(individual_sessions_no_sleep, key=lambda x: x['duration'])
        shortest_session = min(individual_sessions_no_sleep, key=lambda x: x['duration'])

        productive_states = ['work', 'study']
        productivity_time = sum(
            duration for state, duration in state_durations_no_sleep.items()
            if state in productive_states
        )
        productivity = int((productivity_time / total_time_no_sleep) * 100) if total_time_no_sleep > 0 else 0

        average_session_time = date.format_time(
            int(
                sum(session['duration'] for session in individual_sessions_no_sleep)
                / len(individual_sessions_no_sleep)
            )
        )
    else:
        # Если есть только sleep или нет завершенных не-sleep состояний
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
        "states_in_precents": states_in_percents,  # Все состояния включая sleep
        "productivity": productivity,  # Без учета sleep
        "longest_total": {
            'name': longest_total_state[0],
            'duration': date.format_time(longest_total_state[1]) if longest_total_state[1] > 0 else "—"
        },  # Без учета sleep
        "shortest_total": {
            'name': shortest_total_state[0],
            'duration': date.format_time(shortest_total_state[1]) if shortest_total_state[1] > 0 else "—"
        },  # Без учета sleep
        "longest_session": {
            'name': longest_session['name'],
            'duration': date.format_time(longest_session['duration']) if longest_session['duration'] > 0 else "—"
        },  # Без учета sleep
        "shortest_session": {
            'name': shortest_session['name'],
            'duration': date.format_time(shortest_session['duration']) if shortest_session['duration'] > 0 else "—"
        },  # Без учета sleep
        "average_session": average_session_time  # Без учета sleep
    }


async def send_day_statistics(
    tg_obj: Message | CallbackQuery,
    target_date: datetime.date
):
    data = await states_statistics(tg_obj.from_user.id, target_date)

    answer = data['message'] if 'status' in data \
        else msg.format_user_statistics(**data)

    keyboard = inline_kb.pagination_date_kb("date_statistics", target_date).as_markup()

    await answer_or_edit(tg_obj, answer, keyboard=keyboard)


@router.message(F.text == msg.REPLY_KB['start_kb']['statistics'])
@router.message(Command("stats"))
async def today_statistics(message: Message):
    await send_day_statistics(message, date.get_now().date())


@router.callback_query(F.data.startswith("date_statistics"))
async def date_statistics(callback: CallbackQuery):
    data = callback.data.split(":")[1]
    if data != "today":
        target_date = datetime.strptime(data,"%Y-%m-%d").date()

        await send_day_statistics(callback, target_date)

    await callback.answer()
