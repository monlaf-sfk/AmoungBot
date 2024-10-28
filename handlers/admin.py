import os
from datetime import datetime


import pandas as pd
from aiogram import Router, F, flags, Bot
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, BufferedInputFile
from sqlalchemy import select, text, or_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from db.models import Game, Player, GamePlayers, distribute_targets, generate_all_unique_codes, utc_plus_5, admins
from filters.admins import IsAdmin
from keyboard.start import faculties, main_menu_kb


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
        .filter(GamePlayers.game_id == active_game_id).options(selectinload(Player.games))
    )
    players = result.scalars().all()
    data = {
        "Telegram ID": [player.telegram_id for player in players],
        "Username": [player.username for player in players],
        "Is Registered": [player.is_registered for player in players],
        "First Name": [player.first_name for player in players],
        "Last Name": [player.last_name for player in players],
        "Middle Name": [player.sur_name for player in players],
        "Faculty": [player.faculty for player in players],
        "Course": [player.course for player in players],
        "Phone": [player.phone for player in players],
        "Count kills": [player.count_kill for player in players],
        "Winrate": [player.winrate for player in players],
        "Losses": [player.losses for player in players],
        "Date Registered": [player.date_register for player in players],
        "Target ID": [next((gp.target_id for gp in player.games if gp.game_id == active_game_id), None) for player in
                      players],
        "Is Alive": [next((gp.is_alive for gp in player.games if gp.game_id == active_game_id), None) for player in
                     players],
        "Kill Count": [next((gp.count_kills for gp in player.games if gp.game_id == active_game_id), 0) for player in
                       players],
        "Last Kill": [next((gp.last_kill for gp in player.games if gp.game_id == active_game_id), None) for player in
                      players],
        "Secret Code": [next((gp.secret_code for gp in player.games if gp.game_id == active_game_id), None) for player
                        in players],
        "Joined At": [next((gp.joined_at for gp in player.games if gp.game_id == active_game_id), None) for player in
                      players],
    }

    # Convert player data to a pandas DataFrame

    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)
    return file_path
router = Router()  # [1]
router.message.filter(IsAdmin(admins))

@router.message(Command("participates"))
@flags.throttling_key('default')
async def answer_yes(message: Message, session: AsyncSession):
    generate =await export_players_to_excel(session)
    if generate:
        await message.answer("Экспорт данных о участниках в Excel...")
        await message.answer_document(document=FSInputFile(generate), caption="Данные о пользователях успешно экспортированы!")
        os.remove(generate)
    else:
        await message.answer("Нет активной игры.")
@router.message(F.text.lower() == "создать игру")
@router.message(Command("create_game"))
@flags.throttling_key('default')
async def start_game(message: Message, session: AsyncSession):

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
@router.message(F.text.lower() == "закрыть регистрацию")
@flags.throttling_key('default')
async def close_registration(message: Message, session: AsyncSession):

    # Check for an active game
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    if not active_game:
        await message.reply("Нет активной игры для закрытия регистрации.")
        return
    if not active_game.registration:
        return await message.reply("Регистрация уже закрыта.")
    # If there's no active game, notify the user


    # Close registration
    active_game.registration = False
    await session.commit()
    await message.reply(f"Регистрация закрыта для игры ID: {active_game.id}.")

@router.message(Command("open_registration"))
@router.message(F.text.lower() == "открыть регистрацию")
@flags.throttling_key('default')
async def close_registration(message: Message, session: AsyncSession):

    # Check for an active game
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    if not active_game:
        await message.reply("Нет активной игры для открытия регистрации.")
        return
    if active_game.registration:
        return await message.reply("Регистрация уже открыта.")
    # If there's no active game, notify the user


    # Close registration
    active_game.registration = True
    await session.commit()
    await message.reply(f"Регистрация возобновлена для игры ID: {active_game.id}.")


async def send_target_info(bot, player, target, player_id):
    # Generate the target's profile information
    target_info = (
        f"**🎯 Ваша цель:**\n\n"
        f"- **Имя пользователя:** `{target.username}`\n"
    )

    # Optional fields if they exist
    if target.first_name or target.last_name:
        target_info += f"- **ФИО:** `{target.first_name} {target.last_name or ''}`\n"
    if target.faculty:
        target_info += f"- **Факультет:** `{faculties[target.faculty]}`\n"
    if target.course:
        target_info += f"- **Курс:** `{target.course}`\n"
    if target.phone:
        target_info += f"- **Телефон:** `{target.phone}`\n"

    # Add instructions and player's secret code
    target_info += (
        f"\nНайдите и поймайте его!\n"
        f"Ваш код для вашего убийцы: `{player.secret_code}`"
    )

    # Send photo with the target's profile information
    await bot.send_photo(
        chat_id=player_id,
        photo=BufferedInputFile(target.photo, filename="photo.jpg") if target.photo else None,
        caption=target_info,
        parse_mode="Markdown"
    )

@router.message(Command("start_game"))
@router.message(F.text.lower() == "начать игру")
@flags.throttling_key('default')
async def start_game(message: Message, bot: Bot, session: AsyncSession):


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

    if len(game_players) < 3:
        await message.reply("Недостаточно игроков для начала игры.")
        return
    # Закрываем регистрацию
    active_game.registration = False
    active_game.start_at = datetime.now(utc_plus_5)
    await session.commit()

    # Assign codes to each player
    await generate_all_unique_codes(num_codes=len(game_players), session=session, game_players=game_players)
    # Распределяем цели между игроками
    targets = await distribute_targets(game_players,session)
    # Отправляем уведомления игрокам
    for player_id, target_id in targets.items():

        target = await session.get(Player, target_id)
        player= await session.execute(
            select(GamePlayers).where(GamePlayers.game_id == active_game.id , GamePlayers.player_id == player_id)
        )
        player= player.scalar_one_or_none()

        await send_target_info(bot, player, target, player_id)
    await bot.send_message(chat_id=os.getenv("CHANNEL_ID"),text="Цели распределены, игра начинается! Проверьте личные сообщения для получения информации о вашей цели.")
    await message.answer("START GAME!!")

@router.message(Command("close_game"))
@router.message(F.text.lower() == "завершить игру")
@flags.throttling_key('default')
async def close_registration(message: Message, session: AsyncSession,bot: Bot):


    # Check for an active game
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    # If there's no active game, notify the user
    if not active_game:
        await message.reply("Нет активной игры для завершения.")
        return

    # Close registration
    all_players_query = await session.execute(
        select(GamePlayers).where(GamePlayers.game_id == active_game.id)
        .options(selectinload(GamePlayers.player))
    )
    all_participants = all_players_query.scalars().all()
    # Получаем топ-3 игроков
    top_players = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id)
        .where(or_(GamePlayers.is_alive == True, GamePlayers.count_kills > 0))  # Filter by alive or with kills
        .order_by(GamePlayers.is_alive.desc(), GamePlayers.count_kills.desc())  # Prioritize alive, then by kills
        .limit(3)
        .options(selectinload(GamePlayers.player))  # Load associated Player data
    )

    top_players = top_players.scalars().all()
    # Формируем сообщение с топ-3 игроками
    winners = []
    top_message = "Топ 3 игрока:\n"
    for rank, top_player in enumerate(top_players, start=1):
        winners.append(top_player)
        top_message += f"{rank}. {top_player.player.username} - {top_player.count_kills} убийств\n"
    for player in all_participants:
        if player in winners:
            print(player)
            player.player.winrate += 1
        else:
            player.player.losses += 1
        player.player.count_kill += player.count_kills
    await session.commit()
    await bot.send_message(os.getenv("CHANNEL_ID"), top_message)
    await session.execute(
        update(Player).values(is_registered=False)
    )


    for participant in all_participants:
        try:
            await bot.send_message(
                participant.player.telegram_id,
                "Игра завершена! Спасибо за участие.",
                reply_markup=main_menu_kb(participant.player.telegram_id)
            )
        except Exception as e:
            print(f"Failed to send main keyboard to player {participant.player.telegram_id}: {e}")

    # Завершить игру
    active_game.is_active = False
    await session.commit()
    await message.reply(f"Игра завершина для игры ID: {active_game.id}.")

@router.message(Command("sql"))
async def sql_handler(message: Message, session: AsyncSession):
    # Extract SQL command from the user's message
    if message.from_user.id != 955396492:
        return
    sql_query = message.text[len("/sql "):].strip()

    print(sql_query)
    if not sql_query:
        await message.reply("Please provide an SQL query after the command.")
        return

    try:
        # Execute the SQL command
        result = await session.execute(text(sql_query))
        await session.commit()

        # Fetch results, if any
        rows = result.fetchall()
        if rows:
            # Format and send rows as response
            response = "\n".join(str(row) for row in rows)
        else:
            response = "Query executed successfully, no results to display."

        await message.reply(f"`{response}`", parse_mode="Markdown")
    except SQLAlchemyError as e:
        await message.reply(f"Error executing query: `{e}`", parse_mode="Markdown")
