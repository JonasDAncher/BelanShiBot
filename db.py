"""Async MariaDB access (aiomysql) and schema bootstrap."""
from __future__ import annotations

import logging
import warnings
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Sequence

import aiomysql

import config

log = logging.getLogger(__name__)

SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id        BIGINT UNSIGNED NOT NULL,
        officer_role_id BIGINT UNSIGNED NULL,
        timezone        VARCHAR(64)     NOT NULL,
        PRIMARY KEY (guild_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS raid_events (
        id                   INT UNSIGNED     NOT NULL AUTO_INCREMENT,
        guild_id             BIGINT UNSIGNED  NOT NULL,
        channel_id           BIGINT UNSIGNED  NOT NULL,
        message_id           BIGINT UNSIGNED  NULL,
        title                VARCHAR(100)     NOT NULL,
        description          TEXT             NULL,
        min_item_level       SMALLINT UNSIGNED NULL,
        enchants_required    TINYINT(1)       NOT NULL DEFAULT 0,
        consumables_required TINYINT(1)       NOT NULL DEFAULT 0,
        start_minute         SMALLINT UNSIGNED NOT NULL COMMENT 'Local start time, minutes after midnight',
        duration_minutes     SMALLINT UNSIGNED NOT NULL,
        weekdays             TINYINT UNSIGNED NOT NULL COMMENT 'Bitmask, bit 0 = Monday',
        timezone             VARCHAR(64)      NOT NULL,
        cycle                INT UNSIGNED     NOT NULL DEFAULT 1 COMMENT 'Bumped on every rollover; scopes sign-ups',
        reminded_cycle       INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT 'Last cycle whose start reminder was sent',
        occurrence_start     DATETIME         NOT NULL COMMENT 'UTC',
        occurrence_end       DATETIME         NOT NULL COMMENT 'UTC',
        active               TINYINT(1)       NOT NULL DEFAULT 1,
        created_by           BIGINT UNSIGNED  NOT NULL,
        updated_by           BIGINT UNSIGNED  NOT NULL,
        created_at           DATETIME         NOT NULL,
        PRIMARY KEY (id),
        KEY idx_rollover (active, occurrence_end),
        KEY idx_guild (guild_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # Databases created before the start reminder existed (MariaDB supports IF NOT EXISTS here)
    """
    ALTER TABLE raid_events ADD COLUMN IF NOT EXISTS reminded_cycle INT UNSIGNED NOT NULL DEFAULT 0
        COMMENT 'Last cycle whose start reminder was sent' AFTER cycle
    """,
    """
    CREATE TABLE IF NOT EXISTS raid_signups (
        event_id     INT UNSIGNED    NOT NULL,
        cycle        INT UNSIGNED    NOT NULL,
        user_id      BIGINT UNSIGNED NOT NULL,
        role         ENUM('TANK','HEALER','DPS') NOT NULL,
        display_name VARCHAR(64)     NOT NULL,
        signed_at    DATETIME        NOT NULL,
        PRIMARY KEY (event_id, cycle, user_id),
        KEY idx_order (event_id, cycle, signed_at),
        CONSTRAINT fk_signup_event FOREIGN KEY (event_id)
            REFERENCES raid_events (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
)


class Database:
    def __init__(self) -> None:
        self._pool: aiomysql.Pool | None = None

    @property
    def pool(self) -> aiomysql.Pool:
        if self._pool is None:
            raise RuntimeError("Database is not connected")
        return self._pool

    async def connect(self) -> None:
        self._pool = await aiomysql.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            db=config.DB_NAME,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=5,
            pool_recycle=3600,
            cursorclass=aiomysql.DictCursor,
        )
        log.info("Connected to MariaDB at %s:%s/%s", config.DB_HOST, config.DB_PORT, config.DB_NAME)

    async def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def init_schema(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # "table already exists" notes
            for statement in SCHEMA:
                await self.execute(statement)
        log.info("Database schema is ready")

    # ---------- Query helpers ----------
    @asynccontextmanager
    async def _connection(self) -> AsyncIterator[aiomysql.Connection]:
        async with self.pool.acquire() as conn:
            await conn.ping(reconnect=True)  # Survives MariaDB restarts / idle timeouts
            yield conn

    async def fetchone(self, sql: str, args: Sequence[Any] | None = None) -> dict[str, Any] | None:
        async with self._connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, args)
            return await cur.fetchone()

    async def fetchall(self, sql: str, args: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        async with self._connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, args)
            return list(await cur.fetchall())

    async def execute(self, sql: str, args: Sequence[Any] | None = None) -> tuple[int, int]:
        """Run a statement. Returns (rowcount, lastrowid)."""
        async with self._connection() as conn, conn.cursor() as cur:
            await cur.execute(sql, args)
            return cur.rowcount, cur.lastrowid

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiomysql.cursors.Cursor]:
        """A transaction on one connection; commits on success, rolls back on any exception."""
        async with self._connection() as conn:
            await conn.begin()
            try:
                async with conn.cursor() as cur:
                    yield cur
            except BaseException:
                await conn.rollback()
                raise
            await conn.commit()
