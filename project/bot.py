import os
import time


from aiogram.filters import Command, Text, StateFilter
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from loguru import logger

from database.models import Commission, User, Wallet
from database.database import AsyncSessionLocal
from project.keyboards.inline import create_keyboard
from project.keyboards.inline.wallets import edit_wallets
from project.utils.handler import handler
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

logger.add("logs/debug.log", format="{time} {level} {message}", level="INFO")


# Функция обновления информации о комиссиях
@handler
async def update_fees():
    """
    Функция для обновления информации о комиссиях бирж.
    Проверяет, были ли обновлены комиссии в последние 1000 секунд, и если нет,
    обновляет информацию, получая новые данные от бирж.
    """
    async with AsyncSessionLocal() as session:
        current_time = int(time.time())
        time_1000_seconds_ago = current_time - 1000

        try:
            # Пытаемся найти записи о комиссиях, обновленные в последние 1000 секунд
            result = await session.execute(
                select(Commission).where(
                    Commission.update_time.between(time_1000_seconds_ago, current_time)
                )
            )
            result = result.scalars().first()

            # Если такие записи найдены, прекращаем выполнение функции
            if result:
                logger.info("Комиссии уже обновлены.")
                return

            # Получение новых данных о комиссиях от бирж
            new_k = kuco.get_trc_kucoin() or 1.5
            new_b = bina.get_trc_bin() or 1.0
            results_of_points = [new_b, new_k]

            # Обновление или добавление информации о комиссиях для каждой биржи
            for point, commission_value in zip(exchange_points, results_of_points):
                try:
                    point_commission = select(Commission).filter_by(exchange_point=point)
                    point_commission = await session.scalars(point_commission)
                    point_commission = point_commission.one()

                    if point_commission:
                        point_commission.tron_commission = commission_value
                        point_commission.update_time = current_time
                        logger.info(f"Обновлена информация о комиссии для {point}.")
                    else:
                        new_commission_info = Commission(update_time=current_time, tron_commission=commission_value,
                                                         exchange_point=point)
                        session.add(new_commission_info)
                        logger.info(f"Добавлена новая информация о комиссии для {point}.")

                except SQLAlchemyError as e:
                    logger.error(f"Ошибка при обновлении информации о комиссии для {point}: {e}")
                    # Откатываем изменения, если возникла ошибка
                    await session.rollback()

            # Подтверждаем изменения в базе данных
            await session.commit()

        except Exception as e:
            logger.error(f"Неожиданная ошибка при обновлении комиссий: {e}")
            # Откатываем изменения, если возникла ошибка
            await session.rollback()


@dp.message(Command('start'))
@handler
async def hello(message: types.Message, state: FSMContext):
    await message.answer("Hi there")



@dp.message(Command('registry'))
@handler
async def create_acc(message: types.Message, state: FSMContext):
    """
    Обработчик команды регистрации пользователя.

    Проверяет, зарегистрирован ли пользователь уже в системе. Если нет, запрашивает имя.
    """
    async with AsyncSessionLocal() as session:
        try:
            user = await session.execute(select(User).filter_by(chat_id=message.chat.id))
            user = user.scalars().first()
            if user:
                logger.info("Пользователь уже зарегистрирован: {}", message.chat.id)
                return await message.answer("Вы уже зарегистрированы")
        except Exception as e:
            logger.error("Ошибка при проверке пользователя: {}", e)
            return await message.answer("Произошла ошибка при регистрации.")
    data = {'chat_id': message.chat.id}
    if message.from_user.username:
        data['nickname'] = message.from_user.username
    await state.set_state(WAITING_FOR_NAME)
    await state.set_data(data)
    await message.answer("Пожалуйста, введите ваше имя:")
    logger.info("Запрос на регистрацию от пользователя: {}", message.chat.id)



@dp.message(StateFilter(WAITING_FOR_NAME))
@handler
async def set_name(message: types.Message, state: FSMContext):
    """
    Обработчик ввода имени пользователя.

    Запрашивает у пользователя пароль после ввода имени.
    """
    if message.text:
        data = {'name': message.text}
    else:
        logger.info("Пользователь {} не ввёл текст", message.chat.id)
        await state.clear()
        return
    await state.update_data(data)
    await state.set_state(WAITING_FOR_PASS)
    await message.answer("Придумайте пароль.")
    logger.info("Пользователь {} ввел имя: {}", message.chat.id, message.text)



