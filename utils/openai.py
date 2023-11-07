from __future__ import annotations

import base64
import logging
from io import BytesIO
from typing import Optional

from aiohttp_requests import requests
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_fixed,
)

from utils import env

BASE_URL = 'https://api.openai.com/v1'

logger = logging.getLogger(__name__)


class ModerationFlaggedError(Exception):
    def __init__(self, flags: list[str], *args: object) -> None:
        self.flags = flags
        super().__init__(*args)


@retry(
    wait=wait_fixed(3),
    stop=stop_after_delay(60) | stop_after_attempt(5),
    retry=retry_if_not_exception_type(ModerationFlaggedError),
)
async def chat(messages: list[dict[str, str]], user: Optional[str] = None) -> str:
    # Check for content policy violations
    latest_message = messages[-1]['content']
    flags = await moderation(latest_message)
    if flags:
        logger.warning(
            'Chat message prevented because of policy violations (%s), message: %s',
            ', '.join(flags),
            latest_message,
        )
        raise ModerationFlaggedError(flags)

    logger.info('Sending OpenAI chat request with messages: %s', messages)

    data = {
            'model': 'gpt-4-vision-preview',
            'messages': messages,
            'temperature': 0.1,
        }
    if user:
        data['user'] = user

    response = await _send_request(
        '/chat/completions',
        method='POST',
        json_=data,
    )
    rdata = await response.json()

    logger.info('Used %d tokens for request %s', rdata['usage']['total_tokens'], rdata['id'])

    return rdata['choices'][0]['message']['content']


async def moderation(text: str) -> list[str]:
    response = await _send_request(
        '/moderations',
        method='POST',
        json_={'input': text},
    )
    data = await response.json()
    flags = [name for name, value in data['results'][0]['categories'].items() if value is True]
    return flags


async def create_image(prompt: str) -> BytesIO:
    response = await _send_request(
        '/images/generations',
        method='POST',
        json_={'prompt': prompt, 'response_format': 'b64_json'},
    )
    data = await response.json()
    b64_json = data['data'][0]['b64_json']
    image = BytesIO()
    image.write(base64.decodebytes(b64_json.encode()))
    image.seek(0)
    return image


async def _send_request(endpoint, method='GET', token=None, params=None, json_=None):
    headers = {}

    # Build URL
    if endpoint[0] != '/':
        endpoint = f'/{endpoint}'
    url = f'{BASE_URL}{endpoint}'

    # Add token to the headers
    token = token or env.require('OPENAI_API_KEY')
    headers['Authorization'] = f'Bearer {token}'

    logger.debug('Sending request %s %s | JSON: %s | Headers: %s', method, url, json_, headers)

    res = await requests.session.request(method, url, params=params, json=json_, headers=headers)
    res.raise_for_status()
    return res
