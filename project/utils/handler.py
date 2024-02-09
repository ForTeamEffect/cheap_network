import functools
import inspect

from aiogram import types
from aiogram.enums import ChatType
from loguru import logger

package_constraints = {
    'private': [ChatType.PRIVATE],
    'chat': [ChatType.GROUP, ChatType.SUPERGROUP],
    'channel': [ChatType.CHANNEL],
}


def handler(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger.opt(colors=True).info(f'Handler <red>{func.__name__}</red> called')
        module = inspect.getmodule(func)
        chat = types.Chat.get_current()
        for package, constraints in package_constraints.items():
            if f'.{package}.' in module.__name__ and chat.type not in constraints:
                logger.warning('Invalid chat type')
                return
        return await func(*args, **kwargs)

    return wrapper
