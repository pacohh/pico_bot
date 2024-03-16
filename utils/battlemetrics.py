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
async def get_server_players(server_id: str, token: str):
    data = await get_server_info(server_id, token)
    server = data['data']
    server_attrs = server['attributes'] if server else None
    server_details = server_attrs['details'] if server else None
    players = {}
    for player_data in data['included']:
        player_id = player_data['id']
        if player_id not in config.BM_PLAYERS:
            continue
        players[player_id] = {
            'player': {
                'id': player_id,
                'name': player_data['attributes']['name'],
            },
            'server': {
                'id': server['id'] if server else None,
                'name': server['attributes']['name'] if server else None,
                'ip': server_attrs['ip'] if server else None,
                'port': server_attrs['port'] if server else None,
                'port_query': server_attrs['portQuery'] if server else None,
                'country': server_attrs['country'].lower() if server else None,
                'emote': config.BM_SERVER_EMOTES.get(server['id']) if server else None,
                'game': server['relationships']['game']['data']['id'] if server else None,
                'players': server_attrs['players'] if server else None,
                'max_players': server_attrs['maxPlayers'] if server else None,
                'layer': server_details['map'] if server else None,
                'next_layer': server_details.get('squad_nextLayer') if server else None,
                'queue': (
                    server_details['squad_publicQueue'] + server_details['squad_reservedQueue']
                    if server
                    else None
                ),
            },
        }
    return players


@cached(ttl=10)
async def get_server_info(server_id: str, token: str):
    logger.debug('Get server %s info', server_id)
    endpoint = f'/servers/{server_id}'
    params = {
        'include': 'player',
    }
    try:
        res = await _send_request(endpoint, token=token, params=params)
    except ClientResponseError:
        logger.error('Error getting server %s info', server_id)
        return None
    data = await res.json()
    return data


@cached(ttl=10)
async def get_player_server(player_id: str, token: str) -> Optional[dict]:
    logger.debug('Get current server for player %s', player_id)
    endpoint = f'/players/{player_id}'
    params = {
        'include': 'server',
        'fields[server]': 'name,country,players,maxPlayers,details,ip,port,portQuery',
    }
    try:
        res = await _send_request(endpoint, token=token, params=params)
    except ClientResponseError:
        logger.error('Error getting current server for player %s', player_id)
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

    data_attrs = data['data']['attributes']
    server_attrs = server['attributes'] if server else None
    server_details = server_attrs['details'] if server else None
    return {
        'player': {
            'id': data_attrs['id'],
            'name': data_attrs['name'],
        },
        'server': {
            'id': server['id'] if server else None,
            'name': server['attributes']['name'] if server else None,
            'ip': server_attrs['ip'] if server else None,
            'port': server_attrs['port'] if server else None,
            'port_query': server_attrs['portQuery'] if server else None,
            'country': server_attrs['country'].lower() if server else None,
            'emote': config.BM_SERVER_EMOTES.get(server['id']) if server else None,
            'game': server['relationships']['game']['data']['id'] if server else None,
            'players': server_attrs['players'] if server else None,
            'max_players': server_attrs['maxPlayers'] if server else None,
            'layer': server_details['map'] if server else None,
            'queue': (
                server_details['squad_publicQueue'] + server_details['squad_reservedQueue']
                if server
                else None
            ),
        },
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
