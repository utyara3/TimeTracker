from datetime import datetime, timedelta

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


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


def pagination_date_statistics(today: datetime.date) -> InlineKeyboardBuilder:
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"{yesterday.day} ←",
            callback_data=f"date_statistics:{yesterday}"
        ),
        InlineKeyboardButton(
            text=f"{today.day}/{today.month}",
            callback_data="date_statistics:today"
        ),
        InlineKeyboardButton(
            text=f"→ {tomorrow.day}",
            callback_data=f"date_statistics:{tomorrow}"
        )
    )

    return builder