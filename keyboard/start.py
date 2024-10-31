

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


from db.models import Player, admins


def main_menu_kb(user_id) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="Профиль 👤"),
    KeyboardButton(text="Регистрация на игру 👾"))



    if user_id in admins:


        kb.row(
        KeyboardButton(text="Создать игру"),
        KeyboardButton(text="Начать игру"),
        KeyboardButton(text="Завершить игру")
               )
        kb.row(
        KeyboardButton(text="Закрыть регистрацию"),
        KeyboardButton(text="Открыть регистрацию"))
        KeyboardButton(text="О нас 🩸")
        kb.row(KeyboardButton(text="Текущая игра 🔘"),
               KeyboardButton(text="О нас 🩸"))
        kb.row(KeyboardButton(text="Правила игры 👻"))
        return kb.as_markup(resize_keyboard=True)
    kb.row(KeyboardButton(text="Текущая игра 🔘"),
           KeyboardButton(text="О нас 🩸"))
    kb.row(KeyboardButton(text="Правила игры 👻"))
    return kb.as_markup(resize_keyboard=True)

def game_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Убить")
    kb.button(text="Информация по игре")
    kb.button(text="Поддержка")

    kb.button(text="Назад")


    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отмена")

    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def create_profile_update_kb(player: Player):
    builder = InlineKeyboardBuilder()

    # Add buttons for missing information
    if not player.photo:
        builder.row(InlineKeyboardButton(text="Добавить фото", callback_data="add_photo"))
    if not player.first_name or not player.last_name:
        builder.row(InlineKeyboardButton(text="Добавить полное имя", callback_data="add_name"))
    if not player.faculty:
        builder.row(InlineKeyboardButton(text="Добавить факультет", callback_data="add_faculty"))
    if not player.course:
        builder.row(InlineKeyboardButton(text="Добавить курс", callback_data="add_course"))

    return builder.as_markup()



faculties = {
    "energy_school": "ШКОЛА ЭНЕРГЕТИКИИ НЕФТЕГАЗОВОЙ ИНДУСТРИИ",
    "geology_school": "ШКОЛА ГЕОЛОГИИ",
    "it_engineering_school": "ШКОЛА ИНФОРМАЦИОННЫХ ТЕХНОЛОГИЙ И ИНЖЕНЕРИИ",
    "business_school": "БИЗНЕС ШКОЛА",
    "international_economics_school": "МЕЖДУНАРОДНАЯ ШКОЛА ЭКОНОМИКИ",
    "maritime_academy": "КАЗАХСТАНСКАЯ МОРСКАЯ АКАДЕМИЯ",
    "applied_math_school": "ШКОЛА ПРИКЛАДНОЙ МАТЕМАТИКИ",
    "chemical_engineering_school": "ШКОЛА ХИМИЧЕСКОЙ ИНЖЕНЕРИИ",
    "social_sciences_school": "ШКОЛА СОЦИАЛЬНЫХ НАУК",
    "materials_green_tech_school": "ШКОЛА МАТЕРИАЛОВЕДЕНИЯ И ЗЕЛЕНЫХ ТЕХНОЛОГИЙ"
}


# Create inline keyboard for faculty selection
def create_faculty_selection_kb() :
    keyboard = InlineKeyboardBuilder()
    for faculty in faculties:
        keyboard.row(InlineKeyboardButton(text=faculties[faculty], callback_data=f"select_faculty:{faculty}"))
    return keyboard.as_markup()

def course_button_kbs():
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="1", callback_data="course_1"),
        InlineKeyboardButton(text="2", callback_data="course_2"),
        InlineKeyboardButton(text="3", callback_data="course_3"),
        InlineKeyboardButton(text="4", callback_data="course_4"),
    )

    return keyboard.as_markup()