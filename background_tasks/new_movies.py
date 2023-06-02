from __future__ import annotations

import itertools
import logging

import discord

import config
from background_tasks.base import CrontabDiscordTask
from utils import redis, yts_api
from utils.datetime import utc_now

REDIS_KEY = 'rarbg_handled_movies'

logger = logging.getLogger(__name__)


class YtsNewMoviesTask(CrontabDiscordTask):
    """
    Task that checks for new movies on YTS and post them to discord.
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
        new_movies = await self.get_new_movies()

        logger.info('Got %d new movies', len(new_movies))

        for movie in new_movies:
            await self.handle_new_movie(movie)

    async def get_new_movies(self) -> list[dict]:
        movies = await self.get_movies()
        new_movies = await self.filter_seen_ids(movies)
        return new_movies

    @staticmethod
    async def get_movies() -> list[dict]:
        year = utc_now().year
        movies = []
        movies_this_year = await yts_api.list_all_movies(str(year))
        movies_prev_year = await yts_api.list_all_movies(str(year - 1))
        for movie in itertools.chain(movies_this_year, movies_prev_year):
            torrents = {torrent['quality']: torrent for torrent in movie['torrents'] if torrent}
            if '2160p' not in torrents:
                logger.error("Movie does't have 2160 torrent. Movie: %s", movie)
                continue
            torrent = torrents['2160p']
            movies.append(
                {
                    'imdb_id': movie['imdb_code'],
                    'title': movie['title_english'],
                    'year': movie['year'],
                    'genres': movie['genres'],
                    'image': movie['large_cover_image'],
                    'rating': movie['rating'],
                    'quality': torrent['quality'],
                    'size': torrent['size'],
                    'peers': torrent['peers'],
                    'seeds': torrent['seeds'],
                }
            )

        # Sort by number of seeds
        movies.sort(key=lambda movie_: movie_['seeds'], reverse=True)
        # Only return the top N movies
        movies = movies[:30]

        return movies

    async def filter_seen_ids(self, movies: list[dict]) -> list[dict]:
        new_movies = []
        for movie in movies:
            movie_id = movie['imdb_id']
            if not await self.redis.sismember(REDIS_KEY, movie_id):
                new_movies.append(movie)
        return new_movies

    async def handle_new_movie(self, movie: dict) -> None:
        imdb_id = movie['imdb_id']

        logger.info('Handling movie %s', imdb_id)

        embed = discord.Embed()
        embed.title = movie['title']
        embed.url = f'https://www.imdb.com/title/{imdb_id}/'
        embed.set_image(url=movie['image'])
        embed.add_field(
            name='Rating',
            value=f"{movie['rating']}/10",
            inline=True,
        )
        embed.add_field(name='Year', value=movie['year'], inline=True)
        embed.add_field(name='Genres', value=', '.join(movie['genres']), inline=False)
        embed.set_footer(
            text=f'{movie["quality"]} • {movie["size"]} • P/S: {movie["peers"]} / {movie["seeds"]}'
        )
        await self.channel.send(
            content=f'<@{config.DISCORD_TARMO_USER_ID}> new movie:',
            embed=embed,
        )
        await self.redis.sadd(REDIS_KEY, imdb_id)

        logger.info('Handled movie %s', imdb_id)
