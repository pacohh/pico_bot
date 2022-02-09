import logging
import re
from typing import Optional

import dateutil.parser
import dateutil.utils
from aiohttp import ClientResponseError
from aiohttp_requests import requests

import config
from utils.caching import SingleFlightCache as cached
from utils.datetime import datetime_isoformat

BASE_URL = 'https://api.battlemetrics.com'

CURR_MAP_RE = re.compile(r'Current level is (?:.+?), layer is (?P<current_map>.*)$')
NEXT_MAP_RE = re.compile(r'Next level is (?:.+?), layer is (?P<next_map>.*)$')
AFK_SEED_RE = re.compile(r'\b(afk|seed(ing)?)\b', flags=re.IGNORECASE)

RCON_NO_CACHE_ALLOWED_COMMANDS = {
    'squad:broadcast',
}

logger = logging.getLogger(__name__)


@cached(ttl=10)
async def get_player_server(player_id: int, token: str) -> Optional[dict]:
    logger.info('Get current server for player %s', player_id)
    endpoint = f'/players/{player_id}'
    params = {
        'include': 'server',
        'fields[server]': 'name,country',
    }
    try:
        res = await _send_request(endpoint, token=token, params=params)
    except ClientResponseError:
        return None
    data = await res.json()

    servers = data.get('included', [])
    server = None
    for server_ in servers:
        if server_['meta']['online']:
            server = server_
            break

    if server and server['relationships']['game']['data']['id'] not in config.BM_ALLOWED_GAMES:
        server = None

    return {
        'player_id': data['data']['attributes']['id'],
        'player_name': data['data']['attributes']['name'],
        'server_id': server['id'] if server else None,
        'server_name': server['attributes']['name'] if server else None,
        'server_country': server['attributes']['country'].lower() if server else None,
        'server_game': server['relationships']['game']['data']['id'] if server else None,
    }


async def _send_request(endpoint, method='GET', token=None, params=None, json_=None):
    headers = {}

    # Build URL
    if endpoint[0] != '/':
        endpoint = f'/{endpoint}'
    url = f'{BASE_URL}{endpoint}'

    # Add token to the headers
    if token:
        headers['Authorization'] = f'Bearer {token}'

    logger.debug('Sending request %s %s | JSON: %s | Headers: %s', method, url, json_, headers)

    res = await requests.session.request(method, url, params=params, json=json_, headers=headers)
    res.raise_for_status()
    return res
