import asyncio

from cachetools import TTLCache


class AsyncCache:
    def __init__(self, maxsize, ttl):
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)

    async def get(self, key):
        return await asyncio.to_thread(self.cache.get, key)

    async def set(self, key, value):
        await asyncio.to_thread(self.cache.__setitem__, key, value)

    async def delete(self, key):
        await asyncio.to_thread(self.cache.__delitem__, key)


def cache_key(t, commission, getrate):
    return t, commission, getrate


async_cache = AsyncCache(maxsize=3, ttl=1000)


cached_value = await async_cache.get(())
def q():
    if cached_value is not None:
        # Если значение есть в кеше, верните его
        return cached_value

key = cache_key()
print(key)
await async_cache.set(key, d)