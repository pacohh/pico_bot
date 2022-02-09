import logging
from abc import ABC, abstractmethod

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

    def __init__(self, client):
        super().__init__(client)
        self.cron = aiocron.crontab(
            self.crontab, func=self.work_wrapper, start=False, tz=pytz.timezone('Europe/London')
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
