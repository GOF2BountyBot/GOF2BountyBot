from dataclasses import dataclass
from datetime import timedelta, datetime
import re
from typing import AnyStr, Dict, Iterable, Union
import random
from . import stringTyping


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


def tomorrow(today : datetime = None) -> datetime:
    """Make a new timestamp at 12am tomorrow. Or edit the provided one, to be one day later.

    :param datetime today: A timestamp whose day to increment by one, and all other time attributes to zero out (default now)
    :return: a timestamp for 12am tomorrow utc time if today is not given. Return today after changing to tomorrow otherwise.
    """
    if today is None:
        today = datetime.utcnow()
    return today.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)


UTC_OFFSETS = { "Y": timedelta(hours=-12),
                "X": timedelta(hours=-11),
                "W": timedelta(hours=-10),
                "V+": timedelta(hours=-9, minutes=-30),
                "V": timedelta(hours=-9),
                "U": timedelta(hours=-8),
                "T": timedelta(hours=-7),
                "S": timedelta(hours=-6),
                "R": timedelta(hours=-5),
                "Q": timedelta(hours=-4),
                "P+": timedelta(hours=-3, minutes=-30),
                "P": timedelta(hours=-3),
                "O": timedelta(hours=-2),
                "N": timedelta(hours=-1),
                "Z": timedelta(hours=0),
                "A": timedelta(hours=1),
                "B": timedelta(hours=2),
                "C": timedelta(hours=3),
                "C+": timedelta(hours=3, minutes=30),
                "D": timedelta(hours=4),
                "D+": timedelta(hours=4, minutes=30),
                "E": timedelta(hours=5),
                "E+": timedelta(hours=5, minutes=30),
                "E*": timedelta(hours=5, minutes=45),
                "F": timedelta(hours=6),
                "F+": timedelta(hours=3, minutes=30),
                "G": timedelta(hours=7),
                "H": timedelta(hours=8),
                "H+": timedelta(hours=8, minutes=45),
                "I": timedelta(hours=9),
                "I+": timedelta(hours=9, minutes=30),
                "K": timedelta(hours=10),
                "K+": timedelta(hours=10, minutes=30),
                "L": timedelta(hours=11),
                "M": timedelta(hours=12),
                "M*": timedelta(hours=12, minutes=45),
                "M+": timedelta(hours=13),
                "M++": timedelta(hours=14)}


dateSeparators = (".", "-", "/")
days = ("monday", "mon", "tuesday", "tues", "tue", "wednesday", "wed", "thursday", "thurs", "thu", "thur", "friday", "fri",
        "saturday", "sat", "sunday", "sun")
months = ("january", "jan", "february", "feb", "march", "mar", "april", "apr", "may", "june", "jun", "july", "jul", "august",
            "aug", "september", "sept", "sep", "october", "oct", "november", "nov", "december", "dec")
numExtensions = set(stringTyping.numExtensions)


def _regAny(items: Iterable[str]) -> str:
    return "|".join(items)


class _TimeFormats:
    anytime = "\\d\\d?:\\d\\d( ?(am|pm))?"
    twelveHour = "\\d\\d?:\\d\\d ?(am|pm)"
    twentyFourHour = "\\d\\d?:\\d\\d"


class TimePatterns:
    anytime = re.compile(f"^{_TimeFormats.anytime}$")
    twelveHour = re.compile(f"^{_TimeFormats.twelveHour}$")
    twentyFourHour = re.compile(f"^{_TimeFormats.twentyFourHour}$")


class _DateFormats:
    digitsDate = f"\\d\\d?({_regAny(dateSeparators)})\\d\\d?({_regAny(dateSeparators)})\\d\\d(\\d\\d)?"
    digitsDateNoYear = f"\\d\\d?({_regAny(dateSeparators)})\\d\\d?"
    extensionsDateWithDayAndYear = f"{_regAny(days)} the \\d\\d?{_regAny(numExtensions)} of {_regAny(months)} \\d\\d\\d\\d"
    extensionsDateWithDayAndYearNoThe = f"{_regAny(days)} \\d\\d?{_regAny(numExtensions)} of {_regAny(months)} \\d\\d\\d\\d"
    extensionsDateWithDayAndYearNoTheNoOf = f"{_regAny(days)} \\d\\d?{_regAny(numExtensions)} {_regAny(months)} \\d\\d\\d\\d"
    extensionsDateWithDayAndYearUS = f"{_regAny(days)} {_regAny(months)} \\d\\d?{_regAny(numExtensions)} \\d\\d\\d\\d"
    extensionsDateNoDayWithYear = f"\\d\\d?{_regAny(numExtensions)} of {_regAny(months)} \\d\\d\\d\\d"
    extensionsDateNoDayWithYearUS = f"{_regAny(months)} \\d\\d?{_regAny(numExtensions)} \\d\\d\\d\\d"
    extensionsDateNoDayNoYear = f"\\d\\d?{_regAny(numExtensions)} of {_regAny(months)} \\d\\d\\d\\d"


class DatePatterns:
    separatedDigitsDate = re.compile(f"^{_DateFormats.digitsDate}$")
    separatedDigitsDateNoYear = re.compile(f"^{_DateFormats.digitsDateNoYear}$")


def stringIsTime(s) -> bool:
    return bool(TimePatterns.anytime.match(s.lower()))


@dataclass
class TimeParseResult:
    isDelta: bool
    result: Union[datetime, timedelta]
    is24h: bool
    hasDate: bool


def parseTime(s) -> datetime:
    if not stringIsTime(s):
        raise ValueError("Not a valid time")
    m = TimePatterns.twelveHour.match(s.lower())
    is24 = False
    if m is None:
        m = TimePatterns.twentyFourHour.match(s.lower())
        is24 = True
    if m is None:
        raise ValueError("No match")
    
    colonIndex = s.index(":")
    hours = int(s[0:colonIndex])
    minutes = int(s[colonIndex+1:colonIndex+3])

    if minutes < 0 or minutes > 59:
        raise ValueError("Not a valid time")
    if is24:
        if hours < 0 or hours > 23:
            raise ValueError("Not a valid time")
    else:
        if hours < 0 or hours > 11:
            raise ValueError("Not a valid time")

    if not is24:
        dayHalf = s[-2:].lower()
        if dayHalf == "pm":
            if hours == 0:
                raise ValueError("Not a valid time")
            hours += 12

    now = datetime.utcnow()
    return datetime(year=now.year, month=now.month, day=now.day, hour=hours, minute=minutes)


def formatTDHM(td: timedelta) -> str:
    currentSeconds = int(td.total_seconds())
    prefix = "+" if currentSeconds >= 0 else "-"
    currentSeconds = abs(currentSeconds)
    hours = 0
    minutes = 0
    if currentSeconds >= 60 * 60:
        hours, currentSeconds = divmod(currentSeconds, 60 * 60)
    if currentSeconds >= 60:
        minutes, currentSeconds = divmod(currentSeconds, 60)

    return prefix + str(hours).rjust(2, "0") + ":" + str(minutes).rjust(2, "0")


def strIsRelativeDatetime(s: str) -> bool:
    if not stringIsTime(s):
        raise ValueError("Not a valid time")
    
    low = s.lower()
    return low.startswith("in") or low.endswith("")
