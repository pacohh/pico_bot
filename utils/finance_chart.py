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


async def chart(ticker, period):
    interval = PERIOD_INTERVALS.get(period, '1h')
    is_hourly = interval[-1] in ['h', 'm']

    ticker = Ticker(ticker)
    info = ticker.info

    if 'symbol' not in info:
        return None

    data = ticker.history(period, interval)

    if data.empty:
        return None

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
                f"<sup>Period: {period.upper()} | Interval: {interval.upper()}</sup>",
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
                {'bounds': [16, 9.5], 'pattern': "hour"} if is_hourly else {},
            ],
            xaxis_rangeslider_visible=False,
        ),
    )

    image_bytes = fig.to_image(format='png', scale=2)
    image = BytesIO(image_bytes)
    return image
