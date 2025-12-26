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
    states = await db.get_user_states_by_date(tg_obj=tg_obj, target_date=target_day)

    keyboard_builder = inline_kb.pagination_date_kb("date_history", target_day)
    keyboard = keyboard_builder.as_markup()

    if not states:
        await answer_or_edit(tg_obj, msg.FAILURE['no_states_today'], keyboard=keyboard)
        return

    await answer_or_edit(
        tg_obj,
        msg.format_states_history(states=states),
        keyboard=keyboard
    )


@router.callback_query(F.data.startswith("date_history"))
async def date_history(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        day = datetime.strptime(parts[1], "%Y-%m-%d").date()

        if "edit" not in callback.data:
            await send_day_history(callback, day)
        else:
            await choose_state_to_change(callback, day)

        await callback.answer()
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback_data: {callback.data}, {e}")
        await callback.answer("Ошибка обработки запроса")


async def choose_state_to_change(
    callback: CallbackQuery, 
    day: datetime.date
) -> None:
    states = await db.get_user_states_by_date(tg_obj=callback, target_date=day)

    if not states:
        await callback.answer("Нет состояний за этот день")
        return

    builder = InlineKeyboardBuilder()
    for state in states:
        start_time = date.to_datetime(state['start_time'])
        start_time_str = date.format_time_hhmm(start_time)
        end_time = date.format_time_hhmm(
            date.to_datetime(state['end_time']) if state['end_time'] else date.get_now()
        )

        builder.row(
            InlineKeyboardButton(
                text=f"{start_time_str}-{end_time} | {state['state_name']}",
                callback_data=f"choose_state:{state['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"date_history:{day}"
        )
    )

    await callback.message.edit_text(msg.COMMON['choose_state_to_change'], reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("back_to_states_list"))
async def back_to_states_list(callback: CallbackQuery) -> None:
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        day = datetime.strptime(parts[1], "%Y-%m-%d").date()
        await choose_state_to_change(callback, day)
        await callback.answer()
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback_data: {callback.data}, {e}")
        await callback.answer("Ошибка обработки запроса")


@router.callback_query(F.data.startswith("choose_state"))
async def state_info(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        state_id = int(parts[1])
        state_info = await db.get_state_by_id(state_id, tg_id=callback.from_user.id)
        
        if state_info is None:
            logger.warning(f"Попытка доступа к чужому состоянию: user_id={callback.from_user.id}, state_id={state_id}")
            await callback.answer("Состояние не найдено")
            return
        
        state_info['start_time'] = date.to_datetime(state_info['start_time'])
        if state_info['end_time']:
            state_info['end_time'] = date.to_datetime(state_info['end_time'])
        else:
            state_info['end_time'] = date.get_now()

        state_info['duration_seconds'] = date.calculate_duration_seconds(
            start_time=state_info['start_time'],
            end_time=state_info['end_time'],
            duration_seconds=state_info.get('duration_seconds')
        )
        
        text = msg.format_state_info(state_info)
        
        # Получаем день для кнопки "Назад"
        day = state_info['start_time'].date()

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
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"back_to_states_list:{day}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="Отменить",
                callback_data="cancel"
            )
        )
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка в state_info: {e}, data={callback.data}")
        await callback.answer("Ошибка обработки запроса")

    await state.clear()


@router.callback_query(F.data.startswith("change_state_info"))
async def change_state_info(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        mode = parts[1]
        state_id = int(parts[2])
        
        # Проверка доступа
        state_check = await db.get_state_by_id(state_id, tg_id=callback.from_user.id)
        if not state_check:
            logger.warning(f"Попытка изменения чужого состояния: user_id={callback.from_user.id}, state_id={state_id}")
            await callback.answer("Состояние не найдено")
            return
        
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

            builder.row(
                InlineKeyboardButton(
                    text="🗑️ Удалить тег",
                    callback_data=f"delete_tag:{state_id}"
                )
            )

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
                text="◀️ Назад",
                callback_data=f"choose_state:{state_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="Отменить",
                callback_data="cancel"
            )
        )

        await callback.message.edit_text(answer, reply_markup=builder.as_markup())
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка в change_state_info: {e}, data={callback.data}")
        await callback.answer("Ошибка обработки запроса")


