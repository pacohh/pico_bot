from collections import defaultdict

import discord

import config
from background_tasks.base import CrontabDiscordTask
from utils import battlemetrics


class BattlemetricsPlayersTask(CrontabDiscordTask):
    """
    Task that sends a message every time a player joins a server (according to BM).
    """

    crontab = '* * * * * */30'
    run_on_start = True

    def __init__(self, client):
        super().__init__(client)
        self.players = defaultdict(None)

    async def work(self):
        channel = self.client.get_channel(config.DISCORD_PLAYER_LOG_CHANNEL_ID)

        for player_id in config.BM_PLAYER_IDS:
            await self.handle_player(player_id, channel)

    async def handle_player(self, player_id, channel):
        new_data = await battlemetrics.get_player_server(player_id, config.BM_TOKEN)

        if player_id not in self.players:
            self.players[player_id] = new_data
            return

        old_data = self.players[player_id]
        self.players[player_id] = new_data

        old_server_id = old_data['server_id']
        new_server_id = new_data['server_id']

        has_connected = new_server_id and new_server_id != old_server_id
        has_disconnected = old_server_id and not new_server_id

        player_name = new_data['player_name']
        server_name = new_data['server_name']
        game = config.BM_ALLOWED_GAMES.get(new_data['server_game'])
        country = f':flag_{new_data["server_country"]}:'

        if has_connected:
            await channel.send(f'**{player_name}** joined **{server_name}** ({game} {country})')
        elif has_disconnected:
            await channel.send(f'**{player_name}** stopped playing')
