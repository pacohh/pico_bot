from io import BytesIO

import plotly.graph_objects as go
from plotly.graph_objs.layout import Margin
from yfinance import Ticker

PERIOD_INTERVALS = {
    '1d': '5m',
    '5d': '15m',
    '1mo': '90m',
    '3mo': '1d',
    '6mo': '1d',
    '1y': '1d',
    '2y': '5d',
    '5y': '1wk',
    '10y': '1wk',
    'ytd': '1d',
    'max': '1wk',
}


class BaseFinanceChart:
    def __init__(self, ticker, period):
        self.ticker = Ticker(ticker)
        self.period = period
        self.interval = PERIOD_INTERVALS.get(period, '1h')
        self.is_hourly = self.interval[-1] in ['h', 'm']
        self.ticker_data = self.ticker.history(period, self.interval)
        self.ticker_info = self.ticker.info

    @property
    def has_data(self):
        has_symbol = 'symbol' not in self.ticker_info
        has_data = not self.ticker_data.empty
        return has_symbol and has_data

    async def to_image(self):
        if not self.has_data:
            return None
        chart = await self.chart()
        image_bytes = chart.to_image(format='png', scale=2)
        image = BytesIO(image_bytes)
        return image

    async def chart(self):
        raise NotImplementedError()


class FinanceLineChart(BaseFinanceChart):
    async def chart(self):
        info = self.ticker_info
        data = self.ticker_data

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=data.index,
                    y=data['High'],
                )
            ],
            layout=go.Layout(
                title=go.layout.Title(
                    text=f"{info.get('longName', info.get('name'))} ({info['symbol']})<br>"
                    f"<sup>Period: {self.period.upper()} | Interval: {self.interval.upper()}</sup>",
                    font=go.layout.title.Font(
                        family='Arial',
                        size=14,
                    ),
                ),
                width=800,
                height=500,
                margin=Margin(b=10, l=10, r=10, t=50),
                template='plotly_dark',
                xaxis_rangebreaks=[
                    {'bounds': ["sat", "mon"]},
                    {'bounds': [16, 9.5], 'pattern': "hour"} if self.is_hourly else {},
                ],
                xaxis_rangeslider_visible=False,
            ),
        )
        fig.update_traces(connectgaps=True)

        image_bytes = fig.to_image(format='png', scale=2)
        image = BytesIO(image_bytes)
        return image


class FinanceCandleChart(BaseFinanceChart):
    async def chart(self):
        info = self.ticker_info
        data = self.ticker_data

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                )
            ],
            layout=go.Layout(
                title=go.layout.Title(
                    text=f"{info.get('longName', info.get('name'))} ({info['symbol']})<br>"
                    f"<sup>Period: {self.period.upper()} | Interval: {self.interval.upper()}</sup>",
                    font=go.layout.title.Font(
                        family='Arial',
                        size=14,
                    ),
                ),
                width=800,
                height=500,
                margin=Margin(b=10, l=10, r=10, t=50),
                template='plotly_dark',
                xaxis_rangebreaks=[
                    {'bounds': ["sat", "mon"]},
                    {'bounds': [16, 9.5], 'pattern': "hour"} if self.is_hourly else {},
                ],
                xaxis_rangeslider_visible=False,
            ),
        )

        image_bytes = fig.to_image(format='png', scale=2)
        image = BytesIO(image_bytes)
        return image
