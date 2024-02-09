from aiogram import types


async def cancel_button(state):
    cansel = types.InlineKeyboardButton(text="Отменить")
    await state.clear()  # Очищаем состояние
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[cansel]])
    return keyboard
