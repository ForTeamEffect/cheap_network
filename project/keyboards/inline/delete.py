from aiogram import types
from aiogram.utils.i18n import gettext

from project.telegram.events.delete import DeleteEvent


def create_delete_button() -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton(
        text=gettext('buttons.delete'),
        callback_data=DeleteEvent().pack(),
    )
