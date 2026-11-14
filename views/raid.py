"""Raid embed, persistent sign-up and options buttons, the officer options menu, the create/edit modal and a confirm dialog."""
from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

import discord
from discord import ui

from models import Role
from raids.entities import RaidEvent, Signup, ToggleStatus
from raids.permissions import is_raid_manager
from raids.schedule import (
    ScheduleError, format_days, format_duration, format_start, parse_days, parse_duration, parse_time,
)
from utils import send_temp

log = logging.getLogger(__name__)

ROLE_EMOJI = {Role.TANK: "🛡️", Role.HEALER: "💚", Role.DPS: "⚔️"}


# ---------- Embed ----------
def _column(signups: list[Signup], limit: int = 1000) -> str:
    if not signups:
        return "—"
    lines: list[str] = []
    used = 0
    for index, signup in enumerate(signups, start=1):
        line = f"{index}. {discord.utils.escape_markdown(signup.display_name[:24])}"
        if used + len(line) + 1 > limit:
            lines.append(f"*…and {len(signups) - index + 1} more*")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def build_raid_embed(event: RaidEvent, signups: list[Signup]) -> discord.Embed:
    start, end = int(event.occurrence_start.timestamp()), int(event.occurrence_end.timestamp())
    # <t:..> timestamps are rendered in every viewer's own time zone by Discord
    when = (
        f"🗓️ <t:{start}:F> · <t:{start}:R>\n"
        f"⏱️ {format_duration(event.duration_minutes)}, ends <t:{end}:t>"
    )
    embed = discord.Embed(
        title=event.title,
        description=f"{when}\n\n{event.description}" if event.description else when,
        colour=discord.Colour.blurple(),
    )

    ilvl = f"**{event.min_item_level}+**" if event.min_item_level else "No minimum"
    embed.add_field(
        name="📋 Requirements",
        value=(
            f"Item level: {ilvl}\n"
            f"Enchants: {'✅ Required' if event.enchants_required else '➖ Not required'}\n"
            f"Consumables: {'✅ Required' if event.consumables_required else '➖ Not required'}"
        ),
        inline=False,
    )

    by_role = {role: [s for s in signups if s.role is role] for role in Role}
    embed.add_field(name=f"🛡️ Tanks ({len(by_role[Role.TANK])})",
                    value=_column(by_role[Role.TANK]), inline=True)
    embed.add_field(name=f"💚 Healers ({len(by_role[Role.HEALER])})",
                    value=_column(by_role[Role.HEALER]), inline=True)
    embed.add_field(name=f"⚔️ DPS ({len(by_role[Role.DPS])})",
                    value=_column(by_role[Role.DPS]), inline=True)

    embed.set_footer(text=f"Raid #{event.id} • Repeats {format_days(event.weekdays)} • {len(signups)} signed up")
    return embed


def build_cancelled_embed(event: RaidEvent, signups: list[Signup], cancelled_by: str) -> discord.Embed:
    """The sign-up message of a raid that has been cancelled for good."""
    embed = build_raid_embed(event, signups)
    embed.title = f"❌ CANCELLED: {event.title}"[:256]
    embed.colour = discord.Colour.red()
    embed.description = f"**This raid has been cancelled by {discord.utils.escape_markdown(cancelled_by)} and will not repeat.**"
    embed.set_footer(text=f"Raid #{event.id} • Cancelled")
    return embed


# ---------- Persistent buttons ----------
class RaidRoleButton(ui.DynamicItem[ui.Button], template=r"raid:(?P<event>[0-9]+):(?P<role>tank|healer|dps)"):
    """custom_id carries the event id, so buttons keep working across bot restarts."""

    def __init__(self, event_id: int, role: Role) -> None:
        super().__init__(
            ui.Button(label=role.name, emoji=ROLE_EMOJI[role], custom_id=f"raid:{event_id}:{role.name.lower()}")
        )
        self.event_id = event_id
        self.role = role

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: ui.Button, match: re.Match, /):
        return cls(int(match["event"]), Role[match["role"].upper()])

    async def callback(self, interaction: discord.Interaction) -> None:
        service = interaction.client.raids
        result = await service.toggle_signup(self.event_id, interaction.message.id, interaction.user, self.role)

        if result.status is ToggleStatus.ENDED:
            await send_temp(interaction, "This raid has just ended - a fresh sign-up is about to be posted.")
        elif result.status in (ToggleStatus.STALE, ToggleStatus.MISSING):
            await send_temp(interaction, "This sign-up is outdated, so I'm removing it.")
            try:
                await interaction.message.delete()
            except discord.HTTPException:
                pass
        else:
            await interaction.response.edit_message(embed=build_raid_embed(result.event, result.signups))
            if isinstance(interaction.user, discord.Member):  # Role changes go after the reply, so it stays snappy
                await service.update_member_role(interaction.user, result)


