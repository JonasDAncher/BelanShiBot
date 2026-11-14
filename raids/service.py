"""Glue between the repository and Discord: posting, refreshing, reposting, signing up, the RaidParticipant role."""
from __future__ import annotations

import logging
from datetime import datetime

import discord

import config
from models import Role
from raids.entities import RaidEvent, ToggleResult, ToggleStatus
from raids.repository import RaidRepository
from raids.schedule import UTC
from utils import ensure_raid_role
from views.raid import RaidView, build_raid_embed

log = logging.getLogger(__name__)


class RaidService:
    def __init__(self, bot: discord.Client, repo: RaidRepository) -> None:
        self.bot = bot
        self.repo = repo

    async def _channel(self, event: RaidEvent):
        return self.bot.get_channel(event.channel_id) or await self.bot.fetch_channel(event.channel_id)

    async def post(self, event: RaidEvent) -> discord.Message:
        """Post the sign-up message for the event's current occurrence."""
        channel = await self._channel(event)
        signups = await self.repo.get_signups(event.id, event.cycle)
        message = await channel.send(embed=build_raid_embed(event, signups), view=RaidView(event.id))
        await self.repo.set_message_id(event.id, message.id)
        event.message_id = message.id
        return message

    async def refresh(self, event: RaidEvent) -> None:
        """Edit the existing message in place; post a new one if it has been deleted."""
        if event.message_id is not None:
            channel = await self._channel(event)
            signups = await self.repo.get_signups(event.id, event.cycle)
            try:
                await channel.get_partial_message(event.message_id).edit(embed=build_raid_embed(event, signups))
                return
            except discord.NotFound:
                pass
        await self.post(event)

    async def repost(self, event: RaidEvent) -> None:
        """Post a fresh message (bumping it to the bottom of the channel) and remove the old one."""
        old_message_id = event.message_id
        try:
            await self.post(event)
        except discord.NotFound:
            log.warning("Channel for raid #%s no longer exists; deactivating it", event.id)
            signups = await self.repo.get_signups(event.id, event.cycle)
            await self.repo.deactivate(event.id)
            await self.release_participants(event.guild_id, [s.user_id for s in signups])
            return
        except discord.Forbidden:
            log.warning("Missing permission to post raid #%s in channel %s", event.id, event.channel_id)
            return
        await self.delete_message(event.channel_id, old_message_id)

    async def delete_message(self, channel_id: int, message_id: int | None) -> None:
        if message_id is None:
            return
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            await channel.get_partial_message(message_id).delete()
        except discord.HTTPException:
            pass  # Already gone / no access: nothing to clean up

    async def delete_event(self, event: RaidEvent) -> None:
        signups = await self.repo.get_signups(event.id, event.cycle)
        await self.delete_message(event.channel_id, event.message_id)
        await self.repo.delete_event(event.id, event.guild_id)
        await self.release_participants(event.guild_id, [s.user_id for s in signups])

    async def toggle_signup(self, event_id: int, message_id: int, user: discord.abc.User, role: Role) -> ToggleResult:
        result = await self.repo.toggle_signup(
            event_id, message_id, user.id, user.display_name[:64], role, datetime.now(UTC)
        )
        if result.status in (ToggleStatus.JOINED, ToggleStatus.LEFT, ToggleStatus.SWAPPED):
            log.info("RAID #%s - %s: %s %s", event_id, user.display_name, result.status.name, role.name)
        return result

    # ---------- RaidParticipant role ----------
    async def participant_role(self, guild: discord.Guild) -> discord.Role | None:
        """The guild's RaidParticipant role (created if missing), or None if it can't be used."""
        try:
            role = await ensure_raid_role(guild)
        except discord.HTTPException:
            log.exception("Could not create the %s role in %s", config.RAID_PARTICIPANT_ROLE, guild.name)
            return None
        if not role.is_assignable():
            log.warning("Can't assign %s in %s: it is above my top role or I lack Manage Roles",
                        role.name, guild.name)
            return None
        return role

    async def update_member_role(self, member: discord.Member, result: ToggleResult) -> None:
        """Give the role on joining a raid; take it away on leaving, unless they're still in another raid."""
        try:
            if result.status is ToggleStatus.JOINED:
                role = await self.participant_role(member.guild)
                if role is not None and role not in member.roles:
                    await member.add_roles(role, reason=f"Signed up for raid #{result.event.id}")
            elif result.status is ToggleStatus.LEFT:
                await self.release_participants(member.guild.id, [member.id])
        except discord.HTTPException:
            log.exception("Could not update the %s role of %s", config.RAID_PARTICIPANT_ROLE, member)

    async def release_participants(self, guild_id: int, user_ids: list[int]) -> None:
        """Remove the role from these users, except those still signed up for another raid in the guild."""
        guild = self.bot.get_guild(guild_id)
        if guild is None or not user_ids:
            return
        role = discord.utils.get(guild.roles, name=config.RAID_PARTICIPANT_ROLE)
        if role is None or not role.is_assignable():
            return
        keep = await self.repo.still_signed_up(guild_id, user_ids)
        for user_id in set(user_ids) - keep:
            try:
                member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                if role in member.roles:
                    await member.remove_roles(role, reason="Raid finished or sign-up removed")
            except discord.NotFound:
                pass  # Left the server
            except discord.HTTPException:
                log.exception("Could not remove %s from user %s in %s", role.name, user_id, guild.name)

    # ---------- Start reminder ----------
    async def send_start_reminder(self, event: RaidEvent) -> None:
        """Ping RaidParticipant in the sign-up channel when the raid starts (once per occurrence)."""
        if not await self.repo.claim_reminder(event.id, event.cycle):
            return  # Already sent
        if not await self.repo.get_signups(event.id, event.cycle):
            log.info("Raid #%s started with no sign-ups; no reminder sent", event.id)
            return  # Pinging the role would only reach people from other raids
        guild = self.bot.get_guild(event.guild_id)
        if guild is None:
            return
        role = await self.participant_role(guild)
        if role is None:
            return
        channel = await self._channel(event)
        link = ""
        if event.message_id:
            link = f"\n-# Sign-up: https://discord.com/channels/{event.guild_id}/{event.channel_id}/{event.message_id}"
        await channel.send(
            f"{role.mention} **{discord.utils.escape_markdown(event.title)}** is starting now! ⚔️{link}",
            allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=[role]),
        )
        log.info("Sent start reminder for raid #%s", event.id)
