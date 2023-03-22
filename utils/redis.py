import aioredis
from aioredis import Redis


def get_client() -> Redis:
    client = aioredis.from_url('redis://localhost')
    return client