@router.callback_query(F.data.startswith("change_state_name"))
async def change_state_name(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        state_id = int(parts[1])
        state_name = parts[2]

        result = await db.update_state_info(
            state_id=state_id, 
            info={"state_name": state_name},
            tg_id=callback.from_user.id
        )
        
        if not result:
            logger.warning(f"Не удалось изменить состояние: user_id={callback.from_user.id}, state_id={state_id}")
            await callback.answer("Ошибка при изменении состояния")
            return

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад к состоянию",
                callback_data=f"choose_state:{state_id}"
            )
        )
        
        await callback.message.edit_text(
            msg.COMMON['state_name_changed'],
            reply_markup=builder.as_markup()
        )
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка в change_state_name: {e}, data={callback.data}")
        await callback.answer("Ошибка обработки запроса")


@router.message(ChangeStateTag.tag, F.text)
async def change_state_tag(message: Message, state: FSMContext) -> None:
    try:
        state_data = await state.get_data()
        state_id = state_data.get('state_id')
        
        if not state_id:
            logger.error(f"state_id не найден в FSM для user_id={message.from_user.id}")
            await message.answer("Ошибка: данные сессии потеряны")
            await state.clear()
            return

        result = await db.update_state_info(
            state_id=state_id, 
            info={"tag": tag},
            tg_id=message.from_user.id
        )
        
        await state.clear()
        
        if not result:
            logger.warning(f"Не удалось изменить тег: user_id={message.from_user.id}, state_id={state_id}")
            await message.answer("Ошибка при изменении тега")
            return

        builder = InlineKeyboardBuilder()
        
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад к состоянию",
                callback_data=f"choose_state:{state_id}"
            )
        )

        await message.answer(
            msg.COMMON['state_tag_changed'],
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка в change_state_tag: {e}")
        await message.answer("Ошибка обработки запроса")
    
    await state.clear()


@router.callback_query(F.data.startswith("delete_tag"))
async def delete_tag(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        state_id = int(parts[1])
        result = await db.update_state_info(
            state_id=state_id, 
            info={"tag": ""},
            tg_id=callback.from_user.id
        )
        
        if not result:
            logger.warning(f"Не удалось удалить тег для state_id={state_id}, user_id={callback.from_user.id}")
            await callback.answer("Ошибка при удалении тега")
            return

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад к состоянию",
                callback_data=f"choose_state:{state_id}"
            )
        )

        await callback.message.edit_text(
            msg.SUCCESS['state_tag_deleted'],
            reply_markup=builder.as_markup()
        )
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка при удалении тега: {e}, data={callback.data}")
        await callback.answer("Ошибка обработки запроса")

    await state.clear()


@router.callback_query(F.data.startswith("change_state_mood"))
async def change_state_mood(callback: CallbackQuery) -> None:
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return
        
        state_id = int(parts[1])
        mood = int(parts[2])
        
        # Валидация mood
        if mood < 1 or mood > 5:
            logger.warning(f"Неверное значение mood: {mood}, user_id={callback.from_user.id}")
            await callback.answer("Оценка должна быть от 1 до 5")
            return

        result = await db.update_state_info(
            state_id=state_id, 
            info={"mood": mood},
            tg_id=callback.from_user.id
        )
        
        if not result:
            logger.warning(f"Не удалось изменить оценку: user_id={callback.from_user.id}, state_id={state_id}")
            await callback.answer("Ошибка при изменении оценки")
            return

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="◀️ Назад к состоянию",
                callback_data=f"choose_state:{state_id}"
            )
        )

        await callback.message.edit_text(
            msg.COMMON['state_mood_changed'],
            reply_markup=builder.as_markup()
        )
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка в change_state_mood: {e}, data={callback.data}")
        await callback.answer("Ошибка обработки запроса")
