
import os
import time

from aiogram.filters import Command, Text, StateFilter
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select

from database.models import Commission, User, Wallet
from database.database import AsyncSessionLocal
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
        for point, commission in zip(exchange_points,results_of_points):
            try:
                commission = await session.execute(select(Commission).filter_by(exchange_point=point))
                commission = commission.scalars().first()
                if commission:
                    commission.tron_commission = commission
            except Exception as e:
                print('ещё нету записи о комиссии:', e)
            else:
                new_commission_info = Commission(update_time=current_time, tron_commission=commission,
                                                 exchange_point=point)
                session.add(new_commission_info)
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
    await message.answer("Выберите биржу:", reply_markup=exchange_keyboard())


@dp.callback_query(Text(startswith="exchange_"))
async def handle_exchange_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем название биржи из callback_data
    point_name = callback_query.data.split("_")[1]  # Если callback_data = "exchange_Binance"
    async with AsyncSessionLocal() as session:
        point = await session.execute(select(Commission).filter_by(exchange_point=point_name))
        point = point.scalars().first()
    await state.set_data({'point': point})
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
            result = await session.execute(select(Wallet).filter_by(wallet_number=wallet_number))
            wallet_object = result.scalars().first()
            if wallet_object:
                wallet_object.amount = float(message.text)
                await session.commit()
                await state.clear()
                await message.answer("Сумма установлена")
            else:
                await message.answer("Кошелек не найден.")
        except Exception as e:
            await message.answer(f"Произошла ошибка: {e}")
            print('Ошибка в функции установки суммы:', e)


    await state.clear()
    # await message.answer("Сумма установлена")
