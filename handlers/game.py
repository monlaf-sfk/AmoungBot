from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models import Player, GamePlayers, Game

router = Router()


class HuntState(StatesGroup):
    waiting_for_code = State()


# Шаг 1: Команда для инициации подтверждения убийства
@router.message(Command("kill"))
async def initiate_kill(message: types.Message, state: FSMContext, session: AsyncSession):
    await message.answer("Введите код вашей цели для подтверждения убийства:")
    await state.set_state(HuntState.waiting_for_code)


# Шаг 2: Обработчик состояния для проверки кода
@router.message(HuntState.waiting_for_code)
async def confirm_kill(message: types.Message, state: FSMContext, session: AsyncSession):
    # Получаем введенный код
    entered_code = message.text
    active_game = await session.execute(
        select(Game).where(Game.registration == False, Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()

    if not active_game:
        await message.answer("Нет активной игры.")
        await state.clear()
        return

    # Получаем текущего игрока и его цель
    player = await session.execute(
        select(GamePlayers).where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == message.from_user.id)
    )
    player = player.scalar_one_or_none()

    if not player:
        await message.answer("Вы не участвуете в текущей игре.")
        await state.clear()
        return

    target_player_id = player.target_id

    # Проверяем правильность кода
    target = await session.execute(
        select(GamePlayers).where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == target_player_id)
    )
    target = target.scalar_one_or_none()

    if not target:
        await message.answer("Цель не найдена.")
        await state.clear()
        return

    if target.secret_code == entered_code:
        # Код подтвержден, цель считается убитой
        player.count_kills += 1
        player.target_id = target.target_id  # передаем цель дальше
        target.is_alive = False  # цель выбыла
        target.target_id = None  # сброс цели



        await message.answer(f"Код подтвержден! Вы успешно поймали цель {target.player_id}.")

        # Проверяем, осталось ли двое игроков
        remaining_players = await session.execute(
            select(GamePlayers).where(GamePlayers.game_id == active_game.id, GamePlayers.is_alive == True)
        )
        remaining_players = remaining_players.scalars().all()

        if len(remaining_players) == 2:
            # Два игрока остались, определяем победителя
            winner = max(remaining_players, key=lambda p: p.count_kills)
            await message.answer(
                f"Игра окончена! Победитель: {winner.player.username} с {winner.count_kills} убийствами!")

            # Получаем топ-3 игроков
            top_players = await session.execute(
                select(GamePlayers).where(GamePlayers.game_id == active_game.id)
                .order_by(GamePlayers.count_kills.desc())
            )
            top_players = top_players.scalars().all()

            # Формируем сообщение с топ-3 игроками
            top_message = "Топ 3 игрока:\n"
            for rank, top_player in enumerate(top_players[:3], start=1):
                top_message += f"{rank}. {top_player.player.username} - {top_player.count_kills} убийств\n"

            await message.answer(top_message)

            # Завершить игру
            active_game.is_active = False
            await session.commit()
    else:
        await state.clear()
        return message.answer("Неверный код. Попробуйте снова.")
    await session.commit()
    # Завершаем состояние
    await state.clear()

