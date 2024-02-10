import os
import time

from aiogram.filters import Command, Text, StateFilter
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import Commission, User, Wallet
from database.database import AsyncSessionLocal
from project.keyboards.inline import create_keyboard
from project.keyboards.inline.wallets import edit_wallets
from states import *
from keyboards.inline.exchange_point import *
import bina, kuco

# Токен бота
API_TOKEN = os.getenv('BOT_TOKEN')

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
Bot.set_current(bot)
dp = Dispatcher(bots=bot, storage=storage)


# Функция обновления информации о комиссиях
async def update_fees():
    async with AsyncSessionLocal() as session:
        current_time = int(time.time())
        time_1000_seconds_ago = current_time - 1000
        # Выполнение запроса к базе данных для получения записей о комиссиях, обновленных в последние 1000 секунд
        result = await session.execute(
            select(Commission).where(
                Commission.update_time.between(time_1000_seconds_ago, current_time)
            )
        )
        result = result.scalars().first()
        if result:
            return  # Если результат найден, завершаем функцию
        # Получение новых значений комиссий от бирж
        new_k = kuco.get_trc_kucoin() or 1.5
        new_b = bina.get_trc_bin() or 1.0
        results_of_points = [new_b, new_k]
        print(results_of_points)
        for point, commission_value in zip(exchange_points, results_of_points):
            try:
                point_commission = select(Commission).filter_by(exchange_point=point)
                point_commission = await session.scalars(point_commission)
                point_commission = point_commission.one()
                if point_commission:
                    point_commission.tron_commission = commission_value
                    point_commission.update_time = current_time
                else:
                    new_commission_info = Commission(update_time=current_time, tron_commission=commission_value,
                                                     exchange_point=point)
                    session.add(new_commission_info)
            except Exception as e:
                print('ещё нету записи о комиссии:', e)
            finally:
                await session.commit()


@dp.message(Command('start'))
async def hello(message: types.Message, state: FSMContext):
    await message.answer("Hi there")


@dp.message(Command('registry'))
async def create_acc(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).filter_by(chat_id=message.chat.id))
        user = user.scalars().first()
        if user:
            return message.answer("Вы уже зарегистрированы")
    data = {'chat_id': message.chat.id}
    if message.from_user.username:
        data['nickname'] = message.from_user.username
    await state.set_state(WAITING_FOR_NAME)
    await state.set_data(data)
    await message.answer("Пожалуйста, введите ваше имя:")
    # операции с базой


@dp.message(StateFilter(WAITING_FOR_NAME))
async def set_name(message: types.Message, state: FSMContext):
    # data = await state.get_data()
    # data['name'] = message.text
    data = {'name': message.text}
    await state.update_data(data)
    await state.set_state(WAITING_FOR_PASS)
    await message.answer("Придумайте пароль.")


@dp.message(StateFilter(WAITING_FOR_PASS))
async def set_pass(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data['password'] = message.text
    new_user = User(**data)
    async with AsyncSessionLocal() as session:
        session.add(new_user)
        await session.commit()
    await state.clear()
    await message.answer("Благодарю, приступим!"
                         "Создайте кошельки чтобы увидеть самые выгодные условия"
                         "транзакций по сети TRC20 на основании доступного баланса."
                         "Или посмотрите независимые данные по биржам через команду"
                         "/get_fees")


@dp.message(Command('create_wallet'))
async def choose_exchange_point(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).filter_by(chat_id=message.chat.id))
        user = user.scalars().first()
        if not user:
            return message.answer("Зарегистрируйтесь")
    await update_fees()
    await message.answer("Выберите биржу:", reply_markup=await exchange_keyboard(state))


@dp.callback_query(Text(startswith="exchange_"))
async def handle_exchange_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем название биржи из callback_data
    point_name = callback_query.data.split("_")[1]  # Если callback_data = "exchange_smthg"
    async with AsyncSessionLocal() as session:
        point = await session.execute(select(Commission).filter_by(exchange_point=point_name))
        point = point.scalars().first()
    await state.set_data({'point': point})
    data = await state.get_data()
    if 'wallet_number' in data:
        wallet_number = data['wallet_number']
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).options(
                    selectinload(User.wallets)
                ).filter_by(chat_id=callback_query.message.chat.id)
            )
            result = result.scalars().first()
            if result:
                for user_wallet in result.wallets:
                    if user_wallet.wallet_number == wallet_number:
                        user_wallet.exchange_id = point.id
                        await session.commit()
                        await state.clear()
                        await callback_query.message.answer("Биржа установлена")
                        return
            else:
                await state.set_state(WAITING_FOR_Wallet)
                await callback_query.answer()
                await callback_query.message.answer(f"Укажите кошелёк")


