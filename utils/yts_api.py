from __future__ import annotations

import logging

from aiohttp_requests import requests

API_URL = 'https://yts.mx/api/v2/list_movies.json'

logger = logging.getLogger(__name__)


async def list_all_movies(query: str, quality: str = '2160p') -> list[dict]:
    all_movies = []
    params = {
        'limit': 50,
        'quality': quality,
        'query_term': query,
        'page': 1,
    }
    while True:
        data = await request(params)
        movies = data['data'].get('movies')
        if not movies:
            break
        all_movies.extend(movies)
        params['page'] += 1

    return all_movies


async def request(params: dict[str, str]) -> dict:
    logger.debug('Sending request %s', params)
    res = await requests.session.request('GET', API_URL, params=params)
    res.raise_for_status()
    data = await res.json()
    return data
