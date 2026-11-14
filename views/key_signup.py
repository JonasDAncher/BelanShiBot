"""The sign-up embed + buttons for a /key group."""
from __future__ import annotations

import asyncio
import logging

import discord
from discord import ui

from config import GROUP_FULL_REMINDER_DELAY, LOCK_MESSAGE_LIFETIME
from models import DPS_SLOTS, KeyGroup, Role, SignupResult
from utils import send_temp

log = logging.getLogger(__name__)

ZERO_WIDTH = "\u200b"


def _name(user: discord.abc.User) -> str:
    return discord.utils.escape_markdown(user.display_name)


# ---------- Rendering (state -> Discord objects) ----------
def build_key_embed(group: KeyGroup) -> discord.Embed:
    level = group.key_level
    color = 0x00FF00 if level < 5 else 0xFFFF00 if level <= 7 else 0xFF0000
    embed = discord.Embed(
        title=f"{_name(group.creator)} wants to run a {group.label}!",
        description=group.flavor_text,
        color=color,
    )

    if group.tank_reserved:
        tank = "❌ *Reserved*"
    elif group.tank is not None:
        tank = f"❌ {_name(group.tank)}"
    else:
        tank = "🛡️ Tank open"

    if group.healer_reserved:
        healer = "❌ *Reserved*"
    elif group.healer is not None:
        healer = f"❌ {_name(group.healer)}"
    else:
        healer = "💚 Healer open"

    taken = ["*Reserved*"] * group.dps_reserved + [_name(p) for p in group.dps]
    dps_lines = [
        f"❌ # {i + 1}: {taken[i]}" if i < len(taken) else f"⚔️ # {i + 1}: *Open*"
        for i in range(DPS_SLOTS)
    ]

    embed.add_field(name="TANK", value=tank, inline=False)
    embed.add_field(name="HEALER", value=healer, inline=False)
    embed.add_field(name="DPS", value="\n".join(dps_lines), inline=False)
    embed.set_footer(text="Want to receive pings? Use /roles and pick which!")
    return embed


def build_key_content(group: KeyGroup, roles: dict[str, discord.Role]) -> str:
    needs: list[str] = []
    if not group.tank_reserved:
        needs.append(roles[Role.TANK.value].mention)
    if not group.healer_reserved:
        needs.append(roles[Role.HEALER.value].mention)
    if group.dps_needed > 0:
        needs.append(f"{group.dps_needed} x {roles[Role.DPS.value].mention}")
    return (
        f"{group.creator.mention} wants to run a {group.label}!\n"
        f"They need {' '.join(needs) or 'nothing...?'}"
    )


def build_lock_message(group: KeyGroup) -> str:
    def slot(user, reserved: bool) -> str:
        return "*Reserved*" if reserved else user.mention if user is not None else "*Open*"

    dps = ["*Reserved*"] * group.dps_reserved + [p.mention for p in group.dps]
    dps += ["*Open*"] * (DPS_SLOTS - len(dps))
    return (
        "Run locked!"
        f"\n🛡️: {slot(group.tank, group.tank_reserved)}"
        f"\n💚: {slot(group.healer, group.healer_reserved)}"
        + "".join(f"\n⚔️ # {i + 1}: {entry}" for i, entry in enumerate(dps))
    )


