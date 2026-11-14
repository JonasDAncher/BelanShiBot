"""Plain data types and the pure sign-up rules for raids."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import config
from models import Role


def as_utc(value: datetime) -> datetime:
    """MariaDB DATETIME columns hold naive UTC; attach the zone when reading."""
    return value.replace(tzinfo=timezone.utc)


@dataclass
class GuildSettings:
    guild_id: int
    officer_role_id: int | None
    timezone: str


@dataclass
class RaidDraft:
    """The editable part of a raid (what the officer typed in)."""
    title: str
    description: str
    min_item_level: int | None
    enchants_required: bool
    consumables_required: bool
    start_minute: int
    duration_minutes: int
    weekdays: int


@dataclass
class RaidEvent:
    id: int
    guild_id: int
    channel_id: int
    message_id: int | None
    title: str
    description: str
    min_item_level: int | None
    enchants_required: bool
    consumables_required: bool
    start_minute: int
    duration_minutes: int
    weekdays: int
    timezone: str
    cycle: int
    occurrence_start: datetime
    occurrence_end: datetime
    active: bool
    created_by: int
    updated_by: int

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "RaidEvent":
        return cls(
            id=row["id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            message_id=row["message_id"],
            title=row["title"],
            description=row["description"] or "",
            min_item_level=row["min_item_level"],
            enchants_required=bool(row["enchants_required"]),
            consumables_required=bool(row["consumables_required"]),
            start_minute=row["start_minute"],
            duration_minutes=row["duration_minutes"],
            weekdays=row["weekdays"],
            timezone=row["timezone"],
            cycle=row["cycle"],
            occurrence_start=as_utc(row["occurrence_start"]),
            occurrence_end=as_utc(row["occurrence_end"]),
            active=bool(row["active"]),
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )


@dataclass(frozen=True)
class Signup:
    user_id: int
    role: Role
    display_name: str
    signed_at: datetime


class ToggleStatus(enum.Enum):
    JOINED = enum.auto()
    LEFT = enum.auto()
    SWAPPED = enum.auto()
    ROLE_FULL = enum.auto()
    ENDED = enum.auto()    # The occurrence ended a moment ago; rollover is about to happen
    STALE = enum.auto()    # The clicked message is no longer the event's current post
    MISSING = enum.auto()  # Event deleted / deactivated


@dataclass
class ToggleResult:
    status: ToggleStatus
    event: RaidEvent | None = None
    signups: list[Signup] = field(default_factory=list)
    previous: Role | None = None


def decide_toggle(current: Role | None, clicked: Role, tank_count: int,
                  max_tanks: int = config.RAID_MAX_TANKS) -> ToggleStatus:
    """Clicking your own role leaves it; otherwise join (swapping if needed). Only tanks are capped."""
    if current is clicked:
        return ToggleStatus.LEFT
    if clicked is Role.TANK and tank_count >= max_tanks:
        return ToggleStatus.ROLE_FULL
    return ToggleStatus.SWAPPED if current is not None else ToggleStatus.JOINED
