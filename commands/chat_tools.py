from __future__ import annotations

import logging
from io import BytesIO

import discord

from utils import openai

TOOL_DEFINITIONS = [
    {
        'type': 'function',
        'function': {
            'name': 'generate_images',
            'description': 'Create images from a text-only prompt.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'size': {
                        'type': 'string',
                        'enum': ['1792x1024', '1024x1024', '1024x1792'],
                        'description': 'The resolution of the requested image, which can be wide, square, or tall. Use 1024x1024 (square) as the default unless the prompt suggests a wide image, 1792x1024, or a full-body portrait, in which case 1024x1792 (tall) should be used instead. Always include this parameter in the request.',
                    },
                    'prompts': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'The user\'s original image description. If the user does not suggest a number of captions to create, create two of them. If creating multiple captions, make them as diverse as possible. If the user requested modifications to previous images, the captions should not simply be longer, but rather it should be refactored to integrate the suggestions into each of the captions. Generate no more than 4 images, even if the user requests more.',
                    },
                },
            },
        },
    }
]

logger = logging.getLogger(__name__)


async def generate_images(client: discord.Client, prompts: list[str], size: str) -> list[BytesIO]:
    images = []
    tasks = [client.loop.create_task(openai.create_images(prompt, size=size)) for prompt in prompts]
    for task in tasks:
        try:
            res = await task
            _, image = res[0]
            images.append(image)
        except:
            logger.exception('Error generating image')
    return images
