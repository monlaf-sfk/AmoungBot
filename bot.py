import asyncio
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
import os
import dotenv
import logging

from aiogram.types import BotCommand, BotCommandScopeDefault

from db.base import Base
from db.schedualer import start_scheduler
from handlers import start, buy, admin, game, support
from middlewares.db import DbSessionMiddleware
from middlewares.throttling import ThrottlingMiddleware, ThrottlingCallMiddleware

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

dotenv.load_dotenv()



logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
async def set_commands(bot: Bot):
    commands = [BotCommand(command='start', description='Старт '),
                BotCommand(command='register', description='Регистрация'),
                BotCommand(command='set_photo', description='Установить фото'),
                BotCommand(command='set_faculty', description='Указать факультет'),
                BotCommand(command='set_name', description='Указать имя'),
                BotCommand(command='kill', description='Убить'),
                BotCommand(command='info', description='Информация'),
                BotCommand(command='current_game', description='Текущая игра'),
                BotCommand(command='exit', description='Назад'),]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    await set_commands(bot)
    engine = create_async_engine(url=os.getenv("DB_URL"), echo=True )
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)

    await start_scheduler(bot, sessionmaker)

    log_folder = Path("assets")
    log_folder.mkdir(parents=True, exist_ok=True)

    # Configure logging for SQLAlchemy
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.INFO)

    # Set up the file handler for daily rotation
    log_file_path = log_folder / "sql_queries.log"
    file_handler = TimedRotatingFileHandler(log_file_path, when="midnight", interval=1)
    file_handler.suffix = "%Y-%m-%d"  # Add date to each log file name
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    sqlalchemy_logger.addHandler(file_handler)


    dp.update.middleware(DbSessionMiddleware(session_pool=sessionmaker))
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(game.router)
    dp.include_router(buy.router)
    dp.include_router(support.router)
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingCallMiddleware())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())