import logging

import config
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
        logger.info('Updating BM player and server data')
        for player_id, player_name in config.BM_PLAYERS.items():
            await self.handle_player(player_id, player_name)
        self.update_server_data()

    @staticmethod
    async def handle_player(player_id: int, player_name: str) -> None:
        data = await battlemetrics.get_player_server(player_id, config.BM_TOKEN)
        players_data[player_name] = data

    @staticmethod
    def update_server_data() -> None:
        servers = {}
        for player_name, player_data in players_data.items():
            server = player_data['server']
            server_name = server['name']

            if not server_name:
                continue

            if server_name not in servers:
                servers[server_name] = server
                servers[server_name]['pepegas'] = []

            servers[server_name]['pepegas'].append(player_name)

        for server in servers.values():
            server['pepegas'].sort()

        global servers_data
        servers_data = list(servers.values())
