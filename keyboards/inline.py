from datetime import datetime, timedelta

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from utils import date


def rate_keyboard(time_session_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    for num in range(1, 6):
        builder.add(
            InlineKeyboardButton(
                text=str(num),
                callback_data=f"rate_time_session:{time_session_id}:{num}"
            )
        )

    return builder


def pagination_date_kb(info: str, current_day: datetime.date) -> InlineKeyboardBuilder:
    today = date.get_now()
    
    yesterday = current_day - timedelta(days=1)
    tomorrow = current_day + timedelta(days=1)
    
    buttons = []
    buttons.append(
        InlineKeyboardButton(
            text=f"{yesterday.day} ←",
            callback_data=f"{info}:{yesterday}"
        )
    )
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_day.day}/{current_day.month}",
            callback_data=f"{info}:{current_day}:edit"
        ),
    )
    if current_day.day != today.day:
        buttons.append(
            InlineKeyboardButton(
                text=f"→ {tomorrow.day}",
                callback_data=f"{info}:{tomorrow}"
            ),
        )

    builder = InlineKeyboardBuilder()
    builder.row(*buttons)

    return builder
