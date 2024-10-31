from aiogram.fsm.state import StatesGroup, State


class Photo(StatesGroup):
    send_photo = State()

class Full_name(StatesGroup):
    name = State()
    last_name = State()
    surname = State()


class ProfileUpdateState(StatesGroup):
    waiting_for_course = State()

class Support(StatesGroup):
    waiting_for_support = State()
    waiting_for_support_text = State()
    waiting_for_support_photo = State()

class PaidState(StatesGroup):
    recipt = State()


class PromocodeState(StatesGroup):
    code = State()