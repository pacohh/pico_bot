from __future__ import annotations

import logging
import re
from typing import Optional

import feedparser
from aiohttp_requests import requests
from markdownify import markdownify as md

import config
from background_tasks.base import CrontabDiscordTask
from utils import redis

logger = logging.getLogger(__name__)


class NewsMinimalistTask(CrontabDiscordTask):
    """
    Task that posts the daily News Minimalist newsletter to a webhook.
    """

    RSS_URL = 'https://rss.beehiiv.com/feeds/4aF2pGVAEN.xml'
    STORY_RE = re.compile(r'(?P<header>\*\*\[\d+\.\d+] .+)\n+(?P<body>.+)\n', flags=re.MULTILINE)
    REDIS_KEY = 'news_minimalist_last_timestamp'

    crontab = '*/15 * * * *'
    timezone = 'UTC'
    run_on_start = False

    def __init__(self, client):
        super().__init__(client)
        self.redis = redis.get_client()
        self._channel = None

    async def set_key(self, timestamp: str):
        await self.redis.set(self.REDIS_KEY, timestamp)

    async def get_key(self) -> Optional[str]:
        value = await self.redis.get(self.REDIS_KEY)
        return value.decode() if value else value

    async def work(self):
        try:
            data = await self.get_data()
            if data:
                await requests.session.post(config.DISCORD_NEWS_MINIMALIST_WEBHOOK_URL, json=data)
                logger.info('Sent News Minimalist')
        except Exception:
            logger.exception('Error sending News Minimalist')

    async def get_data(self) -> Optional[dict]:
        def get_feed():
            return feedparser.parse(self.RSS_URL)

        response = await self.client.loop.run_in_executor(None, get_feed)
        entry = response['entries'][0]
        timestamp = entry['published']
        link = entry['links'][0]['href']
        html = entry['content'][0]['value']

        last_timestamp = await self.get_key()
        if last_timestamp == timestamp:
            return
        await self.set_key(timestamp)

        markdown = html_to_markdown(html)

        # Parse stories and build the embeds
        stories = self.STORY_RE.findall(markdown)
        stories = stories[:10]  # There is a limit of 10 embeds
        embeds = self.build_embeds(stories, timestamp)

        return {
            'content': f'[Read online]({link})',
            'embeds': embeds,
            'username': 'News Minimalist',
            'avatar_url': 'https://www.newsminimalist.com/_next/image?url=%2F_next%2Fstatic%2Fmedia%2Ficon.168b8766.png&w=256&q=75',
            'attachments': [],
        }

    def build_embeds(self, stories: list[tuple[str, str]], timestamp: str) -> list[dict]:
        embeds = []
        for header, body in stories:
            embeds.append(
                {
                    'description': f'{header}\n\n{body}',
                    'color': 12635742,
                    'footer': {
                        'icon_url': 'https://www.newsminimalist.com/_next/image?url=%2F_next%2Fstatic%2Fmedia%2Ficon.168b8766.png&w=96&q=75'
                    },
                    'timestamp': timestamp,
                }
            )
        return embeds


def html_to_markdown(html: str) -> str:
    result = html.replace('\n', ' ')
    result = md(result).strip()
    return result
