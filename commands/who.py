import logging
from unittest.mock import MagicMock

import config
from background_tasks import bm_players
from commands.base import BaseCommand
from commands.mixins import DeletePreviousMixin
from utils.squad import prettify_layer_name

logger = logging.getLogger(__name__)


class WhoCommand(DeletePreviousMixin, BaseCommand):
    command = '!who'
    channels = {config.DISCORD_SQUAD_CHANNEL_ID}
    allow_pm = False

    previous_message = None
    degen_messages = set()

    async def handle(self, message, response_channel):
        response_message = self.build_message()
        self.previous_message = response_message
        return await response_channel.send(content=response_message)

    async def post_handle(self, message, response_channel, response):
        await self.delete_degen_messages()
        return await super().post_handle(message, response_channel, response)

    @classmethod
    async def update_messages(cls):
        message = cls.build_message()

        # Don't update if message hasn't changed
        if message == cls.previous_message:
            return

        cls.previous_message = message

        # Log number of messages being changed if there is any
        responses_count = sum(map(len, cls.previous_responses.values()))
        if responses_count:
            logger.info('Updating %d !who messages', responses_count)

        # Update messages
        for responses in cls.previous_responses.values():
            for response in responses:
                await response.edit(message)

    async def send_degen_message(self):
        channel = self.squad_channel
        mock_message = MagicMock()
        mock_message.channel = channel
        message = await channel.send('<a:DinkDonk:1002965061805015100>')
        await self.handle_message(mock_message)
        self.degen_messages.add(message)

    async def delete_degen_messages(self):
        await self.delete_channel_responses(self.squad_channel, self.degen_messages)
        self.degen_messages.clear()

    @classmethod
    def build_message(cls):
        return WhoMessageBuilder.build() or 'No pepegas around'

    @property
    def squad_channel(self):
        return self.client.get_channel(config.DISCORD_SQUAD_CHANNEL_ID)


class WhoMessageBuilder:
    @classmethod
    def build(cls) -> str:
        return '\n'.join(cls._build_server(server) for server in bm_players.servers_data)

    @classmethod
    def _build_server(cls, server: dict) -> str:
        emote = server['emote'] if server['emote'] else f":flag_{server['country']}:"
        return (
            f"{emote}   **{server['name']}**\n"
            f"```yaml\n"
            f"Pepegas: {', '.join(server['pepegas'])}\n"
            f"Layer:   {prettify_layer_name(server['layer'])}\n"
            f"Players: {server['players']}/{server['max_players']} (+{server['queue']})\n"
            f"```"
        )
