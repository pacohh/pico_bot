import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Tuple, Union

import aiocron
import pytz

logger = logging.getLogger(__name__)


class DiscordTask(ABC):
    """Abstract class for background tasks that should run once."""

    def __init__(self, client):
        self.client = client

    async def start(self):
        await self.client.wait_until_ready()
        await self.work()

    @abstractmethod
    async def work(self):
        pass


class CrontabDiscordTask(DiscordTask, ABC):
    """Abstract class for crontab background tasks."""

    crontab = '* * * * *'
    run_on_start = False
    raise_errors = False
    timezone = 'Europe/Zurich'

    def __init__(self, client):
        super().__init__(client)
        self.cron = aiocron.crontab(
            self.crontab,
            func=self.work_wrapper,
            start=False,
            tz=pytz.timezone(self.timezone),
        )

    async def start(self):
        await self.client.wait_until_ready()

        if self.run_on_start:
            await self.work_wrapper()

        while True:
            await self.cron.next()

    async def work_wrapper(self):
        try:
            await self.work()
        except Exception:
            if self.raise_errors:
                raise
            else:
                logger.exception('Unexpected exception in crontab discord task')


class SleepDiscordTask(DiscordTask, ABC):
    """Abstract class for sleep background tasks."""

    sleep_seconds: Union[int, Tuple[int, int]]
    raise_errors = False

    def __init__(self, client):
        super().__init__(client)

    async def start(self):
        await self.client.wait_until_ready()

        while True:
            try:
                await self.work_wrapper()
            except:
                logger.exception('Unknown exception')
            sleep_seconds = self._calculate_sleep_seconds()
            await asyncio.sleep(sleep_seconds)

    def _calculate_sleep_seconds(self) -> int:
        if isinstance(self.sleep_seconds, int):
            return self.sleep_seconds
        elif isinstance(self.sleep_seconds, tuple):
            return random.randint(*self.sleep_seconds)
        else:
            raise ValueError(
                'self.sleep_seconds should be an int or a tuple, but is %s: %s',
                type(self.sleep_seconds),
                self.sleep_seconds,
            )

    async def work_wrapper(self):
        try:
            await self.work()
        except Exception:
            if self.raise_errors:
                raise
            else:
                logger.exception('Unexpected exception in crontab discord task')
