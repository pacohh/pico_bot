import logging
from abc import ABC
from asyncio import sleep

import discord

import config
from utils.discord import roles

logger = logging.getLogger(__name__)


def error_handler(method):
    async def wrapper(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except:
            logger.exception('Unexpected exception')

    return wrapper


class BaseCommand:
    command = None
    allow_pm = False
    channels = None
    roles = None
    response_ttl = None

    def __init__(self, client):
        self.client = client

    async def should_handle(self, message):
        """Check if the command should handle the message."""

        # Don't handle messages from bots
        if message.author.bot:
            return False

        # Check that it's the right command
        if not message.content.startswith(self.command):
            return False

        # Check the channel or PM allowed
        is_correct_channel = message.channel.id in self.channels if self.channels else True
        is_pm = isinstance(message.channel, discord.abc.PrivateChannel) and self.allow_pm
        if not is_correct_channel and not is_pm:
            return False

        # Check that the member has the required role
        member = self.get_message_member(message)
        is_correct_role = roles.has_any_roles(member, self.roles) if self.roles else True
        if not is_correct_role:
            return False

        return True

    def get_message_member(self, message):
        member = message.author
        if not isinstance(member, discord.Member):
            guild = self.client.get_guild(config.DISCORD_SERVER_ID)
            member = guild.get_member(member.id)
        return member

    @error_handler
    async def handle_interaction(self, interaction: discord.Interaction, *args):
        """Handle the interaction."""
        response = await self.handle(interaction, *args)
        if self.response_ttl is not None and response:
            await self.delete_response(response)
        return response

    async def handle(self, interaction, *args):
        raise NotImplementedError()

    async def delete_response(self, response):
        await sleep(self.response_ttl)
        await response.delete()
