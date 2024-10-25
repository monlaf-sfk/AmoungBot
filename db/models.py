from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, DateTime, func, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, timezone
from db.base import Base

utc_plus_5 = timezone(timedelta(hours=5))
class Player(Base):
    __tablename__ = "players"

    telegram_id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=True)
    is_registered = Column(Boolean, default=False)
    level = Column(Integer, default=1)
    winrate = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    date_register = Column(DateTime(timezone=True), default=datetime.now(utc_plus_5))

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
    role = Column(String, nullable=True)
    is_alive = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=lambda: datetime.now(utc_plus_5))

    game = relationship("Game", back_populates="players")
    player = relationship("Player", back_populates="games")


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