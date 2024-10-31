from aiogram import Router, F, flags, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.types import PreCheckoutQuery , LabeledPrice


import os

from aiogram.utils.keyboard import InlineKeyboardBuilder
from numpy.ma.core import count
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Player, GamePlayers, Game, admins, Paid
from filters.admins import IsAdmin
from filters.chat_type import ChatTypeFilter
from keyboard.start import main_menu_kb, cancel_kb, faculties
from state.registr import PaidState

router = Router()
router.message.filter(ChatTypeFilter(chat_type="private"))
# @router.message(F.text.lower() == "регистрация на игру")
# @router.message(Command("register"))
# @flags.throttling_key('default')
# async def cmd_start(message: Message, session: AsyncSession):
#     active_game = await session.execute(
#         select(Game).where(Game.is_active == True)
#     )
#     active_game = active_game.scalar_one_or_none()
#     if not active_game:
#         await message.reply("Нет активной игры. Попросите администратора создать игру.")
#         return
#     if active_game.registration == False and active_game.is_active == True:
#         await message.reply("Регистрация на игру закрыта.")
#         return
#
#     player = await session.get(Player, message.from_user.id)
#     if not player:
#         player = Player(
#             telegram_id=message.from_user.id,
#             username=message.from_user.username,
#             is_registered=False
#         )
#         session.add(player)
#         await session.commit()
#     if player.is_registered:
#         await message.answer("Вы уже зарегистрированы!")
#         return
#     if not player.photo:
#         return await message.answer("Установите фото для участья в игре. /set_photo")
#     if not player.first_name or not player.last_name:
#         return await message.answer("Установите ФИО для участья в игре. /set_name")
#     if not player.faculty:
#         return await message.answer("Установите факультет для участья в игре. /set_faculty")
#     if not player.course:
#         return await message.answer("Установите курс для участья в игре. /set_course")
#
#     PAYMENTS_TOKEN = os.getenv("PAYMENTS_TOKEN")
#     PRICE = [LabeledPrice(label="Билет для участия", amount=50000)]
#     await message.answer_invoice(
#                title="Билет",
#                description="Билет для участия в мероприятии",
#                provider_token=PAYMENTS_TOKEN,
#                currency="kzt",
#                photo_url="https://files.oaiusercontent.com/file-fjb4lc3Et55C1DUa6zNq2a96?se=2024-10-24T22%3A51%3A55Z&sp=r&sv=2024-08-04&sr=b&rscc=max-age%3D604800%2C%20immutable%2C%20private&rscd=attachment%3B%20filename%3D58e4533e-9498-4cea-b52a-7e34b96807fb.webp&sig=jSOYdWsA24uII%2BO2weGJrCoBkE7fgcM7ztnK3EFUOQA%3D",
#                photo_width=416,
#                photo_height=234,
#                photo_size=416,
#                is_flexible=False,
#                prices=PRICE,
#                start_parameter="one-month-subscription",
#                payload="test-invoice-payload")
#
# @router.pre_checkout_query(lambda q: True)
# async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery, bot: Bot, session: AsyncSession):
#     player = await session.get(Player, pre_checkout_q.from_user.id)
#
#     if player.is_registered:
#         await pre_checkout_q.answer(ok=False, error_message="Вы уже зарегистрированы!")
#         return
#     active_game = await session.execute(
#         select(Game).where(Game.is_active == True)
#     )
#     active_game = active_game.scalar_one_or_none()
#     if not active_game:
#         await pre_checkout_q.answer(ok=False, error_message="Нет активной игры. Попросите администратора создать игру.")
#
#         return
#     if active_game.registration == False and active_game.is_active == True:
#         await pre_checkout_q.answer(ok=False, error_message="Регистрация на игру закрыта.")
#         return
#
#     await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
#
#
# # successful payment
# @router.message(F.successful_payment)
# async def successful_payment(message: Message, bot: Bot ,session: AsyncSession):
#     payment_info = message.successful_payment
#
#     player = await session.get(Player, message.from_user.id)
#
#     player.is_registered = True
#
#     active_game = await session.execute(
#         select(Game).where(Game.registration == True, Game.is_active == True)
#     )
#     active_game = active_game.scalar_one_or_none()
#
#     game_player = GamePlayers(
#         game_id=active_game.id,
#         player_id=player.telegram_id,
#         is_alive=True
#     )
#     transaction = Transaction(
#         telegram_id=message.from_user.id,
#         transaction_id=payment_info.telegram_payment_charge_id,
#         currency=payment_info.currency,
#         total_amount=payment_info.total_amount / 100,  # Adjust for cents if needed
#         status="success",
#         invoice_payload=payment_info.invoice_payload
#     )
#     session.add(transaction)
#     session.add(game_player)
#     await session.commit()
#     await message.reply(f"Вы присоединились к игре {active_game.id}!")
@router.message(F.text.lower() == "регистрация на игру 👾")
@router.message(Command("register"))
@flags.throttling_key('default')
async def set_photo(message: Message, session: AsyncSession):
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
    if not player.photo:
        return await message.answer("Установите фото для участья в игре. /set_photo")
    if not player.first_name or not player.last_name:
        return await message.answer("Установите ФИО для участья в игре. /set_name")
    if not player.faculty:
        return await message.answer("Установите факультет для участья в игре. /set_faculty")
    if not player.course:
        return await message.answer("Установите курс для участья в игре. /set_course")
    if player.is_payment_requested:
        await message.answer("Ваша заявка на регистрацию уже отправлена. Ожидайте ответа.")
        return
    paid_query = await session.execute(
        select(Paid).where(Paid.game_id == active_game.id)
    )
    paid = paid_query.scalar_one_or_none()
    if paid:
        paid.count += 1
    else:
        paid = Paid(
            count=1,
            game_id=active_game.id
        )
        session.add(paid)
    builder = InlineKeyboardBuilder()
    # Add buttons for missing information

    builder.row(InlineKeyboardButton(text="Оплатил", callback_data=f"paid:{paid.count}"),)


    await session.commit()
    await message.answer("Пожалуйста, оплатите билет для участия в игре. \n"
                         "Стоимость билета - 5000 тенге. \n"
                         "Отправьте на номер : xxxxxxx\n"
                         f"С цифрой в комментарий:  {paid.count}\n"
                         "После оплаты нажмите кнопку 'Оплатил'", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("paid"))
