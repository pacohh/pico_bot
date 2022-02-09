import asyncio
from asyncio import sleep

from aiocache import cached as base_cached


class SingleFlightCache(base_cached):
    """
    Subclass of `aiocache.cached` that caches a `CoroutinePromise` before the
    decorated function is called. This way multiple calls to the decorated
    function will all wait for the cached promise's result from the first call.

    This prevents a long running function from being called multiple times
    before it finishes and the result is cached.
    """

    lock = asyncio.Lock()

    async def decorator(self, f, *args, cache_read=True, cache_write=True, **kwargs):
        async with self.lock:
            promise = None
            key = self.get_cache_key(f, args, kwargs)

            if cache_read:
                # Check if a promise already exists in the cache
                promise = await self.get_from_cache(key)

            cache_hit = promise is not None
            if not cache_hit:
                # Create promise if there wasn't a cache hit
                promise = CoroutinePromise()
                if cache_write:
                    await self.set_in_cache(key, promise)
                promise.set_coroutine(f(*args, **kwargs))

        return await promise.get_result()


class CoroutinePromise:
    """
    Helper class that can await the result of a coroutine multiple times.

    The coroutine doesn't have to be given before the result is awaited for: if
    `get_result()` is called before `set_coroutine()` it will await until
    `set_coroutine()` is called.
    """

    def __init__(self, sleep_time=0.1):
        self.sleep_time = sleep_time

        self.coroutine = None
        self.result = None
        self.exception = None

        self.coroutine_set = False
        self.awaited = False
        self.got_result = False

    def set_coroutine(self, coroutine):
        self.coroutine = coroutine
        self.coroutine_set = True

    async def get_result(self):
        while not self.coroutine_set:
            # Wait until the coroutine is set
            await sleep(self.sleep_time)

        if not self.awaited:
            # Await the coroutine
            self.awaited = True
            try:
                self.result = await self.coroutine
            except Exception as exc:
                self.exception = exc
            self.got_result = True

        while not self.got_result:
            # Wait until the await has returned the result
            await sleep(self.sleep_time)

        if self.exception:
            raise self.exception
        else:
            return self.result
