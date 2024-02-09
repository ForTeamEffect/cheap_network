from aiogram import Bot
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

from project.database.models import FSMData


class DBStorage(BaseStorage):
    async def set_state(self, bot: Bot, key: StorageKey, state: StateType = None):
        model = await FSMData.get_by_storage_key(key)
        if isinstance(state, State):
            state = state.state
        model.state = state
        await model.save(update_fields={'state'})

    async def get_state(self, bot: Bot, key: StorageKey) -> str | None:
        model = await FSMData.get_by_storage_key(key)
        return model.state

    async def set_data(self, bot: Bot, key: StorageKey, data: dict):
        model = await FSMData.get_by_storage_key(key)
        model.data = data
        await model.save(update_fields={'data'})

    async def get_data(self, bot: Bot, key: StorageKey) -> dict:
        model = await FSMData.get_by_storage_key(key)
        return model.data

    async def close(self):
        pass