@flags.throttling_key('default')
async def set_photo(call: CallbackQuery,state: FSMContext, session: AsyncSession, bot: Bot):
    count = call.data.split(":")[1]
    player = await session.get(Player, call.from_user.id)
    if player.is_payment_requested:
        await call.message.edit_text("Ваша заявка на регистрацию уже отправлена. Ожидайте ответа.")
        return
    if player.is_registered:
        await call.message.edit_text("Вы уже зарегистрированы!")
        return
    active_game = await session.execute(
        select(Game).where(Game.is_active == True)
    )
    active_game = active_game.scalar_one_or_none()
    if not active_game:
        await call.message.edit_text("Нет активной игры. Попросите администратора создать игру.")

        return
    if active_game.registration == False and active_game.is_active == True:
        await call.message.edit_text("Регистрация на игру закрыта.")
        return
    await call.message.answer("Отправьте фото чека об оплате. (фото)", reply_markup=cancel_kb())
    await call.message.delete_reply_markup()
    await state.update_data(count=count)
    await state.set_state(PaidState.recipt)
@router.message(F.text.lower() == "отмена", StateFilter(PaidState))
async def cancel_registration(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Регистрация отменена.", reply_markup=main_menu_kb(message.from_user.id))
@router.message(PaidState.recipt , F.photo)
@flags.throttling_key('default')
async def set_photo(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    player = await session.get(Player, message.from_user.id)
    player.is_payment_requested = True
    await session.commit()
    file_path = await message.bot.download(file=message.photo[-1].file_id)
    await message.answer("Ожидайте подтверждения оплаты.", reply_markup=main_menu_kb(message.from_user.id))
    builder = InlineKeyboardBuilder()
    # Add buttons for missing information


    builder.row(InlineKeyboardButton(text="Оплатил", callback_data=f"check_paid:yes:{message.from_user.id}"),
                InlineKeyboardButton(text="Не оплатил", callback_data=f"check_paid:no:{message.from_user.id}"))

    data = await state.get_data()
    count = data.get("count")
    player = await session.get(Player, message.from_user.id)

    if player:
        # Format the player's information
        player_info = (
            f"**👤 Информация об игроке:**\n\n"
            f"- **Имя пользователя:** `{player.username}`\n"
            f"- **Количество убийств:** `{player.count_kill}`\n"
            f"- **Победы:** `{player.winrate}`\n"
            f"- **Поражения:** `{player.losses}`\n"
            f"- **Дата регистрации:** `{player.date_register}`\n\n"
        )

        # Add optional fields if they exist
        if player.first_name or player.last_name:
            player_info += f"- **ФИО:** `{player.first_name} {player.sur_name or ''} {player.last_name}`\n"
        if player.faculty:
            player_info += f"- **Факультет:** `{faculties[player.faculty]}`\n"
        if player.course:
            player_info += f"- **Курс:** `{player.course}`\n"
        if player.phone:
            player_info += f"- **Телефон:** `{player.phone}`\n"

    await bot.send_photo(os.getenv("CHAT_SUPPORT"), photo=BufferedInputFile(file_path.read(), filename="photo.jpg"),caption=f"Запрос на оплату от пользователя {message.from_user.id}:\n\n"
                                                                                                                            f"{player_info}\n"
                                                                                                                            f"С цифрой в комментарий: {count}",parse_mode="Markdown", reply_markup=builder.as_markup())
    await state.clear()
@router.message(PaidState.recipt)
@flags.throttling_key('default')
async def set_photo(message: Message, state: FSMContext):
    await message.answer("Отправьте фото чека об оплате. (фото)", reply_markup=cancel_kb())
    await state.set_state(PaidState.recipt)



@router.callback_query(F.data.startswith("check_paid"), IsAdmin(admins))
@flags.throttling_key('default')
async def set_photo(call: CallbackQuery, session: AsyncSession, bot: Bot):
    user_id = call.data.split(":")[2]
    yes_or_no = call.data.split(":")[1]
    player = await session.get(Player, user_id)
    if yes_or_no == "yes":
        player.is_registered = True
        active_game = await session.execute(
            select(Game).where(Game.registration == True, Game.is_active == True)
        )
        active_game = active_game.scalar_one_or_none()

        game_player = GamePlayers(
            game_id=active_game.id,
            player_id=player.telegram_id,
            is_alive=True
        )
        player.is_payment_requested = False
        session.add(game_player)
        await session.commit()
        await call.message.edit_caption(caption=f"{call.message.caption}\n"
                                     f"UPD: Игрок был зарегистрирован!")
        await bot.send_message(user_id, f"Вы присоединились к игре {active_game.id}!")
    else:
        player.is_payment_requested = False
        await session.commit()
        await call.message.edit_caption(caption=f"{call.message.caption}\n"
                                     "UPD: Игрок не оплатил билет!")
        await bot.send_message(user_id, "Вы не оплатили билет для участия в игре.")

    return
