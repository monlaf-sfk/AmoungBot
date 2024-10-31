
from aiogram import Router, F, flags, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, BufferedInputFile, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Game, Player, utc_plus_5
from filters.chat_type import ChatTypeFilter
from keyboard.start import main_menu_kb, cancel_kb, create_profile_update_kb, create_faculty_selection_kb, faculties, \
    course_button_kbs
from state.registr import Photo, Full_name

router = Router()  # [1]
router.message.filter(ChatTypeFilter(chat_type="private"))
@router.message(Command("start"))  # [2]
@flags.throttling_key('default')
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! Добро пожаловать в команду! Готов ли ты найти предателя и спасти экипаж в Among Us?",
        reply_markup=main_menu_kb(message.from_user.id)
    )


@router.message(F.text.lower() == "профиль 👤")
@flags.throttling_key('default')
async def display_profile(message: Message, session: AsyncSession, bot: Bot):
    player = await session.get(Player, message.from_user.id)

    if not player:
        player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            is_registered=False
        )
        session.add(player)
        await session.commit()

    profile_info = (
        f"**👤 Профиль игрока:**\n\n"
        f"- **Имя пользователя:** `{message.from_user.username}`\n"
        f"- **Количество убийств:** `{player.count_kill}`\n"
        f"- **Победы:** `{player.winrate}`\n"
        f"- **Поражения:** `{player.losses}`\n"
        f"- **Дата регистрации:** `{player.date_register}`\n\n"
    )

    # Add optional fields if they exist
    if player.first_name or player.last_name :
        profile_info += f"- **ФИО:** `{player.first_name}{" "+player.sur_name if player.sur_name else ''} {player.last_name}`\n"
    if player.faculty:
        profile_info += f"- **Факультет:** `{faculties[player.faculty]}`\n"
    if player.course:
        profile_info += f"- **Курс:** `{player.course}`\n"
    if player.phone:
        profile_info += f"- **Телефон:** `{player.phone}`\n"

    # Create inline keyboard for updating missing information
    update_kb = create_profile_update_kb(player)

    # Send profile photo if available; otherwise, send text-only profile
    if player.photo:
        await bot.send_photo(
            chat_id=message.chat.id,
            caption=profile_info,
            parse_mode="Markdown",
            photo=BufferedInputFile(player.photo, filename="photo.jpg"),
            reply_markup=update_kb
        )
    else:
        await message.answer(profile_info, parse_mode="Markdown", reply_markup=update_kb)



@router.callback_query(F.data == "add_photo")
@flags.throttling_key('default')
async def set_photo(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Отправь мне фото для профиля")
    await state.set_state(Photo.send_photo)

@router.message(StateFilter(None),Command("set_photo"))
@flags.throttling_key('default')
async def set_photo(message: Message, state: FSMContext):
    await message.answer("Отправь мне фото для профиля")
    await state.set_state(Photo.send_photo)

@router.message(
    Photo.send_photo,
    F.photo
)
async def food_chosen(message: Message, state: FSMContext, session: AsyncSession):
    file_path = await message.bot.download(file=message.photo[-1].file_id)


    # Получаем игрока из базы данных
    player = await session.get(Player, message.from_user.id)
    if not player:
        player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            is_registered=False
        )
        session.add(player)
        await session.commit()
    # Сохраняем фото в BLOB

    player.photo = file_path.read()
    await session.commit()

    await message.answer("Ваше фото профиля успешно обновлено!")
    await state.clear()

@router.message(Photo.send_photo)
@flags.throttling_key('default')
async def food_chosen(message: Message, state: FSMContext):
    await message.answer("Отправьте фото, пожалуйста. /set_photo")
    await state.clear()


@router.callback_query(F.data == "add_faculty")
async def add_faculty_prompt(callback_query: CallbackQuery):
    await callback_query.message.answer("Выберите ваш факультет:", reply_markup=create_faculty_selection_kb())
@router.message(Command("set_faculty"))
async def add_faculty_prompt(message: Message):
    await message.answer("Выберите ваш факультет:", reply_markup=create_faculty_selection_kb())