class RaidOptionsButton(ui.DynamicItem[ui.Button], template=r"raid:(?P<event>[0-9]+):options"):
    """Opens the officer menu (skip / cancel / delete). Everyone sees it; only officers and admins can use it."""

    def __init__(self, event_id: int) -> None:
        super().__init__(
            ui.Button(label="Options", emoji="⚙️", style=discord.ButtonStyle.secondary,
                      custom_id=f"raid:{event_id}:options")
        )
        self.event_id = event_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: ui.Button, match: re.Match, /):
        return cls(int(match["event"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        repo = interaction.client.raids.repo
        if not isinstance(interaction.user, discord.Member) or not await is_raid_manager(repo, interaction.user):
            await send_temp(interaction, "Only officers and server admins can manage raids.")
            return
        event = await repo.get_event(self.event_id, interaction.guild_id)
        if event is None or event.message_id != interaction.message.id:
            await send_temp(interaction, "This sign-up is outdated, so I'm removing it.")
            try:
                await interaction.message.delete()
            except discord.HTTPException:
                pass
            return
        await interaction.response.send_message(
            options_text(event), view=RaidOptionsView(event, interaction.user.id), ephemeral=True
        )


class RaidView(ui.View):
    def __init__(self, event_id: int) -> None:
        super().__init__(timeout=None)
        for role in Role:
            self.add_item(RaidRoleButton(event_id, role))
        self.add_item(RaidOptionsButton(event_id))


# ---------- Officer options menu ----------
def options_text(event: RaidEvent) -> str:
    start = int(event.occurrence_start.timestamp())
    return (f"**{discord.utils.escape_markdown(event.title)}** (#{event.id}), next on <t:{start}:F>\n"
            "What do you want to do?")


class RaidOptionsView(ui.View):
    """Ephemeral menu for officers. Every action asks for confirmation first."""

    def __init__(self, event: RaidEvent, user_id: int) -> None:
        super().__init__(timeout=180)
        self.event = event
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def _confirm(self, interaction: discord.Interaction, question: str, label: str,
                       action: Callable[[discord.Interaction, RaidEvent], Awaitable[str]]) -> None:
        async def on_confirm(inter: discord.Interaction) -> None:
            await inter.response.edit_message(content="Working on it…", view=None)
            service = inter.client.raids
            event = await service.repo.get_event(self.event.id, inter.guild_id)  # Re-read: it may have changed
            if event is None:
                result = "That raid no longer exists."
            elif event.cycle != self.event.cycle:
                result = "That raid has moved on to its next date in the meantime. Nothing was changed."
            else:
                result = await action(inter, event)
            await inter.edit_original_response(content=result)

        async def on_back(inter: discord.Interaction) -> None:
            await inter.response.edit_message(content=options_text(self.event),
                                              view=RaidOptionsView(self.event, self.user_id))

        self.stop()
        await interaction.response.edit_message(
            content=question, view=ConfirmView(self.user_id, on_confirm, label=label, on_cancel=on_back,
                                               cancel_label="Back"))

    @ui.button(label="Skip this one", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: ui.Button) -> None:
        start = int(self.event.occurrence_start.timestamp())
        await self._confirm(
            interaction,
            f"Cancel **{discord.utils.escape_markdown(self.event.title)}** on <t:{start}:F> and move on to the next date?\n"
            "-# Everyone signed up is pinged, and their sign-ups are cleared.",
            "Skip it", self._do_skip,
        )

    @ui.button(label="Cancel raid", emoji="❌", style=discord.ButtonStyle.danger)
    async def cancel_raid(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._confirm(
            interaction,
            f"Cancel **{discord.utils.escape_markdown(self.event.title)}** for good?\n"
            "-# It stops repeating, the sign-up is marked as cancelled, and everyone signed up is pinged.",
            "Cancel raid", self._do_cancel,
        )

    @ui.button(label="Delete raid", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._confirm(
            interaction,
            f"Delete **{discord.utils.escape_markdown(self.event.title)}** and all of its sign-ups?\n"
            "-# The sign-up message is removed and nobody is notified.",
            "Delete", self._do_delete,
        )

    @staticmethod
    async def _do_skip(interaction: discord.Interaction, event: RaidEvent) -> str:
        if event.occurrence_end <= datetime.now(timezone.utc):
            return "That raid has already ended; a sign-up for the next date is posted automatically."
        updated = await interaction.client.raids.skip_occurrence(event, interaction.user.display_name)
        if updated is None:
            return "That raid has moved on to its next date in the meantime. Nothing was changed."
        return f"⏭️ Skipped. Next date: <t:{int(updated.occurrence_start.timestamp())}:F>"

    @staticmethod
    async def _do_cancel(interaction: discord.Interaction, event: RaidEvent) -> str:
        await interaction.client.raids.cancel_event(event, interaction.user.display_name)
        return f"❌ Raid #{event.id} cancelled."

    @staticmethod
    async def _do_delete(interaction: discord.Interaction, event: RaidEvent) -> str:
        await interaction.client.raids.delete_event(event)
        return f"🗑️ Raid #{event.id} deleted."


# ---------- Create / edit modal ----------
@dataclass
class RaidForm:
    title: str
    description: str
    start_minute: int
    duration_minutes: int
    weekdays: int


class RaidFormModal(ui.Modal):
    def __init__(self, *, title: str, handler: Callable[[discord.Interaction, RaidForm], Awaitable[None]],
                 initial: RaidEvent | None = None) -> None:
        super().__init__(title=title)
        self.handler = handler
        self.title_input = ui.TextInput(
            label="Title", max_length=100, placeholder="Heroic Raid Night",
            default=initial.title if initial else None,
        )
        self.description_input = ui.TextInput(
            label="Description", style=discord.TextStyle.paragraph, required=False, max_length=1000,
            placeholder="Anything raiders should know", default=(initial.description or None) if initial else None,
        )
        self.start_input = ui.TextInput(
            label="Start time (24h)", max_length=8, placeholder="19:30",
            default=format_start(initial.start_minute) if initial else None,
        )
        self.duration_input = ui.TextInput(
            label="Duration", max_length=16, placeholder="2h30m  /  2.5h  /  150m",
            default=format_duration(initial.duration_minutes) if initial else None,
        )
        self.days_input = ui.TextInput(
            label="Repeats on", max_length=60, placeholder="Thu, Sun",
            default=format_days(initial.weekdays) if initial else None,
        )
        for item in (self.title_input, self.description_input, self.start_input,
                     self.duration_input, self.days_input):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            title = self.title_input.value.strip()
            if not title:
                raise ScheduleError("The title can't be empty")
            form = RaidForm(
                title=title,
                description=self.description_input.value.strip(),
                start_minute=parse_time(self.start_input.value),
                duration_minutes=parse_duration(self.duration_input.value),
                weekdays=parse_days(self.days_input.value),
            )
        except ScheduleError as exc:
            await interaction.response.send_message(
                f"⚠️ {exc}\nNothing was saved - please run the command again.", ephemeral=True
            )
            return
        await self.handler(interaction, form)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error("Raid form failed", exc_info=error)
        message = "Something went wrong saving that raid. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


# ---------- Confirm dialog ----------
class ConfirmView(ui.View):
    def __init__(self, user_id: int, on_confirm: Callable[[discord.Interaction], Awaitable[None]], *,
                 label: str = "Delete", on_cancel: Callable[[discord.Interaction], Awaitable[None]] | None = None,
                 cancel_label: str = "Keep it") -> None:
        super().__init__(timeout=60)
        self.user_id = user_id
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.confirm.label = label
        self.cancel.label = cancel_label

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button) -> None:
        self.stop()
        await self.on_confirm(interaction)

    @ui.button(label="Keep it", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button) -> None:
        self.stop()
        if self.on_cancel is not None:
            await self.on_cancel(interaction)
        else:
            await interaction.response.edit_message(content="Cancelled - the raid is untouched.", view=None)
