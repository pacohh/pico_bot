from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

import discord
from aiohttp_requests import requests
from openai import AsyncOpenAI

from commands.base import BaseCommand

logger = logging.getLogger(__name__)


class TtsCommand(BaseCommand):
    command = '!tts'
    allow_pm = False

    VALID_VOICES = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']

    def __init__(self, client):
        super().__init__(client)
        self.openai_client = AsyncOpenAI()

    async def handle(self, message, response_channel: discord.TextChannel):
        parts: list[str] = message.content.split()
        text_attachment = self.extract_text_attachment(message)

        voice = 'alloy'
        if len(parts) >= 2 and parts[1].lower() in self.VALID_VOICES:
            voice = parts[1].lower()
            parts.pop(1)

        # Input checks
        if not text_attachment:
            if len(parts) <= 1:
                return await response_channel.send(
                    content=f'!tts [{"|".join(self.VALID_VOICES)}] text\n'
                            f'[Voice smaples](https://platform.openai.com/docs/guides/text-to-speech/voice-options)',
                    suppress_embeds=True,
                )
            if len(parts) <= 3:
                return await response_channel.send(content='Text is too short', reference=message)

        else:
            if text_attachment.size > 6000:
                return await response_channel.send(content='Error: more than 4,096 characters', reference=message)

        if text_attachment:
            text = await self.load_text(text_attachment)
        else:
            text = ' '.join(parts[1:])

        if len(text) > 4096:
            return await response_channel.send(content='Error: more than 4,096 characters', reference=message)

        logger.info(
            'TTS generation. User = %s. Voice = %s. Text (%d chars): %s',
            message.author,
            voice,
            len(text),
            text[:300],
        )

        is_dm = isinstance(response_channel, discord.DMChannel)
        loading = None
        if is_dm:
            await response_channel.typing()
        else:
            loading = await response_channel.send('<a:loading:1085904578798694410>')

        try:
            response = await self.openai_client.audio.speech.create(
                model='tts-1',
                voice=voice,
                input=text,
            )
            file = BytesIO()
            file.write(await response.aread())
            file.seek(0)
        except Exception:
            logger.exception('Error creating TTS')
            if loading:
                await response_channel.delete_messages([loading])
            response = await response_channel.send(f'Error creating TTS', reference=message)
            return response

        if loading:
            await response_channel.delete_messages([loading])

        response = await response_channel.send(
            files=[discord.File(file, filename='tts.mp3')],
            reference=message,
        )
        file.close()
        return response

    @staticmethod
    def extract_text_attachment(message: discord.Message) -> Optional[discord.Attachment]:
        for attachment in message.attachments:
            if attachment.content_type.startswith('text/plain'):
                return attachment

    @staticmethod
    async def load_text(attachment: discord.Attachment) -> str:
        res = await requests.session.get(attachment.url)
        text = await res.text()
        return text
