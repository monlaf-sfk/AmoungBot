
import os
from datetime import datetime

from aiogram import Router, F, flags
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Game, Player, utc_plus_5
from keyboard.start import get_yes_no_kb

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
async def answer_yes(message: Message, session: AsyncSession):
    player = await session.get(Player, message.from_user.id)
    if not player:
        player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            is_registered=False
        )
        session.add(player)
        await session.commit()
    await message.answer(
        f"""
**👤 Профиль игрока:**

- **Имя пользователя:** `{message.from_user.username}`
- **Уровень:** `{player.level}`

- **Победы:** `{player.winrate}`
- **Поражения:** `{player.losses}`


- **Дата регистрации:** `{player.date_register}`
""", parse_mode="Markdown"
    )


