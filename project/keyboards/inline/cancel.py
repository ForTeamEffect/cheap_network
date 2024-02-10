from aiogram import types
from aiogram.fsm.context import FSMContext


async def cancel_button(state: FSMContext) -> types.InlineKeyboardButton:
    cancel = types.InlineKeyboardButton(text="Отменить", callback_data="cancel")
    return cancel
