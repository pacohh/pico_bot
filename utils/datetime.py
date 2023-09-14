import datetime as dt

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


def to_epoch(datetime) -> int:
    return int((datetime - dt.datetime(1970, 1, 1, tzinfo=datetime.tzinfo)).total_seconds())
