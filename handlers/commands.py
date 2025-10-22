from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from data import messages as msg
from keyboards.reply import start_kb

router = Router()


@router.message(Command('start'))
async def start_cmd(message: Message):
    await message.answer(
        msg.COMMON['start_cmd'],
        reply_markup=start_kb().as_markup(resize_keyboard=True),
    )


@router.message(Command('cancel'))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(msg.COMMON['cancel_cmd'])


@router.message(Command('help'))
async def help_cmd(message: Message):
    await message.answer(msg.COMMON['help_cmd'])
