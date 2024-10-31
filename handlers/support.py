import os
import re

from aiogram import Router, flags, F, Bot
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile
from pandas.io.pytables import dropna_doc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Player, admins
from filters.admins import IsAdmin
from filters.chat_type import ChatTypeFilter
from state.registr import Support
router = Router()
router.message.filter(ChatTypeFilter(chat_type="private"))
@router.message(StateFilter(None),Command("support"))
@router.message(StateFilter(None),F.text.lower() == "поддержка")
@flags.throttling_key('default')
async def set_photo(message: Message, state: FSMContext, session: AsyncSession):
    player = await session.get(Player, message.from_user.id)
    if not player:
        player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            is_registered=False
        )
        session.add(player)
        await session.commit()

    await message.answer("Пожалуйста, опишите вашу проблему! (с фото или без)")
    await state.set_state(Support.waiting_for_support)

@router.message(Support.waiting_for_support , F.photo)
async def food_chosen(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    file_path = await message.bot.download(file=message.photo[-1].file_id)
    # Получаем игрока из базы данных
    # Сохраняем фото в BLOB
    caption = message.caption if message.caption else "Фото без описания"

    # Пересылка фото в чат поддержки
    await bot.send_photo(os.getenv("CHAT_SUPPORT"), photo=BufferedInputFile(file_path.read(), filename="photo.jpg"),
                         caption=f"Запрос от пользователя {message.from_user.id}:\n\n{caption}")
    await message.reply("Ваш запрос с фото был отправлен. Пожалуйста, ожидайте ответа.")
    await state.clear()

@router.message(Support.waiting_for_support, F.text)
@flags.throttling_key('default')
async def food_chosen(message: Message, state: FSMContext, bot: Bot):
    await bot.send_message(os.getenv("CHAT_SUPPORT"), f"Запрос от пользователя {message.from_user.id}:\n\n{message.text}")
    await message.reply("Ваш запрос был отправлен. Пожалуйста, ожидайте ответа.")
    await state.clear()

@router.message(Support.waiting_for_support)
@flags.throttling_key('default')
async def food_chosen(message: Message, state: FSMContext):
    await message.answer("Отправьте текстовое описание вашей проблемы, пожалуйста.")
    await state.clear()

@router.message(F.chat.id == int(os.getenv("CHAT_SUPPORT")), IsAdmin(admins) , Command("a"))
async def support_reply(message: Message, bot: Bot):
    message_text = message.text.replace("/a ", "") if not message.photo else message.caption.replace("/a ", "")
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя, чтобы отправить ему ответ.")
        return
    replay_text = message.reply_to_message.caption if message.reply_to_message.photo else message.reply_to_message.text
    match = re.search(r"Запрос от пользователя (\d+):", replay_text)

    if match:
        user_id = int(match.group(1))
    else:
        await message.answer("Не удалось найти ID пользователя в тексте запроса.")
        return
        # Проверяем, содержит ли ответное сообщение фото, и отправляем ответ с фото или без
    if message.photo:
        # Если ответ содержит фото, отправляем его пользователю с текстом
        await bot.send_photo(user_id, photo=message.photo[-1].file_id,
                             caption=f"Ответ от поддержки:\n\n{message_text}")
    else:
        # Если фото нет, отправляем только текст
        await bot.send_message(user_id, f"Ответ от поддержки:\n\n{message_text}")


    await message.answer("Ответ отправлен.")
