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
        if not self.is_correct_command(message):
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

    def is_correct_command(self, message):
        return message.content.lower().startswith(self.command.lower())

    def get_message_member(self, message):
        member = message.author
        if not isinstance(member, discord.Member):
            guild = self.client.get_guild(config.DISCORD_SERVER_ID)
            member = guild.get_member(member.id)
        return member

    @error_handler
    async def handle_message(self, message, response_channel=None):
        """Handle the message.

        If a response_channel is given the response will be sent there instead
        of to the message's channel.
        """
        channel = self.get_response_channel(message, response_channel)
        await self.pre_handle(message, channel)
        response = await self.handle(message, channel)
        await self.post_handle(message, channel, response)
        if self.response_ttl is not None and response:
            await self.delete_response(response)
        return response

    def get_response_channel(self, message, response_channel):
        channel = response_channel or message.channel
        if not isinstance(channel, (discord.TextChannel, discord.DMChannel)):
            channel = self.client.get_channel(channel)
        return channel

    async def pre_handle(self, message, response_channel):
        pass

    async def handle(self, message, response_channel):
        raise NotImplementedError()

    async def post_handle(self, message, response_channel, response):
        pass

    async def delete_response(self, response):
        await sleep(self.response_ttl)
        await response.delete()
