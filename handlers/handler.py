from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from datetime import datetime
from collections import Counter

from data import messages as msg
import keyboards.reply as reply_kb
import keyboards.inline as inline_kb

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
async def states_message(message: Message) -> None:
    await message.answer(msg.COMMON['states_message'])


@router.message(F.text == msg.REPLY_KB['start_kb']['history'])
async def states_history(message: Message) -> None:
    states = await db.get_user_states(message=message, limit=5)

    await message.answer(msg.format_states_history(states=states))


@router.message(F.text == msg.REPLY_KB['start_kb']['statistics'])
async def states_statistics(message: Message) -> None:
    await message.answer("<i>Данная функция пока что не реализована...</i>")
