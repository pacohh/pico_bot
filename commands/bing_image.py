from __future__ import annotations

import io
import logging

import discord
from aiohttp_requests import requests
from BingImageCreator import ImageGenAsync

from commands.base import BaseCommand
from utils import env

BING_AUTH_COOKIE = env.require('BING_AUTH_COOKIE')

logger = logging.getLogger(__name__)


class BingGenerateImageCommand(BaseCommand):
    command = '!bing_image'
    allow_pm = False

    async def handle(self, message, response_channel):
        parts = message.content.split()
        if len(parts) <= 1:
            return await response_channel.send(content='Missing prompt')
        if len(parts) <= 3:
            return await response_channel.send(content='Add more detail to your prompt')
        prompt = ' '.join(parts[1:])

        logger.info('Image generation for %s with prompt: %s', message.author, prompt)

        is_dm = isinstance(response_channel, discord.DMChannel)
        if is_dm:
            await response_channel.typing()
        else:
            loading = await response_channel.send('<a:loading:1085904578798694410>')

        try:
            images = await self.generate_images(prompt)
        except Exception as exc:
            response = await response_channel.send(f'Error: {exc.args[0]}')
            return response

        if not is_dm:
            await response_channel.delete_messages([loading])
        response = await response_channel.send(
            files=[discord.File(image, filename='image.png') for image in images],
            reference=message,
        )
        for image in images:
            image.close()
        return response

    @staticmethod
    async def generate_images(prompt: str) -> list[io.BytesIO]:
        gen = ImageGenAsync(BING_AUTH_COOKIE, quiet=True)
        urls = await gen.get_images(prompt)
        images = []
        for url in urls:
            res = await requests.session.get(url)
            data = await res.content.read()
            image = io.BytesIO(data)
            images.append(image)
        return images
