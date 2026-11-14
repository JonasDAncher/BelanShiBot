"""Raid embed, persistent sign-up buttons, the create/edit modal and a confirm dialog."""
from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import discord
from discord import ui

import config
from models import Role
from raids.entities import RaidEvent, Signup, ToggleStatus
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
    embed.add_field(name=f"🛡️ Tanks ({len(by_role[Role.TANK])}/{config.RAID_MAX_TANKS})",
                    value=_column(by_role[Role.TANK]), inline=True)
    embed.add_field(name=f"💚 Healers ({len(by_role[Role.HEALER])})",
                    value=_column(by_role[Role.HEALER]), inline=True)
    embed.add_field(name=f"⚔️ DPS ({len(by_role[Role.DPS])})",
                    value=_column(by_role[Role.DPS]), inline=True)

    embed.set_footer(text=f"Raid #{event.id} • Repeats {format_days(event.weekdays)} • {len(signups)} signed up")
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

        if result.status is ToggleStatus.ROLE_FULL:
            await send_temp(interaction, f"All {config.RAID_MAX_TANKS} tank spots are taken, sorry.")
        elif result.status is ToggleStatus.ENDED:
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


class RaidView(ui.View):
    def __init__(self, event_id: int) -> None:
        super().__init__(timeout=None)
        for role in Role:
            self.add_item(RaidRoleButton(event_id, role))


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
    def __init__(self, user_id: int, on_confirm: Callable[[discord.Interaction], Awaitable[None]]) -> None:
        super().__init__(timeout=60)
        self.user_id = user_id
        self.on_confirm = on_confirm

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button) -> None:
        self.stop()
        await self.on_confirm(interaction)

    @ui.button(label="Keep it", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(content="Cancelled - the raid is untouched.", view=None)
