import logging

import config
from background_tasks import bm_players
from commands.base import BaseCommand, BaseReactionHandler
from commands.mixins import DeletePreviousMixin

logger = logging.getLogger(__name__)


class WhoCommand(DeletePreviousMixin, BaseCommand):
    command = '!who'
    channels = {config.DISCORD_SQUAD_CHANNEL_ID}
    allow_pm = False

    previous_message = None

    async def handle(self, message, response_channel):
        message = self.build_message()
        self.previous_message = message
        return await response_channel.send(content=message)

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

    @classmethod
    def build_message(cls):
        return WhoMessageBuilder.build() or 'No pepegas around'


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
