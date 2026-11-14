"""Guild lifecycle events: keep the Tank/Healer/DPS (and RaidParticipant) roles around and greet new servers."""
import logging

import discord
from discord.ext import commands

import config
from content import WELCOME_MESSAGE
from models import ROLE_NAMES
from utils import ensure_raid_role, ensure_roles

log = logging.getLogger(__name__)


class GuildEvents(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info("Joined server %s; checking roles", guild.name)
        try:
            await ensure_roles(guild)
        except discord.HTTPException:
            log.exception("Could not create the ping roles in %s", guild.name)
        if config.raids_enabled_in(guild.id):
            try:
                await ensure_raid_role(guild)
            except discord.HTTPException:
                log.exception("Could not create the %s role in %s", config.RAID_PARTICIPANT_ROLE, guild.name)

        channel = guild.system_channel
        if channel is None or not channel.permissions_for(guild.me).send_messages:
            log.info("No usable system channel in %s; skipping welcome message", guild.name)
            return
        log.info("Sending welcome message in %s", guild.name)
        await channel.send(WELCOME_MESSAGE)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        log.info("I was removed from guild %s", guild.name)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        if role.name == config.RAID_PARTICIPANT_ROLE and config.raids_enabled_in(role.guild.id):
            log.info("%s deleted the %s role. Recreating it.", role.guild.name, role.name)
            try:
                await ensure_raid_role(role.guild)
            except discord.HTTPException:
                log.exception("Could not recreate role %s in %s", role.name, role.guild.name)
            return
        if role.name not in ROLE_NAMES:
            return
        log.info("%s deleted the %s role. Recreating it.", role.guild.name, role.name)
        try:
            await role.guild.create_role(name=role.name, reason="Belan Shi Bot: role used for key pings")
        except discord.HTTPException:
            log.exception("Could not recreate role %s in %s", role.name, role.guild.name)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GuildEvents(bot))
