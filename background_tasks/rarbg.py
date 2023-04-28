from __future__ import annotations

import logging

import discord
import imdb
from imdb.helpers import resizeImage

import config
from background_tasks.base import CrontabDiscordTask
from utils import numbers, rarbg_api, redis
from utils.datetime import utc_now

REDIS_KEY = 'rarbg_handled_movies'


logger = logging.getLogger(__name__)


class RarbgNewMoviesTask(CrontabDiscordTask):
    """
    Task that checks for new movies on Rarbg and post them to discord.
    """

    crontab = '0 * * * * 0'
    run_on_start = True

    def __init__(self, client):
        super().__init__(client)
        self.redis = redis.get_client()
        self._channel = None

    @property
    def channel(self):
        if not self._channel:
            self._channel = self.client.get_channel(config.DISCORD_MOVIES_CHANNEL_ID)
        return self._channel

    async def work(self):
        new_movie_ids = await self.get_new_movie_ids()

        logger.info('Got %d new movies: %s', len(new_movie_ids), new_movie_ids)

        for movie_id in new_movie_ids:
            await self.handle_new_movie(movie_id)

    async def get_new_movie_ids(self) -> set[str]:
        rarbg_ids = await self.get_rarbg_movie_ids()
        new_ids = await self.filter_seen_ids(rarbg_ids)
        return new_ids

    @staticmethod
    async def get_rarbg_movie_ids() -> set[str]:
        data = await rarbg_api.request(
            {
                'mode': 'list',
                'category': '50;51;46',
                'sort': 'seeders',
                'format': 'json_extended',
                'limit': 50,
            }
        )
        movie_ids = set()
        for movie in data.get('torrent_results', []):
            imdb_id = movie['episode_info']['imdb']
            if imdb_id:
                movie_ids.add(imdb_id)
        return movie_ids

    async def filter_seen_ids(self, movie_ids: set[str]) -> set[str]:
        new_ids = set()
        for movie_id in movie_ids:
            if not await self.redis.sismember(REDIS_KEY, movie_id):
                new_ids.add(movie_id)
        return new_ids

    async def handle_new_movie(self, imdb_id: str) -> None:
        def get_movie():
            return imdb.Cinemagoer().get_movie(imdb_id[2:])

        logger.info('Handling movie %s', imdb_id)

        movie = await self.client.loop.run_in_executor(None, get_movie)
        data = movie.data
        url = f'https://www.imdb.com/title/{imdb_id}/'

        # Ignore old movies
        current_year = utc_now().year
        if data['year'] < current_year - 1:
            logger.info("Ignoring movie %s from %d, it's too old", imdb_id, data['year'])
            await self.redis.sadd(REDIS_KEY, imdb_id)
            return

        embed = discord.Embed()
        embed.title = data['title']
        embed.url = url
        embed.set_image(url=resizeImage(data['cover url'], height=300))
        embed.add_field(
            name='Rating',
            value=f"{data['rating']}/10 ({numbers.human_format(data['votes'])})",
            inline=True,
        )
        embed.add_field(name='Year', value=data['year'], inline=True)
        embed.add_field(name='Genres', value=', '.join(data['genres']), inline=False)
        await self.channel.send(
            content=f'<@{config.DISCORD_TARMO_USER_ID}> new movie:',
            embed=embed,
        )
        await self.redis.sadd(REDIS_KEY, imdb_id)

        logger.info('Handled movie %s', imdb_id)
