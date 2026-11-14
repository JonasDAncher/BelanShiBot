"""All SQL for raids lives here."""
from __future__ import annotations

from datetime import datetime, timedelta

import config
from db import Database
from models import Role
from raids.entities import (
    GuildSettings, RaidDraft, RaidEvent, Signup, ToggleResult, ToggleStatus, as_utc, decide_toggle,
)
from raids.schedule import UTC


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


class RaidRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------- Guild settings ----------
    async def get_settings(self, guild_id: int) -> GuildSettings:
        row = await self.db.fetchone(
            "SELECT guild_id, officer_role_id, timezone FROM guild_settings WHERE guild_id = %s", (guild_id,)
        )
        if row is None:
            return GuildSettings(guild_id, None, config.DEFAULT_TIMEZONE)
        return GuildSettings(row["guild_id"], row["officer_role_id"], row["timezone"])

    async def save_settings(self, settings: GuildSettings) -> None:
        await self.db.execute(
            "INSERT INTO guild_settings (guild_id, officer_role_id, timezone) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE officer_role_id = VALUES(officer_role_id), timezone = VALUES(timezone)",
            (settings.guild_id, settings.officer_role_id, settings.timezone),
        )

    # ---------- Events ----------
    async def create_event(self, *, guild_id: int, channel_id: int, timezone: str, draft: RaidDraft,
                           start: datetime, end: datetime, user_id: int) -> int:
        _, event_id = await self.db.execute(
            "INSERT INTO raid_events (guild_id, channel_id, title, description, min_item_level, "
            "enchants_required, consumables_required, start_minute, duration_minutes, weekdays, timezone, "
            "occurrence_start, occurrence_end, created_by, updated_by, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())",
            (guild_id, channel_id, draft.title, draft.description, draft.min_item_level,
             draft.enchants_required, draft.consumables_required, draft.start_minute, draft.duration_minutes,
             draft.weekdays, timezone, _naive_utc(start), _naive_utc(end), user_id, user_id),
        )
        return event_id

    async def update_event(self, event_id: int, guild_id: int, draft: RaidDraft,
                           start: datetime, end: datetime, user_id: int) -> bool:
        """Edits keep the current cycle, so existing sign-ups are preserved."""
        rowcount, _ = await self.db.execute(
            "UPDATE raid_events SET title = %s, description = %s, min_item_level = %s, enchants_required = %s, "
            "consumables_required = %s, start_minute = %s, duration_minutes = %s, weekdays = %s, "
            "occurrence_start = %s, occurrence_end = %s, updated_by = %s WHERE id = %s AND guild_id = %s",
            (draft.title, draft.description, draft.min_item_level, draft.enchants_required,
             draft.consumables_required, draft.start_minute, draft.duration_minutes, draft.weekdays,
             _naive_utc(start), _naive_utc(end), user_id, event_id, guild_id),
        )
        return rowcount > 0

    async def get_event(self, event_id: int, guild_id: int | None = None) -> RaidEvent | None:
        sql, args = "SELECT * FROM raid_events WHERE id = %s AND active = 1", [event_id]
        if guild_id is not None:
            sql, args = sql + " AND guild_id = %s", [event_id, guild_id]
        row = await self.db.fetchone(sql, args)
        return RaidEvent.from_row(row) if row else None

    async def list_events(self, guild_id: int) -> list[RaidEvent]:
        rows = await self.db.fetchall(
            "SELECT * FROM raid_events WHERE guild_id = %s AND active = 1 ORDER BY id", (guild_id,)
        )
        return [RaidEvent.from_row(r) for r in rows]

    async def delete_event(self, event_id: int, guild_id: int) -> bool:
        rowcount, _ = await self.db.execute(
            "DELETE FROM raid_events WHERE id = %s AND guild_id = %s", (event_id, guild_id)
        )  # Sign-ups go with it (ON DELETE CASCADE)
        return rowcount > 0

    async def deactivate(self, event_id: int) -> None:
        await self.db.execute("UPDATE raid_events SET active = 0 WHERE id = %s", (event_id,))

    async def set_message_id(self, event_id: int, message_id: int) -> None:
        await self.db.execute("UPDATE raid_events SET message_id = %s WHERE id = %s", (message_id, event_id))

    # ---------- Rollover ----------
    async def due_events(self, now: datetime) -> list[RaidEvent]:
        rows = await self.db.fetchall(
            "SELECT * FROM raid_events WHERE active = 1 AND occurrence_end <= %s", (_naive_utc(now),)
        )
        return [RaidEvent.from_row(r) for r in rows]

    async def roll_over(self, event_id: int, expected_cycle: int,
                        start: datetime, end: datetime) -> tuple[RaidEvent, list[int]] | None:
        """Advance to the next occurrence and wipe the finished one's sign-ups.

        Returns the updated event and the user ids that were signed up, or None if someone beat us to it.
        """
        async with self.db.transaction() as cur:
            await cur.execute(
                "UPDATE raid_events SET cycle = cycle + 1, occurrence_start = %s, occurrence_end = %s "
                "WHERE id = %s AND cycle = %s AND active = 1",
                (_naive_utc(start), _naive_utc(end), event_id, expected_cycle),
            )
            if cur.rowcount == 0:
                return None
            await cur.execute("SELECT user_id FROM raid_signups WHERE event_id = %s AND cycle <= %s",
                              (event_id, expected_cycle))
            finished = [row["user_id"] for row in await cur.fetchall()]
            await cur.execute("DELETE FROM raid_signups WHERE event_id = %s AND cycle <= %s",
                              (event_id, expected_cycle))
            await cur.execute("SELECT * FROM raid_events WHERE id = %s", (event_id,))
            return RaidEvent.from_row(await cur.fetchone()), finished

    # ---------- Start reminders ----------
    async def due_reminders(self, now: datetime, grace_seconds: int) -> list[RaidEvent]:
        """Raids that started within the last `grace_seconds` and haven't had their reminder yet."""
        rows = await self.db.fetchall(
            "SELECT * FROM raid_events WHERE active = 1 AND reminded_cycle < cycle "
            "AND occurrence_start <= %s AND occurrence_start > %s",
            (_naive_utc(now), _naive_utc(now - timedelta(seconds=grace_seconds))),
        )
        return [RaidEvent.from_row(r) for r in rows]

    async def claim_reminder(self, event_id: int, cycle: int) -> bool:
        """Mark the cycle's reminder as sent. False if it already was (so it's only ever sent once)."""
        rowcount, _ = await self.db.execute(
            "UPDATE raid_events SET reminded_cycle = %s WHERE id = %s AND cycle = %s AND reminded_cycle < %s",
            (cycle, event_id, cycle, cycle),
        )
        return rowcount > 0

    # ---------- Sign-ups ----------
    async def still_signed_up(self, guild_id: int, user_ids: list[int]) -> set[int]:
        """Which of `user_ids` are signed up for the current occurrence of any active raid in the guild."""
        if not user_ids:
            return set()
        placeholders = ", ".join(["%s"] * len(user_ids))
        rows = await self.db.fetchall(
            "SELECT DISTINCT s.user_id FROM raid_signups s "
            "JOIN raid_events e ON e.id = s.event_id AND e.cycle = s.cycle "
            f"WHERE e.guild_id = %s AND e.active = 1 AND s.user_id IN ({placeholders})",
            (guild_id, *user_ids),
        )
        return {row["user_id"] for row in rows}

    async def get_signups(self, event_id: int, cycle: int) -> list[Signup]:
        rows = await self.db.fetchall(
            "SELECT user_id, role, display_name, signed_at FROM raid_signups "
            "WHERE event_id = %s AND cycle = %s ORDER BY signed_at, user_id",
            (event_id, cycle),
        )
        return [_signup(r) for r in rows]

    async def toggle_signup(self, event_id: int, message_id: int, user_id: int, display_name: str,
                            role: Role, now: datetime) -> ToggleResult:
        """Join/leave/swap atomically. The event row is locked, so the tank cap and rollover can't race."""
        async with self.db.transaction() as cur:
            await cur.execute("SELECT * FROM raid_events WHERE id = %s AND active = 1 FOR UPDATE", (event_id,))
            row = await cur.fetchone()
            if row is None:
                return ToggleResult(ToggleStatus.MISSING)
            event = RaidEvent.from_row(row)
            if event.message_id != message_id:
                return ToggleResult(ToggleStatus.STALE, event)
            if event.occurrence_end <= now:
                return ToggleResult(ToggleStatus.ENDED, event)

            await cur.execute(
                "SELECT user_id, role, display_name, signed_at FROM raid_signups "
                "WHERE event_id = %s AND cycle = %s ORDER BY signed_at, user_id",
                (event_id, event.cycle),
            )
            signups = [_signup(r) for r in await cur.fetchall()]
            current = next((s.role for s in signups if s.user_id == user_id), None)
            tank_count = sum(1 for s in signups if s.role is Role.TANK)

            status = decide_toggle(current, role, tank_count)
            key = (event_id, event.cycle, user_id)
            if status is ToggleStatus.LEFT:
                await cur.execute("DELETE FROM raid_signups WHERE event_id = %s AND cycle = %s AND user_id = %s", key)
                signups = [s for s in signups if s.user_id != user_id]
            elif status is ToggleStatus.JOINED:
                await cur.execute(
                    "INSERT INTO raid_signups (event_id, cycle, user_id, role, display_name, signed_at) "
                    "VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP())",
                    (*key, role.name, display_name),
                )
                signups.append(Signup(user_id, role, display_name, now))
            elif status is ToggleStatus.SWAPPED:
                await cur.execute(
                    "UPDATE raid_signups SET role = %s, display_name = %s "
                    "WHERE event_id = %s AND cycle = %s AND user_id = %s",
                    (role.name, display_name, *key),
                )
                signups = [Signup(user_id, role, display_name, s.signed_at) if s.user_id == user_id else s
                           for s in signups]
            return ToggleResult(status, event, signups, previous=current)


def _signup(row: dict) -> Signup:
    return Signup(row["user_id"], Role[row["role"]], row["display_name"], as_utc(row["signed_at"]))
