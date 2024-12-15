from __future__ import annotations

import logging
from collections import defaultdict
from unittest.mock import MagicMock

import discord

import config
from background_tasks import bm_players
from commands.base import BaseCommand
from commands.mixins import DeletePreviousMixin
from utils.squad import prettify_layer_name

logger = logging.getLogger(__name__)


class WhoCommand(DeletePreviousMixin, BaseCommand):
    command = '!who'
    allow_pm = False

    def __init__(self, client: discord.Client, game: str, channel: str):
        super().__init__(client)
        self.game = game
        self.channels = {channel}
        self.previous_message = None
        self.previous_responses = defaultdict(set)
        self.degen_messages = set()

    async def should_handle(self, message):
        # Disable the command while we don't have a BM API key
        return False

    async def handle(self, message, response_channel):
        response_message = self.build_message()
        self.previous_message = response_message
        return await response_channel.send(content=response_message)

    async def post_handle(self, message, response_channel, response):
        await self.delete_degen_messages()
        return await super().post_handle(message, response_channel, response)

    async def update_messages(self):
        message = self.build_message()

        # Don't update if message hasn't changed
        if message == self.previous_message:
            return

        self.previous_message = message

        # Update messages
        for responses in self.previous_responses.values():
            for response in responses:
                await response.edit(content=message)

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

    def build_message(self):
        return WhoMessageBuilder.build(self.game) or 'No pepegas around'

    @property
    def squad_channel(self):
        return self.client.get_channel(config.DISCORD_SQUAD_CHANNEL_ID)


class WhoMessageBuilder:
    @classmethod
    def build(cls, game: str) -> str:
        return '\n'.join(
            cls._build_server(server)
            for server in bm_players.servers_data
            if server['game'] == game
        )

    @classmethod
    def _build_server(cls, server: dict) -> str:
        emote = server['emote'] if server['emote'] else f":flag_{server['country']}:"
        players = ''
        if server['players'] / server['max_players'] < 0.6:
            players = f"Players: {server['players']}/{server['max_players']} (+{server['queue']})\n"
        next_layer_data = server['next_layer_data']
        next_f1 = next_layer_data['team1']['faction'] if next_layer_data else ''
        next_f2 = next_layer_data['team2']['faction'] if next_layer_data else ''
        next_v1 = next_layer_data['team1']['vehicles'] if next_layer_data else ''
        next_v2 = next_layer_data['team2']['vehicles'] if next_layer_data else ''
        server_name = server['name'].replace('discord.gg/', r'discord.gg\/')
        message = (
            f"{emote}   **{server_name}**\n"
            f"```yaml\n"
            f"Pepegas: {', '.join(server['pepegas'])}\n"
            f"Layer:   {prettify_layer_name(server['layer'])}"
        )
        if server['next_layer']:
            message += f"\nNext:    {prettify_layer_name(server['next_layer']) or '–'}"

        message += f"\n{players}\n```"
        return message
