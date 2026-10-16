from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import keyboards.inline as inline_kb
from data import messages as msg
from database import core as db
from handlers import user_history, user_statistics
from utils import bot_logging as bot_log
from utils import date
from utils.base_utils import answer_or_edit

router = Router()
logger = bot_log.get_logger(__name__)

KNOWN_VIEWS = ("date_history", "date_statistics")


@router.callback_query(F.data.startswith("calendar:"))
async def calendar_view(callback: CallbackQuery) -> None:
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            logger.error(f"Неверный формат callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных")
            return

        info, action = parts[1], parts[2]

        if info not in KNOWN_VIEWS:
            logger.error(f"Неизвестный раздел календаря: {callback.data}")
            await callback.answer("Ошибка: неизвестный раздел")
            return

        if action == "noop":
            await callback.answer()
            return

        if action == "month":
            year, month = map(int, parts[3].split("-"))
            await send_month_calendar(callback, info, year, month)
            await callback.answer()
            return

        if action == "day":
            target_day = datetime.strptime(parts[3], "%Y-%m-%d").date()
        elif action == "today":
            target_day = date.get_now().date()
        else:
            logger.error(f"Неизвестное действие календаря: {callback.data}")
            await callback.answer("Ошибка: неизвестное действие")
            return

        if target_day > date.get_now().date():
            await callback.answer("Этот день ещё не наступил")
            return

        await open_day(callback, info, target_day)
        await callback.answer()
    except (ValueError, IndexError, AttributeError) as e:
        logger.error(f"Ошибка обработки календаря: {callback.data}, {e}")
        await callback.answer("Ошибка обработки запроса")


async def send_month_calendar(
    tg_obj: Message | CallbackQuery,
    info: str,
    year: int,
    month: int
) -> None:
    active_days = await db.get_user_active_dates(
        tg_obj=tg_obj,
        year=year,
        month=month
    )

    keyboard = inline_kb.calendar_kb(info, year, month, active_days)

    await answer_or_edit(
        tg_obj,
        msg.format_month_calendar(info=info, year=year, month=month),
        keyboard=keyboard.as_markup()
    )


async def open_day(
    callback: CallbackQuery,
    info: str,
    target_day: datetime.date
) -> None:
    if info == "date_history":
        await user_history.send_day_history(callback, target_day)
    elif info == "date_statistics":
        await user_statistics.send_day_statistics(callback, target_day)
