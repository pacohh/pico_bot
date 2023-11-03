import datetime as dt
from typing import Union

import pytz


def utc_now(include_timezone=True):
    """Construct a UTC datetime from time.time()."""
    now = dt.datetime.utcnow()
    if include_timezone:
        now = now.replace(tzinfo=pytz.utc)
    return now


def british_now():
    """
    Construct a datetime from time.time() with the current British timezone.
    """
    return pytz.timezone('Europe/London').fromutc(utc_now(include_timezone=False))


def format_british_now(date=False, time=True, timezone=True):
    """Return the current time in GB as a string."""
    format_ = []
    if date:
        format_.append('%d/%m/%y')
    if time:
        format_.append('%H:%M:%S')
    if timezone:
        format_.append('%Z')
    format_ = ' '.join(format_)
    now = british_now()
    return format_datetime(now, format_=format_)


def now_isoformat(milliseconds=False, z=False):
    """Return the current datetime in ISO format."""
    datetime = utc_now()
    return datetime_isoformat(datetime, milliseconds=milliseconds, z=z)


def datetime_isoformat(datetime, milliseconds=False, z=False):
    """Return the given datetime in ISO format."""
    timestamp = datetime.isoformat()
    if not milliseconds:
        timestamp = timestamp.split('.', maxsplit=1)[0]
    if z:
        timestamp += 'Z'
    return timestamp


def format_datetime(datetime, format_='%Y.%m.%d %H:%M:%S'):
    return datetime.strftime(format_)


def format_datetime_simple(datetime, format_='%H:%M'):
    return format_datetime(datetime, format_=format_)


def to_epoch(datetime: Union[dt.datetime, dt.date]) -> int:
    return int(datetime.strftime('%s'))


def epoch_to_date(epoch: int) -> dt.date:
    return dt.date.fromtimestamp(epoch)


def epoch_to_datetime(epoch: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(epoch)


def is_today(date: Union[dt.datetime, dt.date]) -> bool:
    if isinstance(date, dt.datetime):
        date = date.date()
    today = utc_now().date()
    return date == today
