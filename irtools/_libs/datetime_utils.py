#! /usr/bin/env python

# Standard Imports
import time
import datetime
import math

# irtools Imports
from irtools import *

# External Import (pytz or workaround)
try:
    import pytz
    gmt_timezone = pytz.timezone('GMT')

    def apply_tz_func(dt, tz):
        return tz.localize(dt)
except ImportError:
    class GMTTimezone(datetime.tzinfo):
        def utcoffset(self, dt):
            return datetime.timedelta(hours=0)

        def tzname(self, dt):
            return "GMT"

        def dst(self, dt):
            return datetime.timedelta(hours=0)
    pytz = None
    gmt_timezone = GMTTimezone()

    def apply_tz_func(dt, tz):
        return dt.replace(tzinfo=tz)


# logging
log = logging.getLogger('irtools.utils.datetime')


def apply_timezone_to_dt(dt, timezone=gmt_timezone):
    return apply_tz_func(dt, timezone)


def convert_datetime_to_timestamp(dt, with_offset=0):
    ts = time.mktime(dt.timetuple())
    if with_offset:
        ts += with_offset
    return ts


def is_string_datetime(text, strptime_format):
    try:
        convert_to_datetime(text, strptime_format)
    except ValueError:
        return False
    else:
        return True


def convert_to_datetime(text, strptime_format):
    return datetime.datetime.strptime(text, strptime_format)


def datetime_is_in_range(dt, dt_start, dt_end, inclusive=False, fix_text=True, strptime_format=None):
    if fix_text and not isinstance(dt, datetime.datetime):
        assert strptime_format is not None
        dt = convert_to_datetime(dt, strptime_format)
    if inclusive:
        return bool(dt_start <= dt <= dt_end)
    else:
        return bool(dt_start < dt < dt_end)


def get_timedelta_from_now(dt_other, dt_now=None, in_seconds=False):
    """
    gets the timedelta between the other date and now.
    :param dt_other: other datetime
    :param dt_now: override now with a new datetime
    :param in_seconds: should we return the result in seconds? (returns an int, positive if future, negative if past)
    :return:
    """
    dt_now = dt_now or datetime.datetime.now()
    delta = dt_other - dt_now
    if in_seconds:
        return delta.total_seconds()
    return delta


def seconds_to_future(dt_future, dt_now=None, round_up=True, raise_on_past=True):
    """
    get the difference in seconds from now until future datetime
    :param dt_future: a future datetime
    :param dt_now: override now with a new datetime
    :param round_up: round up seconds, otherwise round down
    :param raise_on_past: should we raise an exception if future datetime is in the past
    :return:
    """
    dt_now = dt_now or datetime.datetime.now()
    seconds = get_timedelta_from_now(dt_future, dt_now, in_seconds=True)
    if seconds > 0:
        if round_up:
            return int(math.ceil(seconds))
        else:
            return int(math.floor(seconds))
    elif raise_on_past:
        raise RuntimeError('future is in the past', dt_now, dt_future)
    else:
        return 0  # dt_future is actually in the past, so there are no seconds until then


def seconds_from_past(dt_past, dt_now=None, round_up=True, raise_on_future=True):
    """
    get the difference in seconds from past datetime until now
    :param dt_past: a past datetime
    :param dt_now: override now with a new datetime
    :param round_up: round up seconds, otherwise round down
    :param raise_on_future: should we raise an exception if past datetime is in the future
    :return:
    """
    seconds = get_timedelta_from_now(dt_past, dt_now, in_seconds=True) * -1  # multiply -1 to flip future/past
    if seconds > 0:
        if round_up:
            return int(math.ceil(seconds))
        else:
            return int(math.floor(seconds))
    elif raise_on_future:
        raise RuntimeError('past is in the future', dt_now, dt_past)
    else:
        return 0  # dt_past is actually in the future, so there are no seconds until now


__all__ = ['convert_datetime_to_timestamp', 'is_string_datetime',
           'convert_to_datetime', 'datetime_is_in_range', 'apply_timezone_to_dt',
           'get_timedelta_from_now', 'seconds_to_future', 'seconds_from_past']
