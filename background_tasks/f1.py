from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass
from typing import Optional

import dateutil.parser
from aiohttp_requests import requests

import config
from background_tasks.base import CrontabDiscordTask
from utils.datetime import to_epoch, utc_now

SCHEDULE_URL = 'https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/{}.json'

SESSIONS_MAPPING = {
    'fp1': 'FP1',
    'fp2': 'FP2',
    'fp3': 'FP3',
    'sprintQualifying': 'Sprint Quali',
    'sprint': 'Sprint',
    'qualifying': 'Quali',
    'gp': 'Race',
}

logger = logging.getLogger(__name__)


@dataclass
class Session:
    type_: str
    timestamp: datetime.datetime

    @property
    def week(self) -> int:
        return self.timestamp.isocalendar()[1]

    @property
    def iso_timestamp(self) -> int:
        return to_epoch(self.timestamp)


@dataclass
class Race:
    name: str
    sessions: list[Session]

    @property
    def week(self) -> int:
        return self.sessions[0].week


class F1RaceWeek(CrontabDiscordTask):
    """
    Task that sends a message with the schedule on race week.
    """

    crontab = '0 7 * * 3 0'
    run_on_start = False

    def __init__(self, client):
        super().__init__(client)
        self._channel = None

    @property
    def channel(self):
        if not self._channel:
            self._channel = self.client.get_channel(config.DISCORD_F1_CHANNEL_ID)
        return self._channel

    async def work(self):
        race = await self.get_current_race()
        if not race:
            return
        msg = self.build_message(race)
        await self.channel.send(content=msg)

    async def get_current_race(self) -> Optional[Race]:
        current_week = datetime.date.today().isocalendar()[1]
        for race in await self.load_races():
            if race.week == current_week:
                return race

    async def load_races(self) -> list[Race]:
        url = SCHEDULE_URL.format(utc_now().year)
        res = await requests.session.get(url)
        data = json.loads(await res.text())
        races = [self.parse_race(race) for race in data['races']]
        return races

    def parse_race(self, race_dict: dict) -> Race:
        sessions = [self.parse_session(*session) for session in race_dict['sessions'].items()]
        return Race(
            name=race_dict['name'],
            sessions=sessions,
        )

    @staticmethod
    def parse_session(session_type: str, timestamp: str) -> Session:
        return Session(
            type_=session_type,
            timestamp=dateutil.parser.parse(timestamp),
        )

    @staticmethod
    def build_message(race: Race) -> str:
        lines = []
        lines.append("## It's race week! :partying_face:")
        lines.append(f'# {race.name} Grand Prix')

        sessions_len = max(len(SESSIONS_MAPPING[session.type_]) for session in race.sessions)

        for session in race.sessions:
            session_name = SESSIONS_MAPPING[session.type_]
            timestamp = session.iso_timestamp
            lines.append(
                f'- `{session_name:<{sessions_len}}`:   <t:{timestamp}:F>   (<t:{timestamp}:R>)'
            )

        return '\n'.join(lines)
