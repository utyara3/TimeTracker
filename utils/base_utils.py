from aiogram.types import Message, CallbackQuery
from utils import bot_logging as bot_log

logger = bot_log.get_logger(__name__)


async def answer_or_edit(
    tg_obj: Message | CallbackQuery,
    text: str,
    keyboard = None
) -> None:
    try:
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
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        # Попытка отправить новое сообщение, если редактирование не удалось
        if isinstance(tg_obj, CallbackQuery):
            try:
                if keyboard:
                    await tg_obj.message.answer(text, reply_markup=keyboard)
                else:
                    await tg_obj.message.answer(text)
            except Exception as e2:
                logger.error(f"Не удалось отправить сообщение после ошибки редактирования: {e2}")

