from aiogram import Router, F, flags, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.types import PreCheckoutQuery , ContentType, LabeledPrice


import os

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Player, GamePlayers, Game, Transaction

router = Router()

@router.message(Command("register"))
@flags.throttling_key('default')
async def cmd_start(message: Message, session: AsyncSession):
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    if not active_game:
        await message.reply("Нет активной игры. Попросите администратора создать игру.")
        return
    if active_game.registration == False and active_game.is_active == True:
        await message.reply("Регистрация на игру закрыта.")
        return

    player = await session.get(Player, message.from_user.id)
    if not player:
        player = Player(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            is_registered=False
        )
        session.add(player)
        await session.commit()
    if player.is_registered:
        await message.answer("Вы уже зарегистрированы!")
        return
    PAYMENTS_TOKEN = os.getenv("PAYMENTS_TOKEN")
    PRICE = [LabeledPrice(label="Билет для участия", amount=50000)]
    await message.answer_invoice(
               title="Билет",
               description="Билет для участия в мероприятии",
               provider_token=PAYMENTS_TOKEN,
               currency="kzt",
               photo_url="https://files.oaiusercontent.com/file-fjb4lc3Et55C1DUa6zNq2a96?se=2024-10-24T22%3A51%3A55Z&sp=r&sv=2024-08-04&sr=b&rscc=max-age%3D604800%2C%20immutable%2C%20private&rscd=attachment%3B%20filename%3D58e4533e-9498-4cea-b52a-7e34b96807fb.webp&sig=jSOYdWsA24uII%2BO2weGJrCoBkE7fgcM7ztnK3EFUOQA%3D",
               photo_width=416,
               photo_height=234,
               photo_size=416,
               is_flexible=False,
               prices=PRICE,
               start_parameter="one-month-subscription",
               payload="test-invoice-payload")

@router.pre_checkout_query(lambda q: True)
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery, bot: Bot, session: AsyncSession):
    player = await session.get(Player, pre_checkout_q.from_user.id)

    if player.is_registered:
        await pre_checkout_q.answer(ok=False, error_message="Вы уже зарегистрированы!")
        return
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    if not active_game:
        await pre_checkout_q.answer(ok=False, error_message="Нет активной игры. Попросите администратора создать игру.")

        return
    if active_game.registration == False and active_game.is_active == True:
        await pre_checkout_q.answer(ok=False, error_message="Регистрация на игру закрыта.")
        return

    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


# successful payment
@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot ,session: AsyncSession):
    payment_info = message.successful_payment

    player = await session.get(Player, message.from_user.id)

    player.is_registered = True

    active_game = await session.execute(
        select(Game).where(Game.registration == True)
    )
    active_game = active_game.scalar_one_or_none()

    game_player = GamePlayers(
        game_id=active_game.id,
        player_id=player.telegram_id,
        role=None,
        is_alive=True
    )
    transaction = Transaction(
        telegram_id=message.from_user.id,
        transaction_id=payment_info.telegram_payment_charge_id,
        currency=payment_info.currency,
        total_amount=payment_info.total_amount / 100,  # Adjust for cents if needed
        status="success",
        invoice_payload=payment_info.invoice_payload
    )
    session.add(transaction)
    session.add(game_player)
    await session.commit()
    await message.reply(f"Вы присоединились к игре {active_game.id}!")

