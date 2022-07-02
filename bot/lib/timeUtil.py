from datetime import timedelta, datetime
from typing import Dict, Optional
import random


def td_format_noYM(td_object: timedelta) -> str:
    """Create a string describing the attributes of a given datetime.timedelta object, in a
    human reader-friendly format.
    This function does not create 'week', 'month' or 'year' strings, its highest time denominator is 'day'.
    Any time denominations that are equal to zero will not be present in the string.

    :param datetime.timedelta td_object: The timedelta to describe
    :return: A string describing td_object's attributes in a human-readable format
    :rtype: str
    """
    seconds = int(td_object.total_seconds())
    if past := seconds < 0:
        seconds = abs(seconds)

    periods = [
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings) + (" ago" if past else "")


def getRandomDelay(minmaxDict: Dict[str, timedelta]) -> timedelta:
    """Generate a random timedelta between the given minimum and maximum timedeltas, inclusive.
    minMaxDict must contain keys "min" and "max" (case sensitive), with values of timedeltas representing
    the minimium and maximum delays this function can generate (inclusive)

    :param minMaxDict: A dictionary with a "min" timedelta and a "max" timedelta as generation limits
    :type minMaxDict: Dict[str, timedelta]
    :return: A timedelta randomly placed between the given min and max
    :rtype: timedelta
    """
    return timedelta(seconds=random.randint(int(minmaxDict["min"].total_seconds()), int(minmaxDict["max"].total_seconds())))


def tomorrow(today: Optional[datetime] = None) -> datetime:
    """Make a new timestamp at 12am tomorrow. Or edit the provided one, to be one day later.

    :param datetime today: A timestamp whose day to increment by one, and all other time attributes to zero out (default now)
    :return: a timestamp for 12am tomorrow utc time if today is not given. Return today after changing to tomorrow otherwise.
    """
    if today is None:
        today = datetime.utcnow()
    return today.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    
def td_secondsMinutesHours(td: timedelta):
    """Computes the number of hours minutes and minutes for the given timedelta.

    :param td: The timedelta to collapse
    :type td: timedelta
    :return: The number of hours, minutes and seconds in a tuple
    :rtype: List[Tuple[str, int]]
    """
    seconds = int(td.total_seconds())
    periods = [
        ('hours', 60 * 60),
        ('minutes', 60),
        ('seconds', 1)
    ]
    results = {
        'hours': 0,
        'minutes': 0,
        'seconds': 0
    }
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            results[period_name], seconds = divmod(seconds, period_seconds)
        
    return results
