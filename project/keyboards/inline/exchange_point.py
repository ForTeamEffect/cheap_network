from aiogram import types
from project.exchange_points import *
from .cancel import cancel_button


async def exchange_keyboard(state):
    points_buttons = []
    for point in exchange_points:
        points_buttons.append(types.InlineKeyboardButton(text=point, callback_data=f"exchange_{point}"))
    cansel_b = await cancel_button(state)
    points_buttons.append(cansel_b)
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[points_buttons])
    return keyboard
