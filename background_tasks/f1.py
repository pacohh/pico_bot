from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass
from typing import Optional, Union

import dateutil.parser
import fastf1.core
import pandas as pd
from aiohttp_requests import requests

import config
from background_tasks.base import CrontabDiscordTask
from utils import f1, redis
from utils.datetime import is_today, to_epoch, utc_now

REDIS_KEY = 'f1_last_handled_session'

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

TEAM_EMOTES = {
    'Alfa Romeo': '<:a:1152607754180116652>',
    'AlphaTauri': '<:a:1152607462747287573>',
    'Alpine': '<:a:1152607565298024458>',
    'Aston Martin': '<:a:1152607683678056561>',
    'Ferrari': '<:a:1152607316722589746>',
    'Haas F1 Team': '<:a:1152607627621183488>',
    'McLaren': '<:a:1152607334451912744>',
    'Mercedes': '<:a:1152607280827727902>',
    'Red Bull Racing': '<:a:1152607379158999060>',
    'Williams': '<:a:1152607527930953909>',
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
        message = await self.channel.send(content=msg)
        await message.pin()

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


class F1DaySchedule(CrontabDiscordTask):
    """
    Task that sends a message with the schedule of the current day.
    """

    crontab = '0 7 * * * 0'
    run_on_start = True

    def __init__(self, client):
        super().__init__(client)
        self._channel = None

    @property
    def channel(self):
        if not self._channel:
            self._channel = self.client.get_channel(config.DISCORD_F1_CHANNEL_ID)
        return self._channel

    async def work(self):
        race, sessions = await self.get_today_sessions()
        if not sessions:
            return
        msg = self.build_message(race, sessions)
        await self.channel.send(content=msg)

    async def get_today_sessions(self):
        race = await self.get_current_race()
        if not race:
            return None, None
        sessions = [session for session in race.sessions if is_today(session.timestamp)]
        return race, sessions

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
    def build_message(race: Race, sessions: list[Session]) -> str:
        lines = []
        lines.append(f"## {race.name} GP – Today's sessions")

        sessions_len = max(len(SESSIONS_MAPPING[session.type_]) for session in sessions)

        for session in sessions:
            session_name = SESSIONS_MAPPING[session.type_]
            timestamp = session.iso_timestamp
            lines.append(
                f'- `{session_name:<{sessions_len}}`:   <t:{timestamp}:t>   (<t:{timestamp}:R>)'
            )

        return '\n'.join(lines)


class F1Results(CrontabDiscordTask):
    """
    Task that post session results when they become available.
    """

    ALLOWED_SESSIONS = {'sprint shootout', 'sprint', 'qualifying', 'race'}

    crontab = '* * * * * 0'
    run_on_start = False

    def __init__(self, client):
        super().__init__(client)
        self.redis = redis.get_client()
        self._channel = None

    @property
    def channel(self):
        if not self._channel:
            self._channel = self.client.get_channel(config.DISCORD_F1_CHANNEL_ID)
        return self._channel

    async def work(self):
        session = await f1.get_latest_session(self.client)
        last_handled_session = await self.get_redis()
        if not session:
            return
        if str(session) == last_handled_session:
            return
        if session.event.is_testing():
            return
        if session.name.lower() not in self.ALLOWED_SESSIONS:
            return

        try:
            await self.client.loop.run_in_executor(None, session.load)
        except fastf1.core.DataNotLoadedError:
            return

        session_status = session.session_status['Status'].iloc[-1]
        if session_status.lower() != 'ends':
            return

        msg = self.build_message(session)
        await self.channel.send(content=msg)
        await self.set_redis(str(session))

    async def get_redis(self) -> str:
        value = await self.redis.get(REDIS_KEY)
        if value:
            return value.decode()

    async def set_redis(self, name: str) -> None:
        await self.redis.set(REDIS_KEY, name)

    def build_message(self, session: fastf1.core.Session) -> str:
        name = session.session_info.get('Meeting', {}).get('Name', '').replace('Grand Prix', 'GP')
        lines = [f'# {name} {session.name} results']
        results = session.results
        for pos, line in results.iterrows():
            if session.name.lower() in {'sprint', 'race'}:
                lines.append(self.format_race_result(pos, line))
            else:
                lines.append(self.format_quali_result(line))
        return '\n'.join(lines)

    def format_race_result(self, pos, line) -> str:
        emote = TEAM_EMOTES.get(line.TeamName)
        pos_change = self.format_position_change(line)
        time = self.format_time(pos, line.Time)
        return (
            f'{emote}'
            f'   `{line.ClassifiedPosition:>2}'
            f' | {pos_change}'
            f'   {line.Abbreviation}'
            f'   {time:<11}'
            f'   {int(line.Points):>2}`'
        )

    def format_quali_result(self, line) -> str:
        emote = TEAM_EMOTES.get(line.TeamName)
        q1 = self.format_time('1', line.Q1, quali=True)
        q2 = self.format_time('1', line.Q2, quali=True)
        q3 = self.format_time('1', line.Q3, quali=True)
        return (
            f'{emote}'
            f'   `{int(line.Position):>2}'
            f'   {line.Abbreviation}'
            f'   {q1:<11}'
            f'   {q2:<11}'
            f'   {q3:<11}`'
        )

    @staticmethod
    def format_position_change(line) -> str:
        position_change = int(line.GridPosition - line.Position)
        change_symbol = '▲' if position_change > 0 else '▽'
        if position_change == 0:
            return '  –'
        else:
            return f'{change_symbol}{abs(position_change):>2}'

    @staticmethod
    def format_time(pos: str, timedelta: Union[pd.Timedelta, pd.NaT], quali: bool = False) -> str:
        if pd.isnull(timedelta):
            return 'DNF' if not quali else ''
        co = timedelta.components
        if pos == '1' or quali:
            time = f'{co.hours}:{co.minutes:>02}:{co.seconds:>02}.{co.milliseconds}'
        else:
            time = f'+{timedelta.seconds}.{co.milliseconds}s'
        return time
