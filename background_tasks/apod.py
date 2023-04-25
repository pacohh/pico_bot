from __future__ import annotations

import logging
import re

from aiohttp_requests import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

import config
from background_tasks.base import CrontabDiscordTask
from utils import redis

APOD_URL = 'https://apod.nasa.gov/apod/'
LOCAL_LINK_RE = re.compile(r'\((ap\d+\.html\))')

logger = logging.getLogger(__name__)


class AstronomyPictureOfTheDayTask(CrontabDiscordTask):
    """
    Task that posts the Astronomy Picture of the Day to a webhook.
    """

    crontab = '0 5 * * 0'
    run_on_start = True

    def __init__(self, client):
        super().__init__(client)
        self.redis = redis.get_client()
        self._channel = None

    async def work(self):
        try:
            data = await self.get_data()
            await requests.session.post(config.DISCORD_APOC_WEBHOOK_URL, json=data)
        except Exception:
            logger.exception('Error sending APOD')
        else:
            logger.info('Sent APOD')

    async def get_data(self):
        response = await requests.session.get(APOD_URL)
        response.raise_for_status()
        html = await response.text()
        soup = BeautifulSoup(html)

        img_src = f"{APOD_URL}{soup.find('img').parent['href']}"
        date = soup.select('center:nth-of-type(1) > p:nth-of-type(2)')[0].text.strip()
        title = soup.select('center:nth-of-type(2) > b:nth-of-type(1)')[0].text.strip()

        explanation_html = str(soup.select('body > p:nth-of-type(1)')[0])
        explanation_html = explanation_html.replace('\n', ' ')
        explanation = md(explanation_html).strip()
        explanation = explanation[18:]
        explanation = LOCAL_LINK_RE.sub(rf'({APOD_URL}\1)', explanation)

        return {
            'content': None,
            'embeds': [
                {
                    'title': title,
                    'description': explanation,
                    'color': 1784972,
                    'image': {'url': img_src},
                }
            ],
            'username': 'Astronomy Picture of the Day',
            'avatar_url': 'https://gpm.nasa.gov/sites/default/files/document_files/NASA-Logo-Large.png',
            'attachments': [],
        }
