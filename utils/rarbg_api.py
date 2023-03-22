from __future__ import annotations

import logging
from typing import Union

from aiohttp_requests import requests

API_URL = 'http://torrentapi.org/pubapi_v2.php'

logger = logging.getLogger(__name__)


async def get_token() -> str:
    data = await _send_request({'get_token': 'get_token'})
    return data['token']


async def request(params: dict[str, str], token: Union[str, None] = None) -> dict:
    if not token and 'token' not in params:
        token = await get_token()
        params['token'] = token
    return await _send_request(params)


async def _send_request(params: dict[str, str]) -> dict:
    # Docs: https://torrentapi.org/apidocs_v2.txt
    if 'app_id' not in params:
        params['app_id'] = 'pico'

    logger.debug('Sending request %s', params)

    res = await requests.session.request('GET', API_URL, params=params)
    res.raise_for_status()
    data = await res.json()
    return data