@dp.message(StateFilter(WAITING_FOR_PASS))
@handler
async def set_pass(message: types.Message, state: FSMContext):
    """
    Задает пароль для пользователя после ввода имени.
    """
    if not message.text:
        logger.info("Пользователь {} не ввёл текст", message.chat.id)
        await state.clear()
        return
    # Получаем данные из состояния
    data = await state.get_data()
    data['password'] = message.text

    # Создаем нового пользователя и сохраняем его в базе данных
    new_user = User(**data)
    try:
        async with AsyncSessionLocal() as session:
            session.add(new_user)
            await session.commit()
            logger.info("Новый пользователь зарегистрирован: {}", message.from_user.id)
    except Exception as e:
        logger.error("Ошибка при регистрации пользователя: {}. {}", message.from_user.id, e)
        return await message.answer("Произошла ошибка при регистрации.")

    # Очищаем состояние и отправляем сообщение пользователю
    await state.clear()
    await message.answer("Благодарю, приступим!"
                         "Создайте кошельки чтобы увидеть самые выгодные условия"
                         "транзакций по сети TRC20 на основании доступного баланса.")

async def check_auth(message: types.Message):
    # Проверяем, зарегистрирован ли пользователь
    async with AsyncSessionLocal() as session:
        try:
            user = await session.execute(select(User).filter_by(chat_id=message.chat.id))
            user = user.scalars().first()
            return user
        except DBAPIError as e:
            logger.info("Пользователь не зарегистрирован: {}", message.from_user.id)
            await message.answer("Зарегистрируйтесь")
            return False

@dp.message(Command('create_wallet'))
@handler
async def choose_exchange_point(message: types.Message, state: FSMContext):
    """
    Позволяет пользователю выбрать биржу для создания кошелька.
    """
    # Проверяем, зарегистрирован ли пользователь
    if not await check_auth(message):
        return
    # Обновляем информацию о комиссиях и предлагаем выбор биржи
    await update_fees()
    await message.answer("Выберите биржу:", reply_markup=await exchange_keyboard(state))
    logger.info("Пользователь {} выбирает биржу для создания кошелька", message.from_user.id)


