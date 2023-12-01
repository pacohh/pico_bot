import logging
from asyncio import Lock
from collections import defaultdict

import discord

logger = logging.getLogger(__name__)


class DeletePreviousMixin:
    """
    After handling a message, delete all previous responses to the command.
    """

    async def post_handle(self, message, response_channel, response):
        if not response:
            return
        async with Lock():
            channel_responses = self.previous_responses[message.channel]
            await self.delete_channel_responses(message.channel, channel_responses)
            channel_responses.clear()
            channel_responses.add(response)

        await super().post_handle(message, response_channel, response)

    async def add_response(self, response):
        if not response:
            return
        async with Lock():
            self.previous_responses[response.channel].add(response)

    async def delete_channel_responses(self, channel, channel_responses):
        try:
            await channel.delete_messages(channel_responses)
        except discord.errors.NotFound:
            logger.warning(
                'Message not found while trying to delete messages %s',
                [response.id for response in self.previous_responses],
            )
