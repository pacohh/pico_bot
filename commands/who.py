import logging

import config
from background_tasks import bm_players
from commands.base import BaseCommand, BaseReactionHandler
from commands.mixins import DeletePreviousMixin
from components import emojis

REFRESH_EMOJI = emojis.REFRESH

logger = logging.getLogger(__name__)


class WhoCommand(DeletePreviousMixin, BaseCommand):
    command = '!who'
    channels = {config.DISCORD_SQUAD_CHANNEL_ID}
    allow_pm = False

    async def handle(self, message, response_channel):
        message = WhoMessageBuilder.build()
        if message:
            response = await response_channel.send(content=message)
            await response.add_reaction(REFRESH_EMOJI)
            return response


class WhoRefreshReactionHandler(BaseReactionHandler):
    emoji = REFRESH_EMOJI

    async def should_handle(self, reaction, user):
        # Check that the message is for a !who command
        if reaction.message not in WhoCommand.previous_responses[reaction.message.channel]:
            return False

        return await super().should_handle(reaction, user)

    async def handle(self, reaction, user, response_channel):
        # Log
        channel = reaction.message.channel
        logger.info('%s triggered !server refresh in #%s', user, channel.name or channel.id)

        # Remove reaction
        await reaction.message.remove_reaction(reaction.emoji, user)

        # Update message
        message = WhoMessageBuilder.build()
        await reaction.message.edit(message)


class WhoMessageBuilder:
    @classmethod
    def build(cls) -> str:
        return '\n'.join(cls._build_server(server) for server in bm_players.servers_data)

    @classmethod
    def _build_server(cls, server: dict) -> str:
        return (
            f":flag_{server['country']}:   **{server['name']}**\n"
            f"```yaml\n"
            f"Pepegas: {', '.join(server['pepegas'])}\n"
            f"Layer:   {server['layer']}\n"
            f"Players: {server['players']}/{server['max_players']} (+{server['queue']})\n"
            f"```"
        )
