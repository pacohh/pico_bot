import json
from datetime import datetime
from typing import Dict

import dateutil.parser
import dateutil.utils
import discord
from aiohttp_requests import requests
from dateutil.tz import tzutc

import config
from commands.base import BaseCommand
from components.progress_bar import ProgressBarMessage

SESSION_NAMES = {
    'fp1': 'FP1',
    'fp2': 'FP2',
    'fp3': 'FP3',
    'qualifying': 'Qualifying',
    'gp': 'Race',
    'sprint': 'Sprint',
}
IGNORED_SESSIONS = {'fp1', 'fp2', 'fp3'}


class F1CreateEventsCommand(BaseCommand):
    command = '!f1ce'
    channels = {config.DISCORD_ADMIN_CHANNEL_ID}

    async def handle(
        self, message: discord.Message, response_channel: discord.TextChannel
    ) -> discord.Message:
        arguments = message.content.split()[1:]
        if len(arguments) != 2:
            return await response_channel.send(
                f'Wrong arguments. `{self.command} <voice_channel_id> <data_url>`\n'
                'Data from https://github.com/sportstimes/f1/tree/main/_db/f1',
                suppress_embeds=True,
            )

        voice_channel_id = int(arguments[0])
        data_url = arguments[1]

        # Load channel
        guild = message.guild
        voice_channel = guild.get_channel(voice_channel_id)

        # Load data
        try:
            res = await requests.session.get(data_url)
            res.raise_for_status()
            data = json.loads(await res.text())
        except:
            return await response_channel.send(content=f'Error loading data from `{data_url}`')

        # Create progress bar
        num_races = len(data['races'])
        progress_bar = ProgressBarMessage(
            self.client,
            response_channel,
            f'Creating events for {num_races} races\n'
            '`[{progress_bar}] {percentage:3.0f}%` {comment}',
        )
        await progress_bar.send(comment=f'0/{num_races}')

        # Create events for each race
        count = 0
        for race in data['races']:
            await self.handle_race(guild, voice_channel, race)
            count += 1
            await progress_bar.update(count, num_races, comment=f'{count}/{num_races}')

        # Delete progress bar
        await progress_bar.delete()

        return await response_channel.send(content='Finished')

    async def handle_race(
        self, guild: discord.Guild, voice_channel: discord.VoiceChannel, race: Dict
    ) -> None:
        race_name = race['name'].replace('Grand Prix', '').strip()
        race_name = f'{race_name} GP'
        for session, timestamp in race['sessions'].items():
            if session in IGNORED_SESSIONS:
                continue
            session_name = f'{race_name} {SESSION_NAMES[session]}'
            await self.handle_session(guild, voice_channel, session_name, timestamp)

    @staticmethod
    async def handle_session(
        guild: discord.Guild,
        voice_channel: discord.VoiceChannel,
        session_name: str,
        timestamp: str,
    ) -> None:
        event_name = f'F1 {session_name}'
        timestamp = dateutil.parser.parse(timestamp)

        now = datetime.now(tzutc())
        if timestamp < now:
            return

        await guild.create_scheduled_event(
            name=event_name,
            start_time=timestamp,
            entity_type=discord.EntityType.voice,
            privacy_level=discord.PrivacyLevel.guild_only,
            channel=voice_channel,
        )
