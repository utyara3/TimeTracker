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