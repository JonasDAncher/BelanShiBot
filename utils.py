"""Small shared helpers."""
from __future__ import annotations

import logging

import discord

from config import DELETE_TIME, RAID_PARTICIPANT_ROLE
from models import ROLE_NAMES

log = logging.getLogger(__name__)


def human_duration(seconds: int) -> str:
    if seconds >= 60 and seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    return f"{seconds} seconds"


async def send_temp(interaction: discord.Interaction, content: str, *, seconds: int = DELETE_TIME) -> None:
    """Send an ephemeral notice that deletes itself. Works before or after the interaction was answered."""
    content = f"{content}\n-# *This message disappears in {human_duration(seconds)}*"
    if interaction.response.is_done():
        message = await interaction.followup.send(content, ephemeral=True, wait=True)
        await message.delete(delay=seconds)
    else:
        await interaction.response.send_message(content, ephemeral=True, delete_after=seconds)


async def ensure_roles(guild: discord.Guild) -> dict[str, discord.Role]:
    """Return the Tank/Healer/DPS roles of a guild, creating any that are missing.

    Raises discord.Forbidden / HTTPException if a role has to be created and that fails.
    """
    roles: dict[str, discord.Role] = {}
    for name in ROLE_NAMES:
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            log.info("Creating missing role %s on server %s", name, guild.name)
            role = await guild.create_role(name=name, reason="Belan Shi Bot: role used for key pings")
        roles[name] = role
    return roles


async def ensure_raid_role(guild: discord.Guild) -> discord.Role:
    """Return the RaidParticipant role of a guild, creating it if it is missing.

    It is created mentionable so the start reminder can ping it without the bot needing
    the "Mention All Roles" permission. Raises discord.HTTPException if creating it fails.
    """
    role = discord.utils.get(guild.roles, name=RAID_PARTICIPANT_ROLE)
    if role is None:
        log.info("Creating missing role %s on server %s", RAID_PARTICIPANT_ROLE, guild.name)
        role = await guild.create_role(
            name=RAID_PARTICIPANT_ROLE, mentionable=True,
            reason="Belan Shi Bot: role given to raid sign-ups and pinged when the raid starts",
        )
    return role
