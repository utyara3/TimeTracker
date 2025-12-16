from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from datetime import datetime

from data import messages as msg

import keyboards.inline as inline_kb

from utils import date
from utils import bot_logging as bot_log
from utils.base_utils import answer_or_edit
from utils.states import ChangeStateTag

from database import core as db

router = Router()
logger = bot_log.get_logger(__name__)


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
async def date_history(callback: CallbackQuery):
    day = datetime.strptime(callback.data.split(":")[1], "%Y-%m-%d").date()

    if "edit" not in callback.data:
        await send_day_history(callback, day)
    else:
        await choose_state_to_change(callback, day)

    await callback.answer()


async def choose_state_to_change(
    callback: CallbackQuery, 
    day: datetime.date
) -> None:
    states = await db.get_user_states(tg_obj=callback)

    if not states:
        return

    builder = InlineKeyboardBuilder()
    for state in states:
        start_time = date.to_datetime(state['start_time'])
        # Фильтруем состояние точно по году, месяцу и дню
        if start_time.date() != day:
            continue

        start_time_str = datetime.strftime(start_time, "%H:%M")
        end_time = datetime.strftime(
            date.to_datetime(state['end_time']) if state['end_time'] else date.get_now(),
            "%H:%M"
        )

        builder.row(
            InlineKeyboardButton(
                text=f"{start_time_str}-{end_time} | {state['state_name']}",
                callback_data=f"choose_state:{state['id']}"
            )
        )

    await callback.message.edit_text(msg.COMMON['choose_state_to_change'], reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("choose_state"))
async def state_info(callback: CallbackQuery) -> None:
    state_id = int(callback.data.split(":")[1])
    state_info = await db.get_state_by_id(state_id)
    
    if state_info is None:
        # impossible?
        ...

    if state_info is None:
        print(f"user {callback.from_user.first_name} {callback.from_user.id} is trying to access something other than his own state")
        return
        
    state_info['start_time'] = date.to_datetime(state_info['start_time'])
    if state_info['end_time']:
        state_info['end_time'] = date.to_datetime(state_info['end_time'])
    else:
        state_info['end_time'] = date.get_now()

    if not state_info['duration_seconds']:
        state_info['duration_seconds'] = int(
            (date.get_now() - state_info['start_time']).total_seconds()
        )
    
    text = msg.format_state_info(state_info)

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="Изменить состояние",
            callback_data=f"change_state_info:name:{state_id}"
        ),
        InlineKeyboardButton(
            text="Изменить тег",
            callback_data=f"change_state_info:tag:{state_id}"
        ),
        InlineKeyboardButton(
            text="Изменить оценку",
            callback_data=f"change_state_info:mood:{state_id}"
        ),
        InlineKeyboardButton(
            text="Отменить",
            callback_data="cancel"
        )
    )
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("change_state_info"))
async def change_state_info(callback: CallbackQuery, state: FSMContext) -> None:
    mode, state_id = callback.data.split(":")[1:]

    state_id = int(state_id)
    builder = InlineKeyboardBuilder()
    
    if mode == "name":
        answer = msg.COMMON['choose_new_state']
        for state_name, state_info in msg.DEFAULT_STATES.items():
            builder.row(
                InlineKeyboardButton(
                    text=f"{state_info[1]} {state_name}",
                    callback_data=f"change_state_name:{state_id}:{state_name}"
                )
            )

    elif mode == "tag":
        answer = msg.COMMON['enter_new_tag']
        await state.set_state(ChangeStateTag.tag)
        await state.update_data(state_id=state_id)

    elif mode == "mood":
        answer = msg.COMMON['rate_state']
        for mood in range(1, 6):
            builder.add(
                InlineKeyboardButton(
                    text=str(mood),
                    callback_data=f"change_state_mood:{state_id}:{mood}"
                )
            )

    builder.row(
        InlineKeyboardButton(
            text="Отменить",
            callback_data="cancel"
        )
    )

    await callback.message.edit_text(answer, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("change_state_name"))
async def change_state_name(callback: CallbackQuery, state: FSMContext) -> None:
    state_id = int(callback.data.split(":")[1])
    state_name = callback.data.split(":")[2]

    await db.update_state_info(state_id=state_id, info={"state_name": state_name})

    await callback.message.edit_text(msg.COMMON['state_name_changed'])


@router.message(ChangeStateTag.tag, F.text)
async def change_state_tag(message: Message, state: FSMContext) -> None:
    state_data = await state.get_data()
    state_id = state_data.get('state_id')
    tag = message.text.lower()

    await db.update_state_info(state_id=state_id, info={"tag": tag})

    await message.answer(msg.COMMON['state_tag_changed'])


@router.callback_query(F.data.startswith("change_state_mood"))
async def change_state_mood(callback: CallbackQuery) -> None:
    data = callback.data.split(":")
    state_id = int(data[1])
    mood = int(data[2])

    await db.update_state_info(state_id=state_id, info={"mood": mood})

    await callback.message.edit_text(msg.COMMON['state_mood_changed'])

