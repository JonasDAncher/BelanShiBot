# Database setup (MariaDB)

The bot uses one dedicated schema in an existing MariaDB instance for the `/raid` feature.
Without database settings the bot still runs, but `/raid` is disabled.

## Requirements

- MariaDB 10.3 or newer. The schema uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- InnoDB tables. The bot uses transactions, `SELECT ... FOR UPDATE` and one foreign key with `ON DELETE CASCADE`.
- The bot connects over TCP with aiomysql. The default isolation level (`REPEATABLE READ`) is fine.

## 1. Schema and user

```sql
CREATE DATABASE belan_shi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'belan_shi'@'<bot-host>' IDENTIFIED BY '<strong-password>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
    ON belan_shi.* TO 'belan_shi'@'<bot-host>';
```

- **Privileges:** this is the full set the bot needs, tested against MariaDB 10.11. It needs no global privileges and no `DROP`.
- **`CREATE` and `ALTER`:** the bot needs these because it creates and migrates its own tables at startup. The statements are idempotent and run on every start. If you'd rather manage DDL yourself, start the bot once, then revoke `CREATE`, `ALTER`, `INDEX` and `REFERENCES`. The `ALTER ... IF NOT EXISTS` at startup becomes a no-op, but it may still need `ALTER`, so test after revoking.
- **`<bot-host>`** is the address the bot connects from:
  - `127.0.0.1` if the bot runs on the same machine and you set `DB_HOST=127.0.0.1`. It connects over TCP, not the socket, so `localhost` won't match.
  - The container's address or the Docker network range (for example `172.18.%`) if the bot runs in Docker. Or give the bot `network_mode: host`.

## 2. Bot configuration (`.env` next to `bot.py`)

```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=belan_shi
DB_PASSWORD=<strong-password>
DB_NAME=belan_shi
```

`.env` is in `.gitignore`. Make it readable only by the user that runs the bot (`chmod 600`).

## 3. Operational notes

- **Load:** at most 5 pooled connections. The bot polls about every 30 s, with a few writes per button click. Negligible load.
- **Idle connections:** the bot recycles connections after 1 h and pings before each use, so a restart of MariaDB or a short `wait_timeout` is handled.
- **Time zones:** all times are stored as UTC in `DATETIME` columns, written by the bot or with `UTC_TIMESTAMP()`. The server's `time_zone` doesn't matter, and the bot doesn't need the timezone tables.
- **Tables:** `guild_settings`, `raid_events` and `raid_signups`. Sign-ups are deleted when a raid moves to its next date, so the data stays small.
- **Backups:** `mariadb-dump --single-transaction belan_shi` is consistent without locking. Losing the data means losing the configured raids and current sign-ups, nothing worse.
- **Check:** on startup the bot logs `Connected to MariaDB at ...` and `Database schema is ready`. If the database can't be reached, the bot stops at startup and prints the MariaDB error.
