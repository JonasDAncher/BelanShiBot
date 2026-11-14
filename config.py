"""Static configuration and tunables for the Belan Shi bot."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

import command_scopes

load_dotenv()

# ---------- Secrets / environment ----------
TOKEN: Final[str | None] = os.getenv("DISCORD_TOKEN")
SYNC_COMMANDS: Final[bool] = os.getenv("SYNC_COMMANDS", "true").lower() in {"1", "true", "yes"}

# ---------- UI timings (seconds) ----------
DELETE_TIME: Final[int] = 10               # Auto-delete delay for short ephemeral notices
ROLE_PICKER_LIFETIME: Final[int] = 120     # How long the /roles picker stays alive
LOCK_MESSAGE_LIFETIME: Final[int] = 14_000 # How long the "Run locked!" message stays
GROUP_FULL_REMINDER_DELAY: Final[int] = 600  # DM the creator if the group fills after this long

# ---------- Key command ----------
ANY_KEY_LEVEL: Final[int] = 99  # Key levels >= this are displayed as "any"


@dataclass(frozen=True)
class ChannelRule:
    """Restricts /key to a single channel in a given guild."""
    channel_id: int
    wrong_channel_message: str


KEY_CHANNEL_RULES: Final[dict[int, ChannelRule]] = {
    570190869609709569: ChannelRule(1342184148156284938, "Wrong channel"),          # Quack's guild
    489890364090744892: ChannelRule(786705743336046593, "Wrong channel, Gala..."),  # Test server
    368116240276914176: ChannelRule(374937731744268289, "Wrong channel, Maya..."),  # Belan Shi
}

# ---------- Quiz ----------
QUIZ_ANSWER_TIME: Final[int] = 5
QUIZ_PAUSE_TIME: Final[int] = 5
QUIZ_POINTS_PER_ANSWER: Final[int] = 1

# ---------- Database (MariaDB) ----------
# Raid features need a database. If these are not set, the bot still starts without them.
DB_HOST: Final[str | None] = os.getenv("DB_HOST")
DB_PORT: Final[int] = int(os.getenv("DB_PORT", "3306"))
DB_USER: Final[str | None] = os.getenv("DB_USER")
DB_PASSWORD: Final[str] = os.getenv("DB_PASSWORD", "")
DB_NAME: Final[str | None] = os.getenv("DB_NAME")
DB_ENABLED: Final[bool] = all((DB_HOST, DB_USER, DB_NAME))

# ---------- Raids ----------
DEFAULT_TIMEZONE: Final[str] = os.getenv("DEFAULT_TIMEZONE", "UTC")  # Used until /raid setup is run
RAID_MAX_TANKS: Final[int] = 2
RAID_ROLLOVER_INTERVAL: Final[int] = 30  # Seconds between checks for finished/starting raids
RAID_PARTICIPANT_ROLE: Final[str] = "RaidParticipant"  # Given to everyone signed up; pinged when the raid starts
RAID_REMINDER_GRACE: Final[int] = 15 * 60  # Skip the start reminder if the bot only notices this many seconds late

# ---------- Which commands go to which servers (commands.toml) ----------
COMMAND_SCOPES: Final = command_scopes.load()


def raids_enabled_in(guild_id: int) -> bool:
    """Whether the raid feature (/raid and the RaidParticipant role) is enabled on this server."""
    return DB_ENABLED and COMMAND_SCOPES.scope_for("raid").includes(guild_id)
