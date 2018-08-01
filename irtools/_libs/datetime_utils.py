#! /usr/bin/env python

# Standard Imports
import time
import datetime

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


__all__ = ['convert_datetime_to_timestamp', 'is_string_datetime',
           'convert_to_datetime', 'datetime_is_in_range', 'apply_timezone_to_dt']
