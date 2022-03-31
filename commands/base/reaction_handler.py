import logging

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


class BaseReactionHandler:
    emoji = None
    allow_pm = False
    channels = None
    roles = None

    def __init__(self, client):
        self.client = client

    async def should_handle(self, reaction, user):
        """Check if the command should handle the message."""
        message = reaction.message

        # Don't handle messages from bots
        if user.bot:
            return False

        # Check that it's the correct emoji
        emoji = reaction.emoji
        if isinstance(emoji, str):
            emoji_id = emoji
        elif not emoji.id:
            emoji_id = emoji.name
        else:
            emoji_id = str(emoji.id)
        if emoji_id not in self.emoji:
            return False

        # Check the channel or PM allowed
        is_correct_channel = message.channel.id in self.channels if self.channels else True
        is_pm = isinstance(message.channel, discord.abc.PrivateChannel) and self.allow_pm
        if not is_correct_channel and not is_pm:
            return False

        # Check that the member has the required role
        is_correct_role = roles.has_any_roles(user, self.roles) if self.roles else True
        if not is_correct_role:
            return False

        return True

    def get_message_member(self, message):
        member = message.author
        if not isinstance(member, discord.Member):
            server = self.client.get_guild(config.DISCORD_SERVER_ID)
            member = server.get_member(member.id)
        return member

    @error_handler
    async def handle_message(self, reaction, user, response_channel=None):
        """Handle the reaction.

        If a response_channel is given the response will be sent there instead
        of to the message's channel.
        """
        channel = self.get_response_channel(reaction, response_channel)
        await self.pre_handle(reaction, user, channel)
        response = await self.handle(reaction, user, channel)
        await self.post_handle(reaction, user, channel, response)
        return response

    def get_response_channel(self, reaction, response_channel):
        channel = response_channel or reaction.message.channel
        if not isinstance(channel, (discord.TextChannel, discord.DMChannel)):
            channel = self.client.get_channel(channel)
        return channel

    async def pre_handle(self, reaction, user, response_channel):
        pass

    async def handle(self, reaction, user, response_channel):
        raise NotImplementedError()

    async def post_handle(self, reaction, user, response_channel, response):
        pass
