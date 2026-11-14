"""Parsing of human input and the recurring-schedule maths. Pure functions, no Discord/DB."""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
DAY_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
ALL_DAYS = 0b1111111

_FULL_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_ALIASES: dict[str, int] = {}
for _i, _name in enumerate(_FULL_NAMES):
    _ALIASES[_name] = _i
    _ALIASES[_name[:3]] = _i
_ALIASES.update({"tues": 1, "weds": 2, "thur": 3, "thurs": 3})
_GROUPS = {"daily": ALL_DAYS, "everyday": ALL_DAYS, "weekdays": 0b0011111, "weekends": 0b1100000}
_FILLER = {"and", "every", "on"}


class ScheduleError(ValueError):
    """Raised with a user-presentable message when input can't be understood."""


# ---------- Parsing ----------
def parse_days(text: str) -> int:
    """'Thu, Sun' / 'thursday and sunday' / 'mon-wed' / 'weekends' / 'daily' -> weekday bitmask (bit 0 = Monday)."""
    text = text.lower().replace("every day", "daily")
    mask = 0

    def day_index(token: str) -> int:
        if token not in _ALIASES:
            raise ScheduleError(f"I don't know the day '{token}'. Try something like: Thu, Sun")
        return _ALIASES[token]

    def expand_range(match: re.Match) -> str:
        nonlocal mask
        index, end = day_index(match[1]), day_index(match[2])
        while True:
            mask |= 1 << index
            if index == end:
                break
            index = (index + 1) % 7  # Ranges may wrap around the week (fri-mon)
        return " "

    text = re.sub(r"([a-z]+)\s*-\s*([a-z]+)", expand_range, text)
    for token in re.findall(r"[a-z]+", text):
        if token in _FILLER:
            continue
        mask |= _GROUPS[token] if token in _GROUPS else 1 << day_index(token)

    if mask == 0:
        raise ScheduleError("Pick at least one day of the week, e.g. Thu, Sun")
    return mask


def parse_time(text: str) -> int:
    """'19:30' / '1930' / '7:30pm' / '19' -> minutes after midnight."""
    match = re.fullmatch(r"\s*(\d{1,2})(?:[:.]?(\d{2}))?\s*(am|pm)?\s*", text.lower())
    if not match:
        raise ScheduleError("Start time must look like 19:30 or 7:30pm")
    hour, minute, meridiem = int(match[1]), int(match[2] or 0), match[3]
    if meridiem:
        if not 1 <= hour <= 12:
            raise ScheduleError("Start time must look like 19:30 or 7:30pm")
        hour = hour % 12 + (12 if meridiem == "pm" else 0)
    if hour > 23 or minute > 59:
        raise ScheduleError("Start time must be a valid time of day, e.g. 19:30")
    return hour * 60 + minute


def parse_duration(text: str) -> int:
    """'2h30m' / '2.5h' / '150m' / '2:30' / '2' (hours) / '90' (minutes) -> minutes (1..1440)."""
    s = text.lower().strip().replace(",", ".")
    minutes: float
    if m := re.fullmatch(r"(\d+):(\d{2})", s):
        minutes = int(m[1]) * 60 + int(m[2])
    elif m := re.fullmatch(r"\d+(?:\.\d+)?", s):
        value = float(s)
        minutes = value * 60 if value <= 24 else value  # Bare numbers: <=24 means hours, otherwise minutes
    elif (m := re.fullmatch(r"(?:(\d+(?:\.\d+)?)\s*h[a-z]*)?\s*(?:(\d+)\s*(?:m[a-z]*)?)?", s)) and (m[1] or m[2]):
        minutes = float(m[1] or 0) * 60 + int(m[2] or 0)
    else:
        raise ScheduleError("Duration must look like 2h30m, 2.5h or 150m")
    minutes = round(minutes)
    if not 1 <= minutes <= 24 * 60:
        raise ScheduleError("Duration must be between 1 minute and 24 hours")
    return minutes


# ---------- Formatting ----------
def format_days(mask: int) -> str:
    if mask == ALL_DAYS:
        return "Every day"
    return ", ".join(name for i, name in enumerate(DAY_SHORT) if mask >> i & 1)


def format_start(minute_of_day: int) -> str:
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return " ".join(part for part in (f"{hours}h" if hours else "", f"{mins}m" if mins else "") if part)


# ---------- Schedule maths ----------
def occurrence_at(start_minute: int, duration_minutes: int, weekdays: int, tz_name: str,
                  now: datetime) -> tuple[datetime, datetime]:
    """The occurrence people should currently be signing up for, as (start, end) in UTC.

    That is the first occurrence that has not *ended* yet: while a raid is running it is still the
    current one, and the moment it ends (start + duration) the next scheduled day takes over.
    Start times are wall-clock in `tz_name`, so they stay at e.g. 19:30 across daylight-saving changes.
    """
    if not weekdays & ALL_DAYS:
        raise ScheduleError("Pick at least one day of the week")
    tz = ZoneInfo(tz_name)
    now = now.astimezone(UTC)
    local_today = now.astimezone(tz).date()
    start_of_day = time(start_minute // 60, start_minute % 60)
    duration = timedelta(minutes=duration_minutes)

    for offset in range(-1, 9):  # Yesterday covers raids that cross midnight; +8 always reaches a scheduled day
        day = local_today + timedelta(days=offset)
        if not weekdays >> day.weekday() & 1:
            continue
        start = datetime.combine(day, start_of_day, tzinfo=tz).astimezone(UTC)
        end = start + duration
        if end > now:
            return start, end
    raise ScheduleError("Could not work out the next occurrence")  # Unreachable with a non-empty mask
