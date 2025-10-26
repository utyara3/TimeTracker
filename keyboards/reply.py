from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import data.messages as msg

def _base(elements: list, adj: int) -> ReplyKeyboardBuilder:
    builder = ReplyKeyboardBuilder()

    for element in elements:
        builder.add(KeyboardButton(text=element))

    builder.adjust(adj)
    return builder


def start_kb() -> ReplyKeyboardBuilder:
    return _base(msg.REPLY_KB['start_kb'].values(), 2)
