from aiogram.types import Message, CallbackQuery


async def answer_or_edit(
    tg_obj: Message | CallbackQuery,
    text: str,
    keyboard = None
) -> None:
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

