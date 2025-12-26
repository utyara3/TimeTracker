import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from datetime import datetime, timedelta
from collections import Counter

from data import messages as msg
import keyboards.reply as reply_kb
import keyboards.inline as inline_kb

from utils import date
from utils import bot_logging as bot_log
from utils.base_utils import answer_or_edit
from utils.states import ChangeStateTag

from database import core as db

router = Router()
logger = bot_log.get_logger(__name__)


@router.message(Command('start'))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    
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
@router.callback_query(F.data == 'cancel')
async def cancel_cmd(tg_obj: Message | CallbackQuery, state: FSMContext):
    await state.clear()

    await answer_or_edit(tg_obj, msg.COMMON['cancel_cmd'])


@router.message(Command('help'))
async def help_cmd(message: Message):
    await message.answer(msg.COMMON['help_cmd'])


@router.message(Command("my_tags"))
async def user_tags(message: Message) -> None:
    tags = await db.get_user_tags(message=message)

    if tags is None or len(tags) == 0:
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
async def fix_cmd(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    
    args = command.args

    if not args:
        await message.answer(msg.FAILURE['wrong_args'])
        logger.info("fix no args")
        return

    parts = args.split()

    time_parts = {}
    state_and_tag = []

    state_and_tag = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if re.search(r'\d+\s*[hmчм]', part):
            if 'duration' not in time_parts:
                time_parts['duration'] = []
            time_parts['duration'].append(part)
            i += 1
        elif re.search(r'\d+:\d+', part):
            if 'start_time' not in time_parts:
                time_parts['start_time'] = []
            time_parts['start_time'].append(part)
            i += 1
        else:
            state_and_tag = parts[i:]
            break

    if not time_parts or not state_and_tag:
        await message.answer(msg.FAILURE['wrong_args'])
        return

    states = await db.get_user_states(tg_obj=message, limit=2)
    if not states or len(states) < 1:
        await message.answer(msg.FAILURE['no_states_today'])
        return

    current_state = states[0]
    state_start_time = date.to_datetime(current_state['start_time'])

    if time_parts.get('start_time', ''):
        offset = timedelta(seconds=59)
        hhmm_str = ''.join(time_parts['start_time'])
        start_time_candidate = date.resolve_hhmm_to_datetime(
            hhmm_str,
            now=date.get_now(),
            session_start=state_start_time
        )
        if start_time_candidate is None or start_time_candidate <= state_start_time + offset:
            await message.answer(msg.FAILURE['wrong_args'])
            return

        dur_sec_args = (date.get_now() - start_time_candidate).total_seconds()
    else:
        dur_sec_args = date.duration_seconds_from_string(
            ' '.join(time_parts['duration'])
        )

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

    await message.answer(msg.COMMON['rate_old_state'], reply_markup=kb.as_markup())


@router.message(Command(*msg.DEFAULT_STATES.keys()))
async def change_state_cmd(message: Message, state: FSMContext):
    await state.clear()
    
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
    try:
        parts = callback_query.data.split(":")
        if len(parts) < 3:
            logger.error(f"Неверный формат callback_data: {callback_query.data}")
            await callback_query.answer("Ошибка: неверный формат данных")
            return
        
        time_session = int(parts[1])
        mood = int(parts[2])
        
        # Валидация mood
        if mood < 1 or mood > 5:
            logger.warning(f"Неверное значение mood: {mood}, user_id={callback_query.from_user.id}")
            await callback_query.answer("Оценка должна быть от 1 до 5")
            return

        await db.rate_state(time_session_id=time_session, mood=mood)

        await callback_query.message.edit_text(msg.SUCCESS['state_rated'])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка в rate_time_session: {e}, data={callback_query.data}")
        await callback_query.answer("Ошибка обработки запроса")


@router.message(F.text == msg.REPLY_KB['start_kb']['set_state'])
@router.message(Command("set_state"))
async def states_message(message: Message) -> None:
    await message.answer(msg.COMMON['states_message'])


@router.callback_query(F.data == "view_full_stats")
async def view_full_stats(callback: CallbackQuery):
    await callback.answer()
