from __future__ import annotations

import datetime
import logging
import re

from aiohttp_requests import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

import config
from background_tasks.base import CrontabDiscordTask
from utils import redis

APOD_URL = 'https://apod.nasa.gov/apod/'
LOCAL_LINK_RE = re.compile(r'\((ap\d+\.html)\)')
EXPLANATION_MAX_LEN = 4000

logger = logging.getLogger(__name__)


class AstronomyPictureOfTheDayTask(CrontabDiscordTask):
    """
    Task that posts the Astronomy Picture of the Day to a webhook.
    """

    crontab = '0 5 * * *'
    run_on_start = False

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
        soup = BeautifulSoup(html, features='lxml')

        img_src = f"{APOD_URL}{soup.find('img').parent['href']}"
        date = soup.select('center:nth-of-type(1) > p:nth-of-type(2)')[0].text.strip()
        title = soup.select('center:nth-of-type(2) > b:nth-of-type(1)')[0].text.strip()

        today = datetime.date.today()
        url = f"{APOD_URL}ap{today.strftime('%y%m%d')}.html"

        credit_html = str(soup.select('center:nth-of-type(2)')[0])
        credit_html = credit_html.split('<br/>', 1)[1]
        credit = html_to_markdown(credit_html)

        explanation_html = str(soup.select('body > p:nth-of-type(1)')[0])
        explanation = html_to_markdown(explanation_html)

        description = f'\n{credit}\n\n{explanation}'
        description = description.replace(':** ', '**\n')

        if len(description) > EXPLANATION_MAX_LEN:
            description = f'{description[:EXPLANATION_MAX_LEN]}…'

        return {
            'content': None,
            'embeds': [
                {
                    'title': title,
                    'description': description,
                    'url': url,
                    'color': 1784972,
                    'image': {'url': img_src},
                }
            ],
            'username': 'Astronomy Picture of the Day',
            'avatar_url': 'https://gpm.nasa.gov/sites/default/files/document_files/NASA-Logo-Large.png',
            'attachments': [],
        }


def html_to_markdown(html: str) -> str:
    result = html.replace('\n', ' ')
    result = md(result).strip()
    result = LOCAL_LINK_RE.sub(rf'({APOD_URL}\1)', result)
    return result
