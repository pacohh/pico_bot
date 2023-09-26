from __future__ import annotations

import logging

import discord

from commands.base import BaseCommand
from utils import env, openai

API_KEY = env.require('OPENAI_API_KEY')

logger = logging.getLogger(__name__)


class GenerateImageCommand(BaseCommand):
    command = '!image'
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

        image = await openai.create_image(prompt)

        if not is_dm:
            await response_channel.delete_messages([loading])
        response = await response_channel.send(
            file=discord.File(image, filename='image.png'),
            reference=message,
        )
        image.close()
        return response
