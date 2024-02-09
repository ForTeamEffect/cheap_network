from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_keyboard(*buttons: types.InlineKeyboardButton) -> types.InlineKeyboardMarkup:
    return InlineKeyboardBuilder().add(*buttons).adjust(1).as_markup()