@router.callback_query(F.data.startswith("select_faculty:"))
async def save_faculty(callback_query: CallbackQuery, session: AsyncSession):
    selected_faculty = callback_query.data.split(":")[1]
    player = await session.get(Player, callback_query.from_user.id)
    player.faculty = selected_faculty
    await session.commit()
    await callback_query.message.edit_text(f"Факультет '{faculties[selected_faculty]}' добавлен.")





@router.callback_query(F.data =="add_name")
@flags.throttling_key('default')
async def set_photo(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Отправь мне имя для профиля", reply_markup=cancel_kb())
    await state.set_state(Full_name.name)


@router.message(StateFilter(None),Command("set_name"))
@flags.throttling_key('default')
async def set_photo(message: Message, state: FSMContext):
    await message.answer("Отправь мне имя для профиля", reply_markup=cancel_kb())
    await state.set_state(Full_name.name)

@router.message(F.text.lower() == "отмена", StateFilter(Full_name))
async def cancel_registration(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Регистрация отменена.", reply_markup=main_menu_kb(message.from_user.id))

@router.message(Full_name.name)
async def set_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Введите вашу фамилию:")
    await state.set_state(Full_name.last_name)

@router.message(Full_name.last_name)
async def set_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Введите ваше отчество (если нет, напишите '-'): ")
    await state.set_state(Full_name.surname)

@router.message(Full_name.surname)
async def set_middle_name(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    middle_name = message.text if message.text != '-' else None

    # Check if the user is already registered
    player = await session.get(Player, message.from_user.id)
    if not player:
        player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            is_registered=False
        )
        session.add(player)
        await session.commit()

    player.first_name = data["first_name"]
    player.last_name = data["last_name"]
    player.sur_name = middle_name
    await session.commit()

    # Create a new Player instance with FIO details
    await message.answer("Регистрация завершена! Теперь вы зарегистрированы в системе.", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()




@router.callback_query(F.data == "add_course")
async def add_faculty_prompt(callback_query: CallbackQuery):
    await callback_query.message.answer("Выберите ваш факультет:", reply_markup=course_button_kbs())

@router.message(Command("set_course"))
async def add_faculty_prompt(message: Message):
    await message.answer("Выберите ваш факультет:", reply_markup=course_button_kbs())


@router.callback_query(F.data.startswith("course_"))
async def save_faculty(callback_query: CallbackQuery, session: AsyncSession):
    course = callback_query.data.split("_")[1]
    player = await session.get(Player, callback_query.from_user.id)
    player.course = course
    await session.commit()
    await callback_query.message.edit_text(f"Курс {course} выбран")


@router.message(F.text.lower() == "о нас 🩸")
@flags.throttling_key('default')
async def display_profile(message: Message, session: AsyncSession, bot: Bot):
    await message.answer(
    "О нас🩸\n"
    "Добро пожаловать в мир теней \n"
    "и охотников… Slayer KBTU — \n"
    "это захватывающая игра, где \n"
    "каждый участник превращается в хладнокровного охотника и цель \n"
    "одновременно. Вас ждет адреналин, "
    "жуткие повороты и настоящая битва за выживание! \n"
    "Останься последним и докажи, что ты - достойный \n"
    "победитель.\n\n"
    "Следи за новостями и готовься к охоте!\n"
    "@amoung_news"
    )

@router.message(F.text.lower() == "правила игры 👻")
@flags.throttling_key('default')
async def display_profile(message: Message, session: AsyncSession, bot: Bot):
    await message.answer(
    """
Правила игры👻

Ты стал охотником в ночи, но игра требует не только скорости и ловкости, но и строгого соблюдения правил. Помни:
    
 *• Цель:* коснись или отметь свою “добычу”. Охотник забирает жетон или отметку как доказательство.
 *• Место и время:* ограниченное время и замкнутая территория — не пытайся сбежать!
 *• Защита и укрытие:* прячься и беги, но помни — охота не терпит нарушений!
 *• Этика и безопасность:* никаких физических атак, уважай других игроков.
 *• Победитель:* последний выживший или тот, кто поймал больше всего целей. Тьма на твоей стороне, но будь осторожен — тебя тоже ищут!
 """
   ,parse_mode="Markdown" )
