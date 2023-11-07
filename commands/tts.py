from __future__ import annotations

import logging
import re

import discord

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
        if parts[0].lower() == 'natural':
            style = 'natural'
            parts.pop(0)
        if parts[1].lower() == 'natural':
            style = 'natural'
            parts.pop(1)

        prompt = ' '.join(parts[1:])

        logger.info(
            'Image generation. User = %s. Style = %s. HD = %s. Prompt: %s',
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
        except Exception:
            logger.exception('Error creating image')
            if loading:
                await response_channel.delete_messages([loading])
            response = await response_channel.send(f'Error creating images', reference=message)
            return response

        if loading:
            await response_channel.delete_messages([loading])

        revised_prompt, image = images[0]
        response = await response_channel.send(
            content=f'**Prompt:** {prompt}\n'
                    f'**Revised prompt:** {revised_prompt}\n'
                    f'**Style:** `{style}` | **HD:** `{hd}`',
            files=[discord.File(image, filename='image.png')],
            reference=message,
        )
        image.close()
        return response
