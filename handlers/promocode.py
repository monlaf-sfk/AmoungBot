
from datetime import datetime

from aiogram import Bot, Router, F, flags
from aiogram.filters import Command

from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


from aiogram import types
from db.models import GamePlayers, Game, Promocode, admins
from db.schedualer import  utc_plus_5
from filters.admins import IsAdmin
from filters.chat_type import ChatTypeFilter

from state.registr import PromocodeState

router = Router()
router.message.filter(ChatTypeFilter(chat_type="private"))

@router.message(Command("promocode"))
@router.message(F.text.lower() == "промокод")
@flags.throttling_key('default')
async def initiate_kill(message: types.Message, state: FSMContext, session: AsyncSession):
    active_game = await session.execute(
        select(Game).where(Game.registration == False, Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()

    if not active_game:
        await message.answer("Нет активной игры.")
        await state.clear()
        return
    player = await session.execute(
        select(GamePlayers).where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == message.from_user.id)
    )
    player = player.scalar_one_or_none()

    if not player:
        await message.answer("Вы не участвуете в текущей игре.")
        await state.clear()
        return
    if not player.is_alive:
        await message.answer("Вы выбыли.")
        await state.clear()
        return
    await message.answer("Введите код для подтверждения")
    await state.set_state(PromocodeState.code)


# Шаг 2: Обработчик состояния для проверки кода
@router.message(PromocodeState.code)
@flags.throttling_key('default')
async def confirm_kill(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
    # Get the entered code
    entered_code = message.text.strip().upper()  # Normalize the input

    # Fetch the active game
    active_game = await session.execute(
        select(Game).where(Game.registration == False, Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()

    if not active_game:
        await message.answer("Нет активной игры.")
        await state.clear()
        return

    # Get the current player
    player = await session.execute(
        select(GamePlayers).where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == message.from_user.id)
    )
    player = player.scalar_one_or_none()

    if not player:
        await message.answer("Вы не участвуете в текущей игре.")
        await state.clear()
        return

    if not player.is_alive:
        await message.answer("Вы выбыли.")
        await state.clear()
        return

    # Fetch the quest using the entered code
    quest = await session.execute(
        select(Promocode).filter_by(code=entered_code)
    )
    quest = quest.scalar_one_or_none()

    if quest:
        if quest.activation_count <=0:
            await message.answer("Промокод уже использован.")
            await state.clear()
        player.last_kill = datetime.now(utc_plus_5)
        quest.activation_count -= 1
        await session.commit()
        await message.answer("Промокод успешно активирован!")
    else:
        await message.answer("Неверный код. Попробуйте снова.")
        await state.clear()
        return
    # Clear the state after processing
    await state.clear()

@router.message(Command("create_promocode"), IsAdmin(admins))
@router.message(F.text.lower() == "создать промокод")
async def create_promocode(message: types.Message, state: FSMContext, session: AsyncSession):

    # Split the message text into parts
    parts = message.text.split()

    # Check if the correct number of arguments is provided
    if len(parts) != 3:
        await message.answer("Используйте: /create_promocode <код> <максимальное количество активаций>")
        return

    quest_code = parts[1].strip()  # Quest code
    max_activations = parts[2].strip()  # Max activations

    # Validate max activations input
    if not max_activations.isdigit() or int(max_activations) <= 0:
        await message.answer(
            "Пожалуйста, введите действительное положительное число для максимального количества активаций.")
        return

    max_activations = int(max_activations)

    # Check if quest code already exists

    existing_quest = await session.execute(
        select(Promocode).filter_by(code=quest_code)
    )
    if existing_quest.scalar_one_or_none() is not None:
        await message.answer("Код промокода уже существует. Пожалуйста, выберите другой код.")
        return

    # Create and save the new quest
    new_quest = Promocode(code=quest_code, activation_count=max_activations)
    session.add(new_quest)
    await session.commit()

    await message.answer(
        f"Помокод '{quest_code}' успешно создан с максимальным количеством активаций: {max_activations}.")
