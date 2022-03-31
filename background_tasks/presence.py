import discord

import config
from background_tasks import bm_players
from background_tasks.base import CrontabDiscordTask
from utils import battlemetrics


class PresenceTask(CrontabDiscordTask):
    """
    Task that updates the bot's presence with the current number of pepegas playing.
    """

    crontab = '* * * * * */20'
    run_on_start = True

    async def work(self):
        pepegas = 0
        for pepega in bm_players.players_data.values():
            if pepega['server']['id']:
                pepegas += 1
        await self.client.change_presence(
            activity=discord.Activity(
                name=f'{pepegas} pepegas',
                type=discord.ActivityType.watching,
            )
        )
