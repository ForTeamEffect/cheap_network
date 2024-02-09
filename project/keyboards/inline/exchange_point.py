from aiogram import types
from project.exchange_points import *


def exchange_keyboard():
    points_buttons = []
    for point in exchange_points:
        points_buttons.append(types.InlineKeyboardButton(text=point, callback_data=f"exchange_{point}"))
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[points_buttons])
    return keyboard