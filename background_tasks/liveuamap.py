from __future__ import annotations

import asyncio
import logging
import re

from aiohttp_requests import requests
from bs4 import BeautifulSoup, Tag

import config
from background_tasks.base import SleepDiscordTask
from utils import redis

logger = logging.getLogger(__name__)


class LiveUaMap(SleepDiscordTask):
    URL = 'https://israelpalestine.liveuamap.com/'
    HEADERS = {
        'authority': 'israelpalestine.liveuamap.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'cookie': 'PHPSESSID=9psaoqk56gcgvvggrd54o61db1; _csrf-frontend=e8a9401e89acacee67ce4ffaad62605dd7fa873bab0c2aebfb652fe22c8641c9a%3A2%3A%7Bi%3A0%3Bs%3A14%3A%22_csrf-frontend%22%3Bi%3A1%3Bs%3A32%3A%22%D0%13%7EB+si%FB%98%E3%246%D0%15%EF%0F%2B%152%AF%3E%84%DD%BD%95%21%E2%3B%F3%08%BE%AC%22%3B%7D; regioncookie=44f76ac94e9bc39377e6f96e5f04e9b07c2b63cd731df3335579b956bb5cc5e8a%3A2%3A%7Bi%3A0%3Bs%3A12%3A%22regioncookie%22%3Bi%3A1%3Bs%3A3%3A%22yes%22%3B%7D',
        'referer': 'https://liveuamap.com/',
        'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    }
    EVENT_CAT_RE = re.compile(r'(cat\d+)')
    REDIS_KEY = 'liveuamap_israelpalestine_seen_events'
    CATEGORY_COLORS = {
        'cat1': 12867899,
        'cat2': 3433927,
        'cat5': 14735833,
        'cat11': 15697715,
    }

    sleep_seconds = (90, 150)

    def __init__(self, client):
        super().__init__(client)
        self.redis = redis.get_client()

    async def work(self):
        events = await self.get_new_events()
        embeds = list(map(self.build_event_embed, reversed(events)))
        await self.post_events(embeds)

    async def get_key(self) -> set[str]:
        keys = await self.redis.get(self.REDIS_KEY)
        if not keys:
            return set()
        return set(keys.decode().split(','))

    async def set_key(self, event_ids: set[str]) -> None:
        value = ','.join(event_ids)
        await self.redis.set(self.REDIS_KEY, value)

    async def get_new_events(self) -> list[dict]:
        events = await self.get_events()
        event_ids = {event['id'] for event in events}
        seen_event_ids = await self.get_key()
        new_event_ids = event_ids - seen_event_ids
        new_events = [event for event in events if event['id'] in new_event_ids]
        await self.set_key(event_ids)
        return new_events

    async def get_events(self) -> list[dict]:
        html = await self._send_request()
        soup = BeautifulSoup(html, features='lxml')
        events = soup.find_all('div', {'class': 'event'})
        events = list(map(self._parse_event, events))
        return events

    def _parse_event(self, event: Tag):
        category = self.EVENT_CAT_RE.search(str(event.attrs['class']))
        category = category.group() if category else None

        event_id = event.attrs['data-id']
        link = event.attrs['data-link']
        twitpic = event.attrs['data-twitpic'] or None

        date_add = event.find('span', {'class': 'date_add'})
        date_add = date_add.text if date_add else None

        title = event.find('div', {'class': 'title'})
        title = title.text if title else None

        image = event.find('div', {'class': 'img'}).find('img')
        image = image.attrs['src'] if image else None

        place = event.find('div', {'class': 'top-right'})
        place = place.text if place else None

        return {
            'category': category,
            'id': event_id,
            'link': link,
            'date_add': date_add,
            'title': title,
            'place': place,
            'image': twitpic or image,
        }

    async def _send_request(self) -> str:
        res = await requests.session.get(self.URL, headers=self.HEADERS)
        res.raise_for_status()
        html = await res.text()
        return html

    def build_event_embed(self, event: dict) -> dict:
        embed = {
            'description': f"### [[↗︎]]({event['link']}) {event['title']}",
        }
        if event['image']:
            embed['image'] = {'url': event['image']}
        if event['place']:
            embed['footer'] = {'text': f"📍 {event['place']}"}
        if color := self.CATEGORY_COLORS.get(event['category']):
            embed['color'] = color

        return embed

    async def post_events(self, embeds: list[dict]) -> None:
        for embed in embeds:
            data = {
                'content': None,
                'embeds': [embed],
                'username': 'Liveuamap',
                'avatar_url': 'https://cdn.discordapp.com/attachments/1163233625312075806/1163247566557819060/ua_cropped.png',
            }
            res = await requests.session.post(
                config.DISCORD_LIVEUAMAP_ISRAEL_PALESTINE_URL, json=data
            )
            if res.status >= 400:
                logger.error('Error sending embeds. Status code %d. Data: %s', res.status, data)
            await asyncio.sleep(1)  # Don't spam too fast
