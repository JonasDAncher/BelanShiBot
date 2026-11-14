"""The /raid command group and the background task that sends start reminders and rolls finished raids over."""
import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from raids.entities import RaidDraft, RaidEvent
from raids.permissions import raid_manager_only
from raids.repository import RaidRepository
from raids.schedule import UTC, format_days, format_duration, format_start, occurrence_at
from raids.service import RaidService
from utils import send_temp
from views.raid import ConfirmView, RaidForm, RaidFormModal

log = logging.getLogger(__name__)

MinIlvl = app_commands.Range[int, 0, 1000]


@app_commands.guild_only()
class Raids(commands.GroupCog, group_name="raid", group_description="Recurring raid sign-ups"):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()  # Required for GroupCog subclasses that define __init__
        self.bot = bot
        self.repo = RaidRepository(bot.db)
        self.service = RaidService(bot, self.repo)

    async def cog_load(self) -> None:
        from views.raid import RaidRoleButton
        self.bot.raids = self.service
        self.bot.add_dynamic_items(RaidRoleButton)  # Makes buttons on existing messages work after a restart
        self.rollover_loop.start()

    async def cog_unload(self) -> None:
        from views.raid import RaidRoleButton
        self.rollover_loop.cancel()
        self.bot.remove_dynamic_items(RaidRoleButton)

    # ---------- Start reminders & rollover ----------
    @tasks.loop(seconds=config.RAID_ROLLOVER_INTERVAL)
    async def rollover_loop(self) -> None:
        try:
            now = datetime.now(UTC)
            for event in await self.repo.due_reminders(now, config.RAID_REMINDER_GRACE):
                try:
                    await self.service.send_start_reminder(event)
                except Exception:
                    log.exception("Start reminder failed for raid #%s", event.id)
            for event in await self.repo.due_events(now):
                try:
                    await self._roll_over(event, now)
                except Exception:
                    log.exception("Rollover failed for raid #%s", event.id)
        except Exception:
            log.exception("Rollover check failed")  # Keep the loop alive (e.g. DB briefly down)

    @rollover_loop.before_loop
    async def _before_rollover(self) -> None:
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:  # Make sure every raid-enabled server has the RaidParticipant role
            if config.raids_enabled_in(guild.id):
                await self.service.participant_role(guild)

    async def _roll_over(self, event: RaidEvent, now: datetime) -> None:
        start, end = occurrence_at(event.start_minute, event.duration_minutes, event.weekdays, event.timezone, now)
        rolled = await self.repo.roll_over(event.id, event.cycle, start, end)
        if rolled is None:
            return  # Another worker/edit got there first
        updated, finished_user_ids = rolled
        log.info("Raid #%s rolled over to %s", event.id, start.isoformat())
        await self.service.repost(updated)
        await self.service.release_participants(event.guild_id, finished_user_ids)

    # ---------- Autocomplete helpers ----------
    async def _event_choices(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[int]]:
        events = await self.repo.list_events(interaction.guild_id)
        needle = current.lower().lstrip("#")
        return [
            app_commands.Choice(name=f"#{e.id} {e.title}"[:100], value=e.id)
            for e in events if needle in e.title.lower() or needle in str(e.id)
        ][:25]

    # ---------- /raid setup ----------
    @app_commands.command(name="setup", description="Set the officer role and time zone for raids (admins only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        officer_role="Members with this role may create and edit raids (admins always can)",
        timezone="Time zone raid start times are entered in, e.g. Europe/Paris",
    )
    async def setup_cmd(self, interaction: discord.Interaction, officer_role: Optional[discord.Role] = None,
                        timezone: Optional[str] = None) -> None:
        settings = await self.repo.get_settings(interaction.guild_id)
        if timezone is not None:
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, ValueError):
                await send_temp(interaction, f"'{timezone}' isn't a valid time zone. Pick one from the suggestions.")
                return
            settings.timezone = timezone
        if officer_role is not None:
            settings.officer_role_id = officer_role.id
        if timezone is not None or officer_role is not None:
            await self.repo.save_settings(settings)
            log.info("Raid settings updated in guild %s by %s", interaction.guild_id, interaction.user)

        role = f"<@&{settings.officer_role_id}>" if settings.officer_role_id else "*not set* (only admins can manage raids)"
        await interaction.response.send_message(
            f"**Raid settings**\nOfficer role: {role}\nTime zone: `{settings.timezone}`\n"
            "-# Changing the time zone only affects raids created afterwards.",
            ephemeral=True, allowed_mentions=discord.AllowedMentions.none(),
        )

    @setup_cmd.autocomplete("timezone")
    async def _timezone_choices(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        needle = current.lower().replace(" ", "_")
        zones = sorted(z for z in available_timezones() if needle in z.lower())
        return [app_commands.Choice(name=z, value=z) for z in zones[:25]]

    # ---------- /raid create ----------
    @app_commands.command(name="create", description="Create a recurring raid sign-up (officers & admins)")
    @raid_manager_only()
    @app_commands.describe(
        min_item_level="Minimum item level (0 = no minimum)",
        enchants="Are enchants required?",
        consumables="Are consumables required?",
        channel="Where to post the sign-up (default: this channel)",
    )
    async def create(self, interaction: discord.Interaction, min_item_level: MinIlvl = 0, enchants: bool = False,
                     consumables: bool = False, channel: Optional[discord.TextChannel] = None) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await send_temp(interaction, "Please pick a normal text channel with the `channel` option.")
            return
        perms = target.permissions_for(interaction.guild.me)
        if not (perms.view_channel and perms.send_messages and perms.embed_links):
            await send_temp(interaction, f"I need **View Channel**, **Send Messages** and **Embed Links** in {target.mention}.")
            return

        async def handler(inter: discord.Interaction, form: RaidForm) -> None:
            await self._create(inter, form, target, min_item_level or None, enchants, consumables)

        await interaction.response.send_modal(RaidFormModal(title="Create a raid", handler=handler))

    async def _create(self, interaction: discord.Interaction, form: RaidForm, channel: discord.TextChannel,
                      min_item_level: int | None, enchants: bool, consumables: bool) -> None:
        await interaction.response.defer(ephemeral=True)
        settings = await self.repo.get_settings(interaction.guild_id)
        start, end = occurrence_at(form.start_minute, form.duration_minutes, form.weekdays,
                                   settings.timezone, datetime.now(UTC))
        draft = RaidDraft(form.title, form.description, min_item_level, enchants, consumables,
                          form.start_minute, form.duration_minutes, form.weekdays)
        event_id = await self.repo.create_event(
            guild_id=interaction.guild_id, channel_id=channel.id, timezone=settings.timezone,
            draft=draft, start=start, end=end, user_id=interaction.user.id,
        )
        event = await self.repo.get_event(event_id)
        try:
            message = await self.service.post(event)
        except discord.HTTPException:
            log.exception("Could not post raid #%s in channel %s", event_id, channel.id)
            await self.repo.delete_event(event_id, interaction.guild_id)
            await interaction.followup.send("I couldn't post in that channel, so nothing was created.", ephemeral=True)
            return
        log.info("Raid #%s created in guild %s by %s", event_id, interaction.guild_id, interaction.user)
        await interaction.followup.send(
            f"✅ Raid created: {message.jump_url}\n"
            f"-# Start time was read as `{settings.timezone}` time. Change it with `/raid setup`.",
            ephemeral=True,
        )

    # ---------- /raid edit ----------
    @app_commands.command(name="edit", description="Edit a raid (officers & admins)")
    @raid_manager_only()
    @app_commands.describe(
        event="The raid to edit",
        min_item_level="New minimum item level (0 = no minimum, leave empty to keep)",
        enchants="Change whether enchants are required (leave empty to keep)",
        consumables="Change whether consumables are required (leave empty to keep)",
    )
    async def edit(self, interaction: discord.Interaction, event: int, min_item_level: Optional[MinIlvl] = None,
                   enchants: Optional[bool] = None, consumables: Optional[bool] = None) -> None:
        current = await self.repo.get_event(event, interaction.guild_id)
        if current is None:
            await send_temp(interaction, f"I can't find raid #{event} on this server.")
            return

        async def handler(inter: discord.Interaction, form: RaidForm) -> None:
            await self._edit(inter, event, form, min_item_level, enchants, consumables)

        await interaction.response.send_modal(RaidFormModal(title=f"Edit raid #{current.id}", handler=handler, initial=current))

    @edit.autocomplete("event")
    async def _edit_event_choices(self, interaction: discord.Interaction, current: str):
        return await self._event_choices(interaction, current)

    async def _edit(self, interaction: discord.Interaction, event_id: int, form: RaidForm,
                    min_item_level: int | None, enchants: bool | None, consumables: bool | None) -> None:
        await interaction.response.defer(ephemeral=True)
        event = await self.repo.get_event(event_id, interaction.guild_id)  # Re-read: it may have changed meanwhile
        if event is None:
            await interaction.followup.send("That raid was deleted while you were editing it.", ephemeral=True)
            return
        ilvl = event.min_item_level if min_item_level is None else (min_item_level or None)
        draft = RaidDraft(
            form.title, form.description, ilvl,
            event.enchants_required if enchants is None else enchants,
            event.consumables_required if consumables is None else consumables,
            form.start_minute, form.duration_minutes, form.weekdays,
        )
        start, end = occurrence_at(form.start_minute, form.duration_minutes, form.weekdays,
                                   event.timezone, datetime.now(UTC))
        await self.repo.update_event(event.id, interaction.guild_id, draft, start, end, interaction.user.id)
        await self.service.refresh(await self.repo.get_event(event.id))  # Same cycle: sign-ups are kept
        log.info("Raid #%s edited by %s", event.id, interaction.user)
        await interaction.followup.send(f"✅ Raid #{event.id} updated.", ephemeral=True)

    # ---------- /raid delete ----------
    @app_commands.command(name="delete", description="Delete a raid and its sign-ups (officers & admins)")
    @raid_manager_only()
    @app_commands.describe(event="The raid to delete")
    async def delete(self, interaction: discord.Interaction, event: int) -> None:
        target = await self.repo.get_event(event, interaction.guild_id)
        if target is None:
            await send_temp(interaction, f"I can't find raid #{event} on this server.")
            return

        async def confirmed(inter: discord.Interaction) -> None:
            await self.service.delete_event(target)
            log.info("Raid #%s deleted by %s", target.id, inter.user)
            await inter.response.edit_message(content=f"🗑️ Raid #{target.id} deleted.", view=None)

        await interaction.response.send_message(
            f"Delete **{target.title}** (#{target.id}) and all of its sign-ups?",
            view=ConfirmView(interaction.user.id, confirmed), ephemeral=True,
        )

    @delete.autocomplete("event")
    async def _delete_event_choices(self, interaction: discord.Interaction, current: str):
        return await self._event_choices(interaction, current)

    # ---------- /raid repost ----------
    @app_commands.command(name="repost", description="Post a raid's sign-up message again (officers & admins)")
    @raid_manager_only()
    @app_commands.describe(event="The raid to repost")
    async def repost(self, interaction: discord.Interaction, event: int) -> None:
        target = await self.repo.get_event(event, interaction.guild_id)
        if target is None:
            await send_temp(interaction, f"I can't find raid #{event} on this server.")
            return
        await interaction.response.defer(ephemeral=True)
        await self.service.repost(target)
        await interaction.followup.send("✅ Reposted.", ephemeral=True)

    @repost.autocomplete("event")
    async def _repost_event_choices(self, interaction: discord.Interaction, current: str):
        return await self._event_choices(interaction, current)

    # ---------- /raid list ----------
    @app_commands.command(name="list", description="Show the raids set up on this server")
    async def list_cmd(self, interaction: discord.Interaction) -> None:
        events = await self.repo.list_events(interaction.guild_id)
        if not events:
            await send_temp(interaction, "No raids are set up yet. Officers can use `/raid create`.")
            return
        lines = []
        for e in events[:20]:
            start = int(e.occurrence_start.timestamp())
            lines.append(
                f"**#{e.id} {discord.utils.escape_markdown(e.title)}** in <#{e.channel_id}>\n"
                f"{format_days(e.weekdays)} at {format_start(e.start_minute)} `{e.timezone}` "
                f"({format_duration(e.duration_minutes)}) · next <t:{start}:R>"
            )
        await interaction.response.send_message(
            embed=discord.Embed(title="Raids", description="\n\n".join(lines), colour=discord.Colour.blurple()),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Raids(bot))  # Which servers get /raid is decided by commands.toml
