"""Who may create/edit raids: server admins and members holding the configured officer role."""
from __future__ import annotations

import discord
from discord import app_commands


class NotRaidManager(app_commands.CheckFailure):
    def __init__(self) -> None:
        super().__init__("Only officers and server admins can manage raids.")


async def is_raid_manager(repo, member: discord.Member) -> bool:
    if member.guild_permissions.administrator or member.id == member.guild.owner_id:
        return True
    settings = await repo.get_settings(member.guild.id)
    return settings.officer_role_id is not None and any(r.id == settings.officer_role_id for r in member.roles)


def raid_manager_only():
    """app_commands check; expects the bot to expose `raids` (RaidService)."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if await is_raid_manager(interaction.client.raids.repo, interaction.user):
            return True
        raise NotRaidManager()

    return app_commands.check(predicate)
