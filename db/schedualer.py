import asyncio
import os
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import or_, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from aiogram import Bot
from sqlalchemy.orm import selectinload

from db.models import Game, GamePlayers, Player
from keyboard.start import main_menu_kb

utc_plus_5 = timezone(timedelta(hours=5))  # Adjust to your timezone

# Inactivity threshold: 3 days
INACTIVITY_THRESHOLD = timedelta(days=3)


async def check_inactive_players(bot: Bot, session: AsyncSession):
    now = datetime.now(utc_plus_5)

    # Fetch active games
    active_games_query = await session.execute(select(Game).where(Game.is_active == True, Game.registration == False))
    active_game = active_games_query.scalar_one_or_none()

    if not active_game:
        return  # Exit if there are no active games

    # Fetch players in the active game
    players_query = await session.execute(
        select(GamePlayers).where(GamePlayers.game_id == active_game.id, GamePlayers.is_alive == True).options(selectinload(GamePlayers.player))
    )
    players = players_query.scalars().all()

    for player in players:
        last_kill_time = player.last_kill
        if last_kill_time and last_kill_time.tzinfo is None:
            last_kill_time = last_kill_time.replace(tzinfo=utc_plus_5)

        # Check if player has been inactive
        if last_kill_time and (now - last_kill_time) > INACTIVITY_THRESHOLD:
            # Mark player as inactive and reassign targets
            previous_player_query = await session.execute(
                select(GamePlayers)
                .where(GamePlayers.target_id == player.player_id, GamePlayers.game_id == active_game.id)
            )
            previous_player = previous_player_query.scalar_one_or_none()

            # If there's a previous player in the sequence, assign their target to the inactive player's target
            if previous_player:
                previous_player.target_id = player.target_id

            player.is_alive = False
            player.target_id = None
            player.player.is_registered = False
            # Mark player as unregistered
            await session.commit()

            # Notify the removed player
            try:
                await bot.send_message(player.player_id, "Вы были исключены из игры из-за неактивности.",reply_markup=main_menu_kb(player.player_id))
            except Exception as e:
                print(f"Failed to notify player {player.player_id}: {e}")

    # Check remaining players to determine game end
            remaining_players_result = await session.execute(
                select(GamePlayers)
                .where(GamePlayers.game_id == active_game.id, GamePlayers.is_alive == True)
                .options(selectinload(GamePlayers.player))  # Eagerly load related 'player' model
            )
            remaining_players = remaining_players_result.scalars().all()

            if len(remaining_players) <= 2:
                # If two or fewer players remain, determine the winner
                winner = max(remaining_players, key=lambda p: p.count_kills)

                await bot.send_message(os.getenv("CHANNEL_ID"),
                                       f"Игра окончена! Победитель: {winner.player.username} с {winner.count_kills} убийствами!")

                # Get the top-3 players based on kills
                top_players = await session.execute(
                    select(GamePlayers)
                    .where(GamePlayers.game_id == active_game.id)
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
                # Compose message for top-3 players
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

                # Reset player registration statuses
                await session.execute(update(Player).values(is_registered=False))
                # Mark game as inactive
                active_game.is_active = False
                await session.commit()


                for participant in all_participants:
                    try:
                        await bot.send_message(
                            participant.player.telegram_id,
                            "Игра завершена! Спасибо за участие.",
                            reply_markup=main_menu_kb(participant.player.telegram_id)
                        )
                    except Exception as e:
                        print(f"Failed to send main keyboard to player {participant.player.telegram_id}: {e}")

                break




async def start_scheduler(bot: Bot , session_pool: async_sessionmaker):
    async with session_pool() as session:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(check_inactive_players, 'cron', minute='*', misfire_grace_time=1000,args=[bot, session])
        scheduler.start()


# Start the scheduler when bot starts

