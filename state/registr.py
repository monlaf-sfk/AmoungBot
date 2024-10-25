from aiogram.fsm.state import StatesGroup, State


class Photo(StatesGroup):
    send_photo = State()
