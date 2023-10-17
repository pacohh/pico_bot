import json

import aioredis
from aioredis import Redis


def get_client() -> Redis:
    client = aioredis.from_url('redis://localhost')
    return client


async def get_fifo_list(redis: Redis, key: str) -> list:
    value = await redis.get(key)
    if not value:
        return []
    return json.loads(value.decode())


async def set_fifo_list(redis: Redis, key: str, list_: list, max_length: int) -> None:
    value = json.dumps(list_[-max_length:])
    await redis.set(key, value)
