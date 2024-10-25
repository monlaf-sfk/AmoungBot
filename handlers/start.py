
import os
from datetime import datetime
from io import BytesIO

from aiogram import Router, F, flags, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Game, Player, utc_plus_5
from keyboard.start import get_yes_no_kb
from state.registr import Photo

router = Router()  # [1]

@router.message(Command("start"))  # [2]
@flags.throttling_key('default')
async def cmd_start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! Добро пожаловать в команду! Готов ли ты найти предателя и спасти экипаж в Among Us?",
        reply_markup=get_yes_no_kb()
    )

@router.message(F.text.lower() == "profile")
@flags.throttling_key('default')
async def answer_yes(message: Message, session: AsyncSession, bot: Bot):
    player = await session.get(Player, message.from_user.id)
    if not player:
        player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            is_registered=False
        )
        session.add(player)
        await session.commit()
    if player.photo:
        await bot.send_photo(chat_id=message.chat.id,caption=
            f"""
**👤 Профиль игрока:**

- **Имя пользователя:** `{message.from_user.username}`
- **Уровень:** `{player.level}`

- **Победы:** `{player.winrate}`
- **Поражения:** `{player.losses}`


- **Дата регистрации:** `{player.date_register}`
    """, parse_mode="Markdown",photo=BufferedInputFile(player.photo, filename="photo.jpg"))
    else:
        await message.answer(
            f"""
**👤 Профиль игрока:**

- **Имя пользователя:** `{message.from_user.username}`
- **Уровень:** `{player.level}`

- **Победы:** `{player.winrate}`
- **Поражения:** `{player.losses}`


- **Дата регистрации:** `{player.date_register}`
    """, parse_mode="Markdown")

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
async def food_chosen(message: Message, state: FSMContext):
    await message.answer("Отправьте фото, пожалуйста. /set_photo")
    await state.clear()
