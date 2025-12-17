from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def create_back_keyboard(state_id: int, callback_prefix: str = "choose_state") -> InlineKeyboardBuilder:
    """
    Создает клавиатуру с кнопкой "Назад к состоянию".
    
    Args:
        state_id: ID состояния
        callback_prefix: Префикс для callback_data (по умолчанию "choose_state")
    
    Returns:
        InlineKeyboardBuilder с кнопкой "Назад"
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к состоянию",
            callback_data=f"{callback_prefix}:{state_id}"
        )
    )
    return builder

