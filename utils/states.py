from aiogram.fsm.state import State, StatesGroup

class ChangeStateTag(StatesGroup):
    tag = State()
    