from __future__ import annotations

import logging
import random
import re

import discord
from aioredis import Redis
from openai.types.beta.threads import MessageContentText, MessageContentImageFile
from aiohttp_requests import requests

import config
from commands.base import BaseCommand
from helpers.chatter import Chatter
import utils.redis
import utils.urls
from utils import emojis
from utils.openai import describe_image

REDIS_TRIGGER_FREQ_KEY = 'chatter_trigger_frequency'
DEFAULT_TRIGGER_FREQ = 50

IMAGE_CONTENT_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
IMAGE_MAX_SIZE = 20 * 1024 * 1024  # 20 MB

AVAILABLE_EMOTES = {
    ':lul:': emojis.LUL,
    ':couchStare:': emojis.COUCH_STARE,
    ':huh:': emojis.HUH,
    ':hmmmmcat:': emojis.HMMMMCAT,
    ':happymonke:': emojis.HAPPY_MONKE,
    ':kekSalute:': emojis.KEK_SALUTE,
}


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
        contents = await self.parse_user_message(message)
        for content in contents:
            await self.chatter.add_message(content)

        logger.info('Message added: %s', content)

        freq = await get_trigger_freq(self.redis)
        random_run = random.randint(1, freq) == 1
        force_run = 'pico' in content.lower()
        if force_run or random_run:
            logger.info('Chatter run triggered')
            await response_channel.typing()
            await self.run_chatter(response_channel)

    async def parse_user_message(self, message: discord.Message) -> list[str]:
        contents = []

        content = await self.replace_image_urls(message.clean_content)
        contents.append(content)

        attachment_descriptions = await self.describe_attachments(message.attachments)
        contents.extend(attachment_descriptions)

        user = message.author.nick or message.author.display_name
        for idx, content in enumerate(contents):
            contents[idx] = f'{user}: {content}'

        return contents

    @staticmethod
    async def replace_image_urls(text: str) -> str:
        # Find URLs in the text
        urls = utils.urls.extract_urls(text)

        # Expand tenor URLs
        for idx, url in enumerate(urls):
            if utils.urls.is_tenor_url(url):
                new_url = f'{url}.gif'
                urls[idx] = new_url
                text = text.replace(url, new_url)

        # Check which URLs are for valid images
        image_urls = []
        for url in urls:
            response = await requests.session.head(url, allow_redirects=True)
            if (
                response.content_type in IMAGE_CONTENT_TYPES
                and response.content_length <= IMAGE_MAX_SIZE
            ):
                final_url = response.url.human_repr()
                if final_url != url:
                    text = text.replace(url, final_url)
                image_urls.append(final_url)

        # Replace image URLs by image descriptions
        for url in image_urls:
            try:
                description = await describe_image(url)
                description = description.replace('"', r'\"')
                image = f'{{"type": "image", "url": "{url}", "description": "{description}"}}'
                text = text.replace(url, image)
            except:
                pass

        return text

    @staticmethod
    async def describe_attachments(attachments: list[discord.Attachment]) -> list[str]:
        image_urls = []
        for attachment in attachments:
            if attachment.content_type not in IMAGE_CONTENT_TYPES:
                continue
            if attachment.size > IMAGE_MAX_SIZE:
                continue
            image_urls.append(attachment.url)

        descriptions = []
        for url in image_urls:
            try:
                description = await describe_image(url)
                description = description.replace('"', r'\"')
                image = f'{{"type": "image", "url": "{url}", "description": "{description}"}}'
                descriptions.append(image)
            except:
                pass

        return descriptions

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
        text = message_content.text.value
        for emote_string, emote in AVAILABLE_EMOTES.items():
            text = text.replace(emote_string, emote)
        await response_channel.send(text)


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
