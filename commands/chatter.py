from __future__ import annotations

import logging
import random
import re

import discord
from aioredis import Redis
from openai.types.beta.threads import MessageContentText, MessageContentImageFile

import config
from commands.base import BaseCommand
from helpers.chatter import Chatter
import utils.redis

REDIS_TRIGGER_FREQ_KEY = 'chatter_trigger_frequency'
DEFAULT_TRIGGER_FREQ = 50

logger = logging.getLogger(__name__)


async def set_trigger_freq(redis: Redis, freq: int) -> None:
    await redis.set(REDIS_TRIGGER_FREQ_KEY, freq)


async def get_trigger_freq(redis: Redis) -> int:
    redis_val = await redis.get(REDIS_TRIGGER_FREQ_KEY)
    return int(redis_val or DEFAULT_TRIGGER_FREQ)


class ChatterCommand(BaseCommand):
    command = ''
    allow_pm = False
    channels = {config.DISCORD_LOUNGE_CHANNEL_ID}

    def __init__(self, client):
        super().__init__(client)
        self.chatter: Chatter = self.client.chatter
        self.redis = utils.redis.get_client()

    async def handle(self, message: discord.Message, response_channel: discord.TextChannel) -> None:
        content = f'{message.author.display_name}: {message.content}'
        await self.chatter.add_message(content)

        logger.info('Message added: %s', content)

        freq = await get_trigger_freq(self.redis)
        random_run = random.randint(1, freq) == 1
        force_run = 'pico' in content.lower()
        if force_run or random_run:
            logger.info('Chatter run triggered')
            await response_channel.typing()
            await self.run_chatter(response_channel)
            chatter_messages = await self.chatter.run()
            for chatter_message in chatter_messages:
                await response_channel.send(chatter_message.conte)

    async def run_chatter(self, response_channel: discord.TextChannel) -> None:
        chatter_messages = await self.chatter.run()
        for chatter_message in chatter_messages:
            for message_content in chatter_message.content:
                if isinstance(message_content, MessageContentText):
                    await self._handle_text_message(response_channel, message_content)
                elif isinstance(message_content, MessageContentImageFile):
                    # This assistant shouldn't generate images
                    pass

    @staticmethod
    async def _handle_text_message(
        response_channel: discord.TextChannel,
        message_content: MessageContentText,
    ) -> None:
        await response_channel.send(message_content.text.value)


class ChatterFrequencyCommand(BaseCommand):
    command = '!cf'
    allowed_users = [config.DISCORD_TARMO_USER_ID]

    def __init__(self, client):
        super().__init__(client)
        self.redis = utils.redis.get_client()

    async def handle(self, message: discord.Message, response_channel: discord.TextChannel):
        parts: list[str] = message.content.split()
        old_freq = await get_trigger_freq(self.redis)
        if len(parts) <= 1:
            return await response_channel.send(
                content=f'Chatter has 1/{old_freq} chances of replying'
            )

        try:
            new_freq = int(parts[1])
        except ValueError:
            return await response_channel.send(
                content=f'Chatter has 1/{old_freq} chances of replying'
            )

        if new_freq < 1:
            return await response_channel.send(content='Frequency should be at least 1')

        try:
            await set_trigger_freq(self.redis, new_freq)
        except:
            return await response_channel.send(content='Error setting chatter frequency')

        return await response_channel.send(
            content=f'Chatter frequency set. It now has 1/{new_freq} chances of replying.'
        )