@dp.message(StateFilter(WAITING_FOR_Wallet))
async def process_wallet_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    wallet = message.text
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).filter_by(chat_id=message.chat.id))
        user = user.scalars().first()
        if not user:
            await message.answer("Зарегистрируйтесь")
            return
        result = await session.execute(
            select(User).options(
                selectinload(User.wallets)
            ).filter_by(chat_id=message.chat.id)
        )
        result = result.scalars().first()
        if result:
            for user_wallet in result.wallets:
                if user_wallet.wallet_number == data.get('old_number'):
                    user_wallet.wallet_number = wallet
                    await session.commit()
                    return
        else:
            exchange_id = data['point'].id
            new_wallet = Wallet(exchange_id=exchange_id, user=user, wallet_number=wallet)
            session.add(new_wallet)
            await session.commit()
            await state.set_state(WAITING_FOR_AMOUNT)
            await state.set_data({'wallet': wallet})
            await message.answer("Какой установим баланс?")


# Обработка введенной суммы
@dp.message(StateFilter(WAITING_FOR_AMOUNT))
async def process_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        wallet_number = data['wallet']
        try:
            result = await session.execute(
                select(User).options(
                    selectinload(User.wallets)
                ).filter_by(chat_id=message.chat.id)
            )
            result = result.scalars().first()
            if result:
                for user_wallet in result.wallets:
                    if user_wallet.wallet_number == wallet_number:
                        user_wallet.amount = float(message.text)
                        await session.commit()
                        await state.clear()
                        await message.answer("Сумма установлена")
            else:
                await message.answer("Кошелек не найден.")
        except Exception as e:
            await message.answer(f"Произошла ошибка")
            print('Ошибка в функции установки суммы:', e)

    await state.clear()
    # await message.answer("Сумма установлена")


async def get_wallets_func(message: types.Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).options(
                selectinload(User.wallets).selectinload(Wallet.exchange)
            ).filter_by(chat_id=message.chat.id)
        )
        user = result.scalars().first()
        if user is None:
            return "Пользователь не найден."
        wallets_info = []
        for wallet in user.wallets:
            exchange_info = f"{wallet.exchange.exchange_point}, комиссия: {wallet.exchange.tron_commission}\n"
            wallet_info = f"Кошелек: {wallet.wallet_number}\nбаланс: {wallet.amount}, биржа: {exchange_info}"
            wallets_info.append(wallet_info)
            # возвращаем строку сообщения и объекты кошельков
        return ["\n".join(wallets_info), user.wallets]


@dp.message(Command('wallets'))
async def show_wallets(message: types.Message, state: FSMContext):
    # Выполнение запроса к базе данных для получения пользователя по chat_id
    wallets_of_user = await get_wallets_func(message)
    reply_mark = await edit_wallets(wallets_of_user[1], state)
    keyboard = create_keyboard(*reply_mark)
    await message.answer(wallets_of_user[0], reply_markup=keyboard)


@dp.callback_query(Text(startswith="wallet-number_"))
async def handle_wallet_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем название кошелька из callback_data
    number = callback_query.data.split("_")[1]  # Если callback_data = "wallet-number_smthg"
    cansel_b = await cancel_button(state)
    change_amount = types.InlineKeyboardButton(text='Изменить сумму', callback_data=f"change-summ_{number}")
    change_wallet_name = types.InlineKeyboardButton(text='Изменить номер', callback_data=f"change-wallet_{number}")
    change_network = types.InlineKeyboardButton(text='Изменить биржу', callback_data=f"change-network_{number}")
    choose_action = create_keyboard(change_amount, change_wallet_name, change_network, cansel_b)
    await state.set_state(WAITING_FOR_Wallet)
    await callback_query.answer()
    await callback_query.message.answer(f"Выберите действие", reply_markup=choose_action)


@dp.callback_query(Text(startswith="change-summ_"))
async def handle_change_summ_callback(callback_query: types.CallbackQuery, state: FSMContext):
    wallet = callback_query.data.split("_")[1]
    await callback_query.message.answer(f"Какой установим баланс?")
    await state.set_data({'wallet': wallet})
    await state.set_state(WAITING_FOR_AMOUNT)
    await callback_query.answer()


async def change_wallet_name(number):
    async with AsyncSessionLocal() as session:
        wallet = await session.execute(select(Wallet).filter_by(exchange_point=number))
        wallet = wallet.scalars().first()
        wallet.wallet_number = number
        await session.commit()


@dp.callback_query(Text(startswith="change-wallet_"))
async def handle_change_wallet_name_callback(callback_query: types.CallbackQuery, state: FSMContext):
    old_number = callback_query.data.split("_")[1]
    await callback_query.message.answer(f"Введите кошелёк")
    await state.set_state(WAITING_FOR_Wallet)
    await state.set_data({'old_number': old_number})
    await callback_query.answer()


@dp.callback_query(Text(startswith="change-network_"))
async def handle_change_network_callback(callback_query: types.CallbackQuery, state: FSMContext):
    wallet_number = callback_query.data.split("_")[1]
    await callback_query.message.answer(f"Выберите биржу:", reply_markup=await exchange_keyboard(state))
    await state.set_data({'wallet_number': wallet_number})
    await callback_query.answer()


@dp.callback_query(Text("cancel"))
async def handle_cancel_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.answer()
