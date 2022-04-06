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

SESSION_NAMES = {
    'fp1': 'FP1',
    'fp2': 'FP2',
    'fp3': 'FP3',
    'qualifying': 'Qualifying',
    'gp': 'Race',
    'sprint': 'Sprint',
}


class F1CreateEventsCommand(BaseCommand):
    command = '!f1ce'
    channels = {config.DISCORD_ADMIN_CHANNEL_ID}

    async def handle(self, message, response_channel):
        arguments = message.content.split()[1:]
        if len(arguments) != 2:
            return await response_channel.send(
                content=f'Wrong arguments. `{self.command} voice_channel_id data_url`'
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

        # Create events for each race
        for race in data['races']:
            await self.handle_race(guild, voice_channel, race)

        return await response_channel.send(content='Finished')

    async def handle_race(
        self, guild: discord.Guild, voice_channel: discord.VoiceChannel, race: Dict
    ) -> None:
        race_name = race['name'].replace('Grand Prix', '').strip()
        race_name = f'{race_name} GP'
        for session, timestamp in race['sessions'].items():
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
