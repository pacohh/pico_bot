from __future__ import annotations

import asyncio
import logging

from aiohttp_requests import requests

import config
import utils.datetime
import utils.redis
import utils.urls
from background_tasks.base import CrontabDiscordTask

logger = logging.getLogger(__name__)


class HackerNewsTask(CrontabDiscordTask):
    URL = 'https://hn.algolia.com/api/v1/search_by_date?numericFilters=points>=300&page={}'
    REDIS_KEY = 'hacker_news_seen_items'
    REDIS_MAX_LENGTH = 200

    crontab = '*/5 * * * *'
    run_on_start = False

    def __init__(self, client):
        super().__init__(client)
        self.redis = utils.redis.get_client()

    async def get_seen_item_ids(self) -> list[int]:
        value = await utils.redis.get_fifo_list(self.redis, self.REDIS_KEY)
        return value

    async def set_seen_item_ids(self, item_ids: list[int]) -> None:
        await utils.redis.set_fifo_list(self.redis, self.REDIS_KEY, item_ids, self.REDIS_MAX_LENGTH)

    async def work(self):
        items = await self.get_new_items()
        logger.info('Found %d new items', len(items))
        embeds = [self.build_embed(item) for item in items]
        await self.post_embeds(embeds)

    async def get_new_items(self) -> list[dict]:
        items = await self.get_items()

        # Filter new items only
        item_ids = [item['id'] for item in items]
        seen_item_ids = await self.get_seen_item_ids()
        new_item_ids = set(item_ids) - set(seen_item_ids)
        new_items = [item for item in items if item['id'] in new_item_ids]

        # Update the seen items ids in redis
        seen_item_ids.extend(new_item_ids)
        await self.set_seen_item_ids(seen_item_ids)

        return new_items

    async def get_items(self) -> list[dict]:
        # Request 5 pages of items, i.e. last 100 items (20 items per page)
        raw_hits = []
        for page_num in range(5):
            data = await self._send_request(page_num)
            raw_hits.extend(data.get('hits', []))

        hits = []
        for hit in raw_hits:
            hits.append(
                {
                    'id': int(hit['objectID']),
                    'title': hit['title'],
                    'url': hit.get('url'),
                    'hn_url': f"https://news.ycombinator.com/item?id={hit['objectID']}",
                    'num_comments': hit['num_comments'],
                    'points': hit['points'],
                }
            )
        hits.reverse()
        return hits

    async def _send_request(self, page_num: int) -> dict:
        url = self.URL.format(page_num)
        res = await requests.session.get(url)
        res.raise_for_status()
        data = await res.json()
        return data

    @staticmethod
    def build_embed(event: dict) -> dict:
        title = event['title']
        url = event['url']
        hn_url = event['hn_url']
        num_comments = event['num_comments']
        url_part = ''
        if url:
            domain = utils.urls.get_domain(url)
            url_part = f' [({domain})]({url})'
        embed = {
            'description': f"### {title}{url_part}\n[{num_comments} comments]({hn_url})",
            'color': 15560749,
        }
        return embed

    @staticmethod
    async def post_embeds(embeds: list[dict]) -> None:
        for embed in embeds:
            data = {
                'content': None,
                'embeds': [embed],
                'username': 'HackerNews',
                'avatar_url': 'https://cdn.discordapp.com/attachments/780877442256470058/1163766513979887636/images.png',
            }
            res = await requests.session.post(config.DISCORD_HACKERNEWS_WEBHOOK_URL, json=data)
            if res.status >= 400:
                logger.error('Error sending embed. Status code %d. Data: %s', res.status, data)
            await asyncio.sleep(1)  # Don't spam too fast
