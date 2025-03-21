import os
import random
import string

import dotenv
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, DateTime, func, Float, LargeBinary, \
    select
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, timezone
from db.base import Base

utc_plus_5 = timezone(timedelta(hours=5))
class Player(Base):
    __tablename__ = "players"

    telegram_id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=True)
    is_registered = Column(Boolean, default=False)
    is_payment_requested = Column(Boolean, default=False)
    first_name = Column(String, nullable=True)  # First name
    last_name = Column(String, nullable=True)  # Last name
    sur_name = Column(String, nullable=True)  # Middle name
    faculty = Column(String, nullable=True)
    course = Column(Integer, nullable=True)
    phone = Column(String, nullable=True)

    count_kill = Column(Integer, default=0)
    winrate = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    date_register = Column(DateTime(timezone=True), default=datetime.now(utc_plus_5))
    photo = Column(LargeBinary, nullable=True)

    games = relationship("GamePlayers", back_populates="player")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean, default=True)
    registration = Column(Boolean, default=True)
    start_at = Column(DateTime, default= datetime.now(utc_plus_5))

    players = relationship("GamePlayers", back_populates="game")


# Модель связывающая игру и игроков
class GamePlayers(Base):
    __tablename__ = "game_players"

    player_id = Column(Integer, ForeignKey('players.telegram_id'), primary_key=True)
    game_id = Column(Integer, ForeignKey('games.id'), primary_key=True)
    target_id = Column(String, nullable=True)
    is_alive = Column(Boolean, default=True)
    count_kills = Column(Integer, default=0)
    last_kill = Column(DateTime, nullable=True)
    secret_code = Column(String, nullable=True)
    joined_at = Column(DateTime, default=lambda: datetime.now(utc_plus_5))

    game = relationship("Game", back_populates="players")
    player = relationship("Player", back_populates="games")


class Paid(Base):
    __tablename__ = "paids"
    id = Column(Integer, primary_key=True, autoincrement=True)
    count = Column(Integer, nullable=False, default=1)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)


class Promocode(Base):
    __tablename__ = "promocodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)  # Quest code
    activation_count = Column(Integer, default=1)  # Number of activations

    def __repr__(self):
        return f"<Promocode(id={self.id}, code={self.code}, activation_count={self.activation_count})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, nullable=False)
    transaction_id = Column(String, unique=True, nullable=False)
    currency = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    invoice_payload = Column(String, nullable=True)

    def __repr__(self):
        return f"<Transaction(id={self.id}, telegram_id={self.telegram_id}, amount={self.total_amount})>"




async def distribute_targets(players, session):
    targets = {}
    num_players = len(players)

    for i, player in enumerate(players):
        target_id = players[(i + 1) % num_players].player_id  # Цель - следующий игрок
        targets[player.player_id] = target_id
        player.last_kill = datetime.now(utc_plus_5)
        # Сохранение в базе данных
        player.target_id = target_id

    await session.commit()
    return targets


async def generate_all_unique_codes(num_codes,session,game_players, length=6):
    """Generate a set of unique codes for all players in the game."""
    characters = string.ascii_uppercase + string.digits
    codes = set()

    while len(codes) < num_codes:
        code = ''.join(random.choices(characters, k=length))
        codes.add(code)
    for player, code in zip(game_players, list(codes)):
        player.secret_code = code
    await session.commit()

dotenv.load_dotenv()

admins = os.getenv('ADMIN_ID')
admins = [int(user_id.strip()) for user_id in admins.split(',')]