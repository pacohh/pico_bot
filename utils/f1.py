import datetime
from typing import Optional

import fastf1
from fastf1.core import Session
from fastf1.events import Event

from utils.datetime import utc_now


async def get_latest_session(client) -> Optional[Session]:
    event = await get_current_event(client)
    if event is None:
        return
    now = utc_now()

    session = None
    for identifier in range(1, 6):
        session_start = event.get_session_date(identifier)
        if session_start < now:
            session = event.get_session(identifier)

    return session


async def get_current_event(client) -> Optional[Event]:
    def get_schedule():
        return fastf1.get_event_schedule(now.year)

    now = datetime.datetime.now()
    monday = now - datetime.timedelta(days=now.weekday())
    sunday = monday + datetime.timedelta(days=6)
    events = await client.loop.run_in_executor(None, get_schedule)
    events = events.loc[(events['EventDate'] >= monday) & (events['EventDate'] <= sunday)]

    num_events = events.shape[0]
    if num_events == 0:
        return None
    if num_events > 1:
        raise RuntimeError(f'Got {num_events} active F1 events, expected 1 or 0')
    return events.iloc[0]
