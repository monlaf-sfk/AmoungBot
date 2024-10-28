import os
from datetime import datetime

from aiogram import Bot, Router, F, flags
from aiogram.filters import Command
from aiogram.types import  BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from aiogram import types
from db.models import Player, GamePlayers, Game
from db.schedualer import INACTIVITY_THRESHOLD, utc_plus_5
from keyboard.start import main_menu_kb, game_kb, faculties

router = Router()


class HuntState(StatesGroup):
    waiting_for_code = State()


# Шаг 1: Команда для инициации подтверждения убийства
@router.message(Command("kill"))
@router.message(F.text.lower() == "убить")
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
    await message.answer("Введите код вашей цели для подтверждения убийства:")
    await state.set_state(HuntState.waiting_for_code)


# Шаг 2: Обработчик состояния для проверки кода
@router.message(HuntState.waiting_for_code)
@flags.throttling_key('default')
async def confirm_kill(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
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
        select(GamePlayers).where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == target_player_id).options(selectinload(GamePlayers.player))
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
        target.player.is_registered = False
        try:
            await bot.send_message(
                target.player.telegram_id,
                "Вас поймали!",
                reply_markup=main_menu_kb(target.player.telegram_id)
            )
        except Exception as e:
            print(f"Failed to send main keyboard to player {target.player.telegram_id}: {e}")
        await session.commit()
        await message.answer(f"Код подтвержден! Вы успешно поймали цель {target.player_id}.")
        await bot.send_message(os.getenv("CHANNEL_LOGS"), f"Игрок {player.player_id} поймал цель {target.player_id}!")
        # Проверяем, осталось ли двое игроков
        remaining_players_result = await session.execute(
            select(GamePlayers)
            .where(GamePlayers.game_id == active_game.id, GamePlayers.is_alive == True)
            .options(selectinload(GamePlayers.player))  # Eagerly load related 'player' model
        )
        remaining_players = remaining_players_result.scalars().all()

        if len(remaining_players) <= 2:
            # Два игрока остались, определяем победителя
            winner = max(remaining_players, key=lambda p: p.count_kills)
            await bot.send_message(os.getenv("CHANNEL_ID"),
                f"Игра окончена! Победитель: {winner.player.username} с {winner.count_kills} убийствами!")

            # Получаем топ-3 игроков
            top_players = await session.execute(
                select(GamePlayers)
                .where(GamePlayers.game_id == active_game.id)
                .where(or_(GamePlayers.is_alive == True, GamePlayers.count_kills > 0))  # Filter by alive or with kills
                .order_by(GamePlayers.is_alive.desc(),
                          GamePlayers.count_kills.desc())  # Prioritize alive, then by kills
                .limit(3)
                .options(selectinload(GamePlayers.player))  # Load associated Player data
            )

            top_players = top_players.scalars().all()
            all_players_query = await session.execute(
                select(GamePlayers).where(GamePlayers.game_id == active_game.id)
                .options(selectinload(GamePlayers.player))
            )
            all_participants = all_players_query.scalars().all()
            # Формируем сообщение с топ-3 игроками
            winners = []
            top_message = "Топ 3 игрока:\n"
            for rank, top_player in enumerate(top_players, start=1):
                winners.append(top_player)
                top_message += f"{rank}. {top_player.player.username} - {top_player.count_kills} убийств\n"
            for player in all_participants:
                if player in winners:
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
        else:
            target = await session.get(Player, player.target_id)

            await bot.send_photo(
                chat_id=message.from_user.id,
                caption=f"Ваша цель — игрок {target.username}. Найдите и поймайте его!\n",
                photo=BufferedInputFile(target.photo, filename="photo.jpg")
            )



    else:
        await state.clear()
        return message.answer("Неверный код. Попробуйте снова.")
    await session.commit()
    # Завершаем состояние
    await state.clear()