@dp.callback_query(Text(startswith="exchange_"))
@handler
async def handle_exchange_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор биржи пользователем через inline-кнопки.
    """
    # Разбор callback_data для получения названия биржи
    point_name = callback_query.data.split("_")[1]
    logger.info(f"Пользователь {callback_query.from_user.id} выбрал биржу {point_name}")

    try:
        # Поиск выбранной биржи в базе данных
        async with AsyncSessionLocal() as session:
            point = await session.execute(select(Commission).filter_by(exchange_point=point_name))
            point = point.scalars().first()
            if point is None:
                logger.warning(f"Биржа {point_name} не найдена")
                await callback_query.answer("Биржа не найдена, попробуйте еще раз.")
                return

        # Сохранение выбранной биржи в состояние
        data = await state.get_data()

        if 'wallet_number' in data:
            wallet_number = data['wallet_number']
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).options(
                        selectinload(User.wallets)
                    ).filter_by(chat_id=callback_query.message.chat.id)
                )
                user = result.scalars().first()
                if user:
                    for user_wallet in user.wallets:
                        if user_wallet.wallet_number == wallet_number:
                            user_wallet.exchange_id = point.id
                            await session.commit()
                            logger.info(f"Биржа {point_name} установлена для кошелька {wallet_number}")
                            await callback_query.message.answer("Биржа установлена")
                            await state.clear()
                            await callback_query.answer()
                            return
        else:
            await state.set_state(WAITING_FOR_Wallet)
            await callback_query.answer()
            await state.set_data({'point': point})
            await callback_query.message.answer(f"Укажите кошелёк")
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора биржи: {e}")
        await callback_query.answer("Произошла ошибка, попробуйте еще раз.")



@dp.message(StateFilter(WAITING_FOR_Wallet))
@handler
async def process_wallet_number(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод номера кошелька от пользователя.
    """
    if not message.text:
        logger.info("Пользователь {} не ввёл текст", message.chat.id)
        await state.clear()
        return
    data = await state.get_data()
    wallet = message.text
    try:
        async with AsyncSessionLocal() as session:
            # Попытка найти пользователя по chat_id
            user = await session.execute(select(User).filter_by(chat_id=message.chat.id))
            user = user.scalars().first()
            if not user:
                logger.info(f"Пользователь с chat_id={message.chat.id} не найден.")
                await message.answer("Зарегистрируйтесь")
                return

            # Проверка существования старого номера кошелька
            if 'old_number' in data:
                result = await session.execute(
                    select(User).options(selectinload(User.wallets)).filter_by(chat_id=message.chat.id)
                )
                user_with_wallets = result.scalars().first()
                if user_with_wallets:
                    for user_wallet in user_with_wallets.wallets:
                        if user_wallet.wallet_number == data.get('old_number'):
                            user_wallet.wallet_number = wallet
                            await session.commit()
                            logger.info(f"Номер кошелька изменен на {wallet} для пользователя {message.chat.id}")
                            await message.answer("Номер кошелька изменён")
                            await state.clear()
                            return

            # Добавление нового кошелька
            exchange_id = data['point'].id
            new_wallet = Wallet(exchange_id=exchange_id, user=user, wallet_number=wallet)
            session.add(new_wallet)
            await session.commit()
            logger.info(f"Новый кошелек {wallet} добавлен для пользователя {message.chat.id}")
            await state.set_state(WAITING_FOR_AMOUNT)
            await state.set_data({'wallet': wallet})
            await message.answer("Какой установим баланс?")
    except Exception as e:
        logger.error(f"Ошибка при обработке номера кошелька: {e}")
        await message.answer("Произошла ошибка при обработке вашего запроса.")



@dp.message(StateFilter(WAITING_FOR_AMOUNT))
@handler
async def process_amount(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод суммы пользователем, и обновляет баланс кошелька.
    """
    data = await state.get_data()
    wallet_number = data['wallet']
    try:
        async with AsyncSessionLocal() as session:
            # Запрос к базе для получения пользователя и связанных с ним кошельков
            result = await session.execute(
                select(User).options(selectinload(User.wallets)).filter_by(chat_id=message.chat.id)
            )
            user = result.scalars().first()

            if user:
                # Поиск кошелька по номеру среди кошельков пользователя
                wallet_found = False
                for user_wallet in user.wallets:
                    if user_wallet.wallet_number == wallet_number:
                        user_wallet.amount = float(message.text)
                        wallet_found = True
                        break

                if wallet_found:
                    await session.commit()
                    logger.info(f"Баланс кошелька {wallet_number} обновлен: {message.text}")
                    await message.answer("Сумма установлена")
                else:
                    logger.warning(f"Кошелек {wallet_number} не найден для пользователя {message.chat.id}.")
                    await message.answer("Кошелек не найден.")
            else:
                logger.warning(f"Пользователь с chat_id={message.chat.id} не найден.")
                await message.answer("Пользователь не найден.")

    except Exception as e:
        logger.error(f"Ошибка при обновлении суммы в кошельке: {e}")
        await message.answer("Произошла ошибка при обработке вашего запроса.")

    finally:
        await state.clear()


@handler
async def get_wallets_func(message: types.Message):
    """
    Получает информацию о всех кошельках пользователя.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).options(
                    selectinload(User.wallets).selectinload(Wallet.exchange)
                ).filter_by(chat_id=message.chat.id)
            )
            user = result.scalars().first()

            if user is None:
                logger.info(f"Пользователь с chat_id={message.chat.id} не найден.")
                return "Пользователь не найден."

            wallets_info = []
            for wallet in user.wallets:
                exchange_info = f"{wallet.exchange.exchange_point}, " \
                                f"комиссия: {wallet.exchange.tron_commission}"
                wallet_info = f"Кошелек: {wallet.wallet_number}\n" \
                              f" баланс: {wallet.amount}, биржа: {exchange_info}\n"
                wallets_info.append(wallet_info)

            logger.info(f"Информация о кошельках пользователя с chat_id={message.chat.id} "
                        f"успешно получена.")
            return ["\n".join(wallets_info), user.wallets]

    except Exception as e:
        logger.error(f"Ошибка при получении информации о кошельках: {e}")
        return ["Произошла ошибка при обработке вашего запроса.", None]



