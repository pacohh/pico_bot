import logging

import discord

import config
from commands.base import BaseCommand
from utils import finance_chart

logger = logging.getLogger(__name__)

PERIOD_MAPPING = {
    '1d': '1d',
    '5d': '5d',
    '1m': '1mo',
    '3m': '3mo',
    '6m': '6mo',
    '1y': '1y',
    '2y': '2y',
    '5y': '5y',
    '10y': '10y',
    'ytd': 'ytd',
    'max': 'max',
}


class ChartCommand(BaseCommand):
    command = '!c'
    channels = {config.DISCORD_FINANCE_CHANNEL_ID}
    allow_pm = False

    async def handle(self, message, response_channel):
        arguments = message.content.split()[1:]
        if len(arguments) != 2:
            return await response_channel.send(
                f'Wrong arguments. `{self.command} <ticker> <period>`\n'
                f'Valid periods: {", ".join(PERIOD_MAPPING)}',
                suppress_embeds=True,
            )

        ticker = arguments[0].upper()
        period = arguments[1].lower()

        if period not in PERIOD_MAPPING:
            return await response_channel.send(
                f'Invalid period, valid values: {", ".join(PERIOD_MAPPING)}',
                suppress_embeds=True,
            )

        await response_channel.trigger_typing()

        period = PERIOD_MAPPING[period]
        chart = await self.client.loop.create_task(finance_chart.chart(ticker, period))

        if not chart:
            return await response_channel.send(f'No data found for ticker {ticker}')

        return await response_channel.send(file=discord.File(fp=chart, filename='chart.png'))