# ---------- The view ----------
class KeyView(ui.View):
    def __init__(self, group: KeyGroup) -> None:
        super().__init__(timeout=None)
        self.group = group
        self._mutex = asyncio.Lock()
        self._refresh_buttons()

    # ----- helpers -----
    def _refresh_buttons(self) -> None:
        g = self.group
        self.tank_button.disabled = g.locked or g.tank_reserved
        self.healer_button.disabled = g.locked or g.healer_reserved
        self.dps_button.disabled = g.locked or g.dps_reserved >= DPS_SLOTS
        if g.locked:
            self.lock_button.label, self.lock_button.emoji = "UN-LOCK", "↩️"
        else:
            self.lock_button.label, self.lock_button.emoji = "LOCK RUN", "✅"

    def _log(self, interaction: discord.Interaction, text: str) -> None:
        log.info("KEY: %s - %s %s", interaction.message.id, interaction.user.display_name, text)

    async def _require_creator(self, interaction: discord.Interaction, verb: str) -> bool:
        if interaction.user.id == self.group.creator.id:
            return True
        await send_temp(interaction, f"You cannot {verb} a run you did not start!")
        return False

    async def _delete_lock_message(self) -> None:
        message, self.group.lock_message = self.group.lock_message, None
        if message is not None:
            try:
                await message.delete()
            except discord.HTTPException:
                pass

    # ----- role buttons -----
    async def _on_role_click(self, interaction: discord.Interaction, role: Role) -> None:
        async with self._mutex:
            outcome = self.group.toggle(interaction.user, role)
            if outcome.result is SignupResult.FULL:
                await send_temp(interaction, role.full_message)
                return
            await interaction.response.edit_message(embed=build_key_embed(self.group), view=self)

        if outcome.result is SignupResult.LEFT:
            self._log(interaction, f"un-joined as {role.name}")
        elif outcome.result is SignupResult.SWAPPED:
            self._log(interaction, f"swapped from {outcome.previous.name} to {role.name}")
        else:
            self._log(interaction, f"joined as {role.name}")
            await self._remind_creator(interaction)

    async def _remind_creator(self, interaction: discord.Interaction) -> None:
        """DM the creator when their (older) group fills up."""
        group = self.group
        if not group.is_group_full() or interaction.user.id == group.creator.id:
            return
        age = (discord.utils.utcnow() - interaction.message.created_at).total_seconds()
        if age <= GROUP_FULL_REMINDER_DELAY:
            return
        text = (
            f"The key group you made in {interaction.guild.name} has been filled!\n"
            f"# [Click here to see it!]({interaction.message.jump_url})\n"
            f"-# This reminder is sent to you because you made the group more than "
            f"{GROUP_FULL_REMINDER_DELAY // 60} minutes ago."
        )
        try:
            await group.creator.send(text)
        except discord.HTTPException:
            log.warning("Could not DM %s that their key group is full", group.creator)
        else:
            log.info("A reminder was sent to %s that their key group is full", group.creator)

    @ui.button(label="TANK", emoji="🛡️")
    async def tank_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._on_role_click(interaction, Role.TANK)

    @ui.button(label="HEALER", emoji="💚")
    async def healer_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._on_role_click(interaction, Role.HEALER)

    @ui.button(label="DPS", emoji="⚔️")
    async def dps_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._on_role_click(interaction, Role.DPS)

    # ----- creator-only buttons -----
    @ui.button(label="CANCEL", emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not await self._require_creator(interaction, "cancel"):
            return
        await send_temp(interaction, "Run cancelled!")
        await self._delete_lock_message()
        await interaction.message.delete()
        self._log(interaction, "cancelled the key.")
        self.stop()

    @ui.button(label="LOCK RUN", emoji="✅")
    async def lock_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if not await self._require_creator(interaction, "un-lock" if self.group.locked else "lock"):
            return

        if not self.group.locked:
            self.group.locked = True
            self._refresh_buttons()
            await interaction.response.edit_message(view=self)
            sent = await interaction.followup.send(build_lock_message(self.group), wait=True)
            # Use a bot-token handle so it can still be deleted after the interaction token expires.
            partial = interaction.channel.get_partial_message(sent.id)
            self.group.lock_message = partial
            await partial.delete(delay=LOCK_MESSAGE_LIFETIME)
            self._log(interaction, "locked the key.")
        else:
            self.group.locked = False
            self._refresh_buttons()
            await interaction.response.edit_message(view=self)
            await self._delete_lock_message()
            await send_temp(interaction, "Run un-locked!\nRole buttons activated.")
            self._log(interaction, "un-locked the key.")