@dp.message(Command('wallets'))
@handler
async def show_wallets(message: types.Message, state: FSMContext):
    """
    Отображает информацию о кошельках пользователя.
    """
    # Проверяем, зарегистрирован ли пользователь
    if not await check_auth(message):
        return
    try:
        wallets_of_user, wallets_objects = await get_wallets_func(message)

        if wallets_objects is None:
            await message.answer(wallets_of_user)  # Вывод сообщения об ошибке или о том, что пользователь не найден
            return

        reply_mark = await edit_wallets(wallets_objects, state)
        keyboard = create_keyboard(*reply_mark)
        await message.answer(wallets_of_user, reply_markup=keyboard)
        logger.info(f"Информация о кошельках отправлена пользователю с chat_id={message.chat.id}.")

    except Exception as e:
        logger.error(f"Ошибка при отображении информации о кошельках: {e}")
        await message.answer("Произошла ошибка при попытке отобразить кошельки.")



@dp.callback_query(Text(startswith="wallet-number_"))
@handler
async def handle_wallet_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку с номером кошелька.
    """
    # Логируем получение callback запроса
    logger.info(f"Обработка callback от кошелька: {callback_query.data}")
    try:
        number = callback_query.data.split("_")[1]  # Если callback_data = "wallet-number_smthg"
        cansel_b = await cancel_button(state)
        change_amount = types.InlineKeyboardButton(text='Изменить сумму', callback_data=f"change-summ_{number}")
        change_wallet_name = types.InlineKeyboardButton(text='Изменить номер', callback_data=f"change-wallet_{number}")
        change_network = types.InlineKeyboardButton(text='Изменить биржу', callback_data=f"change-network_{number}")
        choose_action = create_keyboard(change_amount, change_wallet_name, change_network, cansel_b)
        await state.set_state(WAITING_FOR_Wallet)
        await callback_query.answer()
        await callback_query.message.answer(f"Выберите действие", reply_markup=choose_action)

    except Exception as e:
        logger.error(f"Ошибка при обработке callback запроса: {e}")
        await callback_query.answer("Произошла ошибка, попробуйте еще раз.")


@dp.callback_query(Text(startswith="change-summ_"))
@handler
async def handle_change_summ_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает запрос на изменение суммы в кошельке.
    """
    logger.info(f"Запрос на изменение суммы для кошелька: {callback_query.data}")
    try:
        wallet = callback_query.data.split("_")[1]
        await callback_query.message.answer(f"Какой установим баланс?")
        await state.set_data({'wallet': wallet})
        await state.set_state(WAITING_FOR_AMOUNT)
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на изменение суммы: {e}")
        await callback_query.answer("Произошла ошибка, попробуйте еще раз.")

@handler
async def change_wallet_name(number):
    """
    Изменяет название кошелька.
    """
    logger.info(f"Изменение названия кошелька на {number}")
    try:
        async with AsyncSessionLocal() as session:
            wallet = await session.execute(select(Wallet).filter_by(wallet_number=number))
            wallet = wallet.scalars().first()
            if wallet:
                wallet.wallet_number = number
                await session.commit()
                logger.info(f"Номер кошелька успешно изменен на {number}")
            else:
                logger.warning(f"Кошелек с номером {number} не найден.")
    except Exception as e:
        logger.error(f"Ошибка при изменении номера кошелька: {e}")


