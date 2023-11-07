from __future__ import annotations

import asyncio
import io
import logging
import random
import re

import discord
import httpx
import regex
import requests.utils as requests_utils
from aiohttp_requests import requests

from commands.base import BaseCommand
from utils import env, openai

BING_AUTH_COOKIE = env.require('BING_AUTH_COOKIE')

logger = logging.getLogger(__name__)


class GenerateImageCommand(BaseCommand):
    re_command = re.compile(r'^!(img|image|imagine)\b')
    allow_pm = False

    async def handle(self, message, response_channel):
        parts: list[str] = message.content.split()
        if len(parts) <= 1:
            return await response_channel.send(content='Missing prompt')
        if len(parts) <= 3:
            return await response_channel.send(content='Add more detail to your prompt')

        hd = False
        if parts[0].lower() == 'hd':
            hd = True
            parts.pop(0)
        if parts[1].lower() == 'hd':
            hd = True
            parts.pop(1)

        style = 'vivid'
        if parts[0].lower() == 'standard':
            style = 'standard'
            parts.pop(0)
        if parts[1].lower() == 'standard':
            style = 'standard'
            parts.pop(1)

        prompt = ' '.join(parts[1:])

        logger.info(
            'Image generation. User = %s. Style = %s. HD = %b. Prompt: %s',
            message.author,
            style,
            hd,
            prompt,
        )

        is_dm = isinstance(response_channel, discord.DMChannel)
        loading = None
        if is_dm:
            await response_channel.typing()
        else:
            loading = await response_channel.send('<a:loading:1085904578798694410>')

        try:
            images = await openai.create_images(prompt, style=style, hd=hd, user=message.author.name)
        except Exception as exc:
            if loading:
                await response_channel.delete_messages([loading])
            response = await response_channel.send(f'Error: {exc.args[0]}', reference=message)
            return response

        if loading:
            await response_channel.delete_messages([loading])

        cost_per = 0.08 if hd else 0.04
        cost = cost_per * len(images)

        response = await response_channel.send(
            content=f'**Prompt:** {prompt}\nStyle: {style}. HD: {hd}. Cost: ${cost}',
            files=[discord.File(image, filename='image.png') for image in images],
            reference=message,
        )
        for image in images:
            image.close()
        return response

