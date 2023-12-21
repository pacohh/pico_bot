import logging

import a2s
import discord

import commands
import config
from background_tasks import squad
from background_tasks.base import CrontabDiscordTask
from utils import battlemetrics

logger = logging.getLogger(__name__)

players_data = {}
servers_data = []


class BattlemetricsPlayersTask(CrontabDiscordTask):
    """
    Task that checks what players are online and on which servers.
    """

    crontab = '* * * * * */20'
    run_on_start = True

    def __init__(self, client):
        super().__init__(client)

    async def work(self):
        await self.update_players_data()
        await self.update_server_data()
        await self.update_who_messages()
        await self.update_bot_presence()

    @staticmethod
    async def update_players_data() -> None:
        players = await battlemetrics.get_server_players('2272069', config.BM_TOKEN)
        for player_id, player_name in config.BM_PLAYERS.items():
            players_data[player_name] = players.get(player_id)

    async def update_server_data(self) -> None:
        servers = {}
        for player_name, player_data in players_data.items():
            if not player_data:
                continue

            server = player_data['server']
            server_name = server['name']

            if not server_name:
                continue

            if server_name not in servers:
                servers[server_name] = server
                servers[server_name]['pepegas'] = []

            servers[server_name]['pepegas'].append(player_name)

        for server in servers.values():
            server['pepegas'].sort(key=lambda name: name.lower())
            server['next_layer_data'] = squad.layers_data.get(server['next_layer'])

        global servers_data
        was_empty = not servers_data
        servers_data = list(servers.values())
        servers_data.sort(key=lambda server_: len(server_['pepegas']), reverse=True)
        is_empty = not servers_data
        # This is commented out to disable the degen messages
        # if was_empty and not is_empty:
        #     await commands.WhoCommand(self.client).send_degen_message()
        # if is_empty and not was_empty:
        #     await commands.WhoCommand(self.client).delete_degen_messages()

    async def update_who_messages(self) -> None:
        await self.client.squad_who_command.update_messages()
        await self.client.ps_who_command.update_messages()

    async def update_bot_presence(self) -> None:
        # Count how many pepegas are playing
        pepegas = 0
        for pepega in players_data.values():
            if not pepega:
                continue
            if pepega['server']['id']:
                pepegas += 1

        # Update bot presence
        plural = 's' if pepegas != 1 else ''
        await self.client.change_presence(
            activity=discord.Activity(
                name=f'with {pepegas} pepega{plural}',
                type=discord.ActivityType.playing,
            )
        )