@dp.callback_query(Text(startswith="change-wallet_"))
@handler
async def handle_change_wallet_name_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает запрос на изменение номера кошелька.
    """
    logger.info("Запрос на изменение номера кошелька")
    try:
        old_number = callback_query.data.split("_")[1]
        await callback_query.message.answer("Введите новый номер кошелька")
        await state.set_state(WAITING_FOR_Wallet)
        await state.set_data({'old_number': old_number})
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения номера кошелька: {e}")
        await callback_query.answer("Произошла ошибка, попробуйте еще раз.")

@dp.callback_query(Text(startswith="change-network_"))
@handler
async def handle_change_network_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает запрос на изменение биржи кошелька.
    """
    logger.info("Запрос на изменение биржи кошелька")
    try:
        wallet_number = callback_query.data.split("_")[1]
        await callback_query.message.answer("Выберите новую биржу:", reply_markup=await exchange_keyboard(state))
        await state.set_data({'wallet_number': wallet_number})
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения биржи кошелька: {e}")
        await callback_query.answer("Произошла ошибка, попробуйте еще раз.")

@dp.message(Command('calculate'))
@handler
async def calc(message: types.Message, state: FSMContext):
    """
    Запрашивает у пользователя сумму для расчета возможных транзакций.
    """
    # Проверяем, зарегистрирован ли пользователь

    if not await check_auth(message):
        return
    logger.info("Запрос суммы для расчета")
    try:
        await message.answer("Введите сумму транзакции")
        await state.set_state(WAITING_FOR_CALCULATE)
    except Exception as e:
        logger.error(f"Ошибка при запросе суммы транзакции: {e}")
        await message.answer("Произошла ошибка, попробуйте еще раз.")
@handler
@dp.callback_query(Text("cancel"))
async def handle_cancel_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обрабатывает запрос на отмену текущего действия.
    """
    logger.info("Запрос на отмену текущего действия")
    try:
        await state.clear()
        await callback_query.answer("Действие отменено.")
    except Exception as e:
        logger.error(f"Ошибка при отмене действия: {e}")
        await callback_query.answer("Произошла ошибка, попробуйте отменить действие еще раз.")


@handler
@dp.message(StateFilter(WAITING_FOR_CALCULATE))
async def calculate_commission(message: types.Message, state: FSMContext):
    """
    Рассчитывает комиссию для суммы транзакции, указанной пользователем, и предоставляет
    информацию о подходящих и не подходящих кошельках в зависимости от доступной суммы и комиссии.
    """
    logger.info(f"Пользователь {message.from_user.id} начал расчет комиссии")
    if not message.text:
        logger.info("Пользователь {} не ввёл текст", message.chat.id)
        await state.clear()
        return
    try:
        # Получаем сумму для расчета
        amount_to_calculate = float(message.text)

        # Получаем кошельки пользователя
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).options(
                    selectinload(User.wallets).selectinload(Wallet.exchange)
                ).filter_by(chat_id=message.chat.id)
            )
            user = result.scalars().first()

            if not user:
                logger.error(f"Пользователь {message.from_user.id} не найден")
                await message.answer("Пользователь не найден.")
                return

            suitable_wallets = []
            unsuitable_wallets = []
            # Обработка кошельков пользователя
            for wallet in user.wallets:
                if wallet.amount:
                    tron_commission = wallet.exchange.tron_commission
                    if wallet.amount >= amount_to_calculate:
                        suitable_wallets.append((wallet, tron_commission))
                    else:
                        unsuitable_wallets.append((wallet, tron_commission))

            suitable_wallets.sort(key=lambda x: x[1])  # Сортировка подходящих кошельков

            # Формирование сообщения для пользователя
            message_lines = ["Доступные переводы:"]
            for wallet, tron_commission in suitable_wallets:
                message_lines.append(
                    f"Кошелек: {wallet.wallet_number}\n"
                    f"комиссия - {tron_commission}$   сумма- {amount_to_calculate}$\n"
                )
            message_lines.append("---------------------")
            for wallet, tron_commission in unsuitable_wallets:
                message_lines.append(
                    f"Кошелек: {wallet.wallet_number}\n"
                    f"комиссия - {tron_commission}$   баланс- {wallet.amount}$\n"
                )
            await message.answer("\n".join(message_lines))
    except ValueError:
        logger.error(f"Ошибка при обработке суммы от пользователя {message.from_user.id}")
        await message.answer("Ошибка в введенной сумме. Укажите корректное числовое значение.")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при расчете комиссии для пользователя {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при расчете комиссии. Попробуйте позже.")
    finally:
        await state.clear()

# добавить скидывание авторизации