@router.message(Command("info"))
@router.message(F.text.lower() == "информация по игре")
@flags.throttling_key('default')
async def game_info_handler(message: types.Message, session: AsyncSession):
    # Find active game

    active_game = await session.execute(
        select(Game).where(Game.registration == False, Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()

    if not active_game:
        await message.answer("Нет активной игры.")

        return
    # Get player info
    player = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == message.from_user.id)
        .options(selectinload(GamePlayers.player))
    )
    player = player.scalar_one_or_none()

    if not player:
        await message.answer("Вы не участвуете в текущей игре.")
        return

    # Live player count
    live_players = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id, GamePlayers.is_alive == True)
    )
    live_players_count = live_players.scalars().all()

    # Current target's username
    target = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == player.target_id)
        .options(selectinload(GamePlayers.player))
    )
    target = target.scalar_one_or_none()


    # Top killers (top 3)
    top_killers_result = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id)
        .order_by(GamePlayers.count_kills.desc())
        .limit(3)
        .options(selectinload(GamePlayers.player))
    )
    top_killers = top_killers_result.scalars().all()

    # Format top killers list
    top_killers_message = "Топ убийц:\n"
    for rank, top_player in enumerate(top_killers, start=1):
        top_killers_message += f"{rank}. {top_player.player.username} - {top_player.count_kills} убийств\n"

    # Message format


    target_info = (
        f"**🎯 Ваша цель:**\n\n"
        f"- **Имя пользователя:** `{target.player.username}`\n"
    )
    # Calculate remaining time until kick

    last_kill_time = player.last_kill
    if last_kill_time and last_kill_time.tzinfo is None:
        last_kill_time = last_kill_time.replace(tzinfo=utc_plus_5)
    now = datetime.now(utc_plus_5)

    time_since_last_kill = now - last_kill_time
    time_until_kick = INACTIVITY_THRESHOLD - time_since_last_kill

    # Format the remaining time
    if time_until_kick.total_seconds() > 0:
        days = time_until_kick.days
        hours, remainder = divmod(time_until_kick.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        countdown_text = f"{days} дн {hours} ч {minutes} мин"
    else:
        countdown_text = "Исключение скоро произойдет!"

    # Append countdown to profile info
    target_info += f"- **До исключения:** `{countdown_text}`\n"
    # Optional fields if they exist
    if target.player.first_name or target.player.last_name:
        target_info += f"- **ФИО:** `{target.player.first_name} {target.player.last_name or ''}`\n"
    if target.player.faculty:
        target_info += f"- **Факультет:** `{faculties[target.player.faculty]}`\n"
    if target.player.course:
        target_info += f"- **Курс:** `{target.player.course}`\n"
    if target.player.phone:
        target_info += f"- **Телефон:** `{target.player.phone}`\n"
    target_info+=(f"Ваш код: {player.secret_code}\n"
    f"Игроков в живых: {len(live_players_count)}\n\n"
    f"{top_killers_message}")
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Показать фото цели",
        callback_data="show_target_photo")
    )

    # Send message
    await message.answer(target_info,parse_mode="Markdown" ,reply_markup=builder.as_markup())

@router.callback_query(F.data == "show_target_photo")
async def show_target_photo(callback_query: types.CallbackQuery, session: AsyncSession):
    # Retrieve active game and player info
    active_game = await session.execute(
        select(Game).where(Game.registration == False, Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()

    if not active_game:
        await callback_query.message.answer("Нет активной игры.")
        return

    player = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == callback_query.from_user.id)
        .options(selectinload(GamePlayers.player))
    )
    player = player.scalar_one_or_none()

    if not player:
        await callback_query.message.answer("Вы не участвуете в текущей игре.")
        return

    # Fetch target player and send photo if available
    target_player = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == player.target_id)
        .options(selectinload(GamePlayers.player))
    )
    target_player = target_player.scalar_one_or_none()

    if target_player and target_player.player.photo:
        await callback_query.message.answer_photo(photo=BufferedInputFile(target_player.player.photo, filename="photo.jpg"), caption=f"Фото вашей цели: {target_player.player.username}")
    else:
        await callback_query.message.answer("Фото цели недоступно.")





@router.message(Command("exit"))
@router.message(F.text.lower() == "назад")
@flags.throttling_key('default')
async def exit_game(message: types.Message, session: AsyncSession):
    await message.answer(text="Меню:", reply_markup=main_menu_kb(message.from_user.id))



@router.message(Command("current_game"))
@router.message(F.text.lower() == "текущая игра")
@flags.throttling_key('default')
async def current_game_info_handler( message: types.Message, session: AsyncSession, bot: Bot):
    # Fetch active game
    active_game_query = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game_query.scalar_one_or_none()

    if not active_game:
        await bot.send_message(message.chat.id, "Нет активной игры.")
        return
    if active_game.registration:
        await message.answer("Регистрация еще не завершена.")
        return
    player = await session.execute(
        select(GamePlayers)
        .where(GamePlayers.game_id == active_game.id, GamePlayers.player_id == message.from_user.id)
        .options(selectinload(GamePlayers.player))
    )
    player = player.scalar_one_or_none()

    if not player:
        await message.answer("Вы не участвуете в текущей игре.")
        return
    if not player.is_alive:
        await bot.send_message(message.chat.id, "Вы выбыли из игры.")
        return
    # Fetch players in the active game
    players_query = await session.execute(
        select(GamePlayers).where(GamePlayers.game_id == active_game.id).options(selectinload(GamePlayers.player))
    )
    players = players_query.scalars().all()

    # Calculate live players count
    live_players = [player for player in players if player.is_alive]
    live_count = len(live_players)

    # Get top killers
    top_killers = sorted(live_players, key=lambda p: p.count_kills, reverse=True)[:3]

    # Prepare the progress bar
    total_players = len(players)
    progress_bar_length = 20  # Length of the progress bar in characters
    progress = int((live_count / total_players) * progress_bar_length) if total_players > 0 else 0
    progress_bar = '█' * progress + '░' * (progress_bar_length - progress)

    # Construct the message
    message_text = f"**Текущая игра**\n\n"
    message_text += f"🔹 **Живые игроки:** {live_count}/{total_players}\n"
    message_text += f"🔹 **Прогресс игры:** [{progress_bar}] {live_count}/{total_players}\n\n"
    message_text += f"🔹 **Топ убийц:**\n"

    for rank, player in enumerate(top_killers, start=1):
        message_text += f"{rank}. {player.player.username} - {player.count_kills} убийств\n"

    if not top_killers:
        message_text += "Нет убийц.\n"

    await bot.send_message(message.chat.id, message_text, parse_mode='Markdown',reply_markup=game_kb())
