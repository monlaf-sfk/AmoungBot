import os

import pandas as pd
from aiogram import Router, F, flags, Bot
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, BufferedInputFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Game, Player, GamePlayers, distribute_targets, generate_all_unique_codes


async def export_players_to_excel(session: AsyncSession, file_path: str = "players.xlsx"):
    active_game_result = await session.execute(
        text("SELECT id FROM games WHERE is_active = true")
    )
    active_game_id = active_game_result.scalar_one_or_none()

    if not active_game_id:
        print("No active game found.")
        return None

    # Query players in the active game
    result = await session.execute(
        select(Player)
        .join(GamePlayers, Player.telegram_id == GamePlayers.player_id)
        .filter(GamePlayers.game_id == active_game_id)
    )
    players = result.scalars().all()

    # Convert player data to a pandas DataFrame
    data = {
        "Telegram ID": [player.telegram_id for player in players],
        "Username": [player.username for player in players],
        "Is Registered": [player.is_registered for player in players],
        "Level": [player.level for player in players],
        "Winrate": [player.winrate for player in players],
        "Losses": [player.losses for player in players],
        "Date Registered": [player.date_register for player in players],
    }

    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)
    return file_path
router = Router()  # [1]

@router.message(Command("participates"))
@flags.throttling_key('default')
async def answer_yes(message: Message, session: AsyncSession):
    if message.from_user.id != int(os.getenv("ADMIN_ID")):
        await message.reply("У вас нет прав.")
        return
    generate =await export_players_to_excel(session)
    if generate:
        await message.answer("Экспорт данных о участниках в Excel...")
        await message.answer_document(document=FSInputFile(generate), caption="Данные о пользователях успешно экспортированы!")
        os.remove(generate)
    else:
        await message.answer("Нет активной игры.")

@router.message(Command("create_game"))
@flags.throttling_key('default')
async def start_game(message: Message, session: AsyncSession):
    if message.from_user.id != int(os.getenv("ADMIN_ID")):
        await message.reply("У вас нет прав для создания игры.")
        return
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()


    if active_game:
        await message.reply(f"Игра уже начата! ID активной игры: {active_game.id}")
        return
    game = Game(registration=True, is_active=True)
    session.add(game)
    await session.commit()
    await message.reply(f"Новая игра начата! ID игры: {game.id}")


@router.message(Command("close_registration"))
@flags.throttling_key('default')
async def close_registration(message: Message, session: AsyncSession):
    if message.from_user.id != int(os.getenv("ADMIN_ID")):
        await message.reply("У вас нет прав для закрытия регистрации.")
        return

    # Check for an active game
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    if not active_game.registration:
        return await message.reply("Регистрация уже закрыта.")
    # If there's no active game, notify the user
    if not active_game:
        await message.reply("Нет активной игры для закрытия регистрации.")
        return

    # Close registration
    active_game.registration = False
    await session.commit()
    await message.reply(f"Регистрация закрыта для игры ID: {active_game.id}.")

@router.message(Command("open_registration"))
@flags.throttling_key('default')
async def close_registration(message: Message, session: AsyncSession):
    if message.from_user.id != int(os.getenv("ADMIN_ID")):
        await message.reply("У вас нет прав для закрытия регистрации.")
        return

    # Check for an active game
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    if active_game.registration:
        return await message.reply("Регистрация уже открыта.")
    # If there's no active game, notify the user
    if not active_game:
        await message.reply("Нет активной игры для открытия регистрации.")
        return

    # Close registration
    active_game.registration = True
    await session.commit()
    await message.reply(f"Регистрация возобновлена для игры ID: {active_game.id}.")

@router.message(Command("start_game"))
@flags.throttling_key('default')
async def start_game(message: Message, bot: Bot, session: AsyncSession):
    if message.from_user.id != int(os.getenv("ADMIN_ID")):
        await message.reply("У вас нет прав для создания игры.")
        return

    # Проверяем, есть ли активная игра
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()

    if active_game is None:
        await message.reply("Нет активной игры для начала.")
        return
        # Получаем всех игроков, зарегистрированных в текущей игре
    game_players = await session.execute(
        select(GamePlayers)
        .join(Player, Player.telegram_id == GamePlayers.player_id)
        .filter(GamePlayers.game_id == active_game.id)
    )

    game_players = game_players.scalars().all()
    print(game_players)
    if len(game_players) < 2:
        await message.reply("Недостаточно игроков для начала игры.")
        return
    # Закрываем регистрацию
    active_game.registration = False

    await generate_all_unique_codes(num_codes=len(game_players), session=session , game_players=game_players)

    # Assign codes to each player

    await session.commit()
    # Распределяем цели между игроками
    targets = await distribute_targets(game_players,session)
    # Отправляем уведомления игрокам
    for player_id, target_id in targets.items():

        target = await session.get(Player, target_id)
        player= await session.execute(
            select(GamePlayers).where(GamePlayers.game_id == active_game.id , GamePlayers.player_id == player_id)
        )
        player= player.scalar_one_or_none()

        await bot.send_photo(
            chat_id=player_id,
            caption=f"Ваша цель — игрок {target.username}. Найдите и поймайте его!\n"
                    f"Ващ код для вашего убийцы {player.secret_code}",photo=BufferedInputFile(target.photo, filename="photo.jpg")
        )
    await message.reply("Цели распределены, игра начинается! Проверьте личные сообщения для получения информации о вашей цели.")
