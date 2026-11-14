"""Buttons that let members toggle the Tank/Healer/DPS ping roles."""
from __future__ import annotations

import logging

import discord
from discord import ui

from config import ROLE_PICKER_LIFETIME
from models import Role
from utils import ensure_roles, send_temp

log = logging.getLogger(__name__)

HIERARCHY_ERROR = (
    "***Error***: All three of the `Tank`, `Healer`, & `DPS` roles must be lower in the role hierarchy "
    "than the bot's highest role (`{bot_role}`).\n"
    "If you are __not__ a server admin, you should inform one of the issue."
)


class RolePickerView(ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=ROLE_PICKER_LIFETIME)

    async def _toggle(self, interaction: discord.Interaction, role_name: str) -> None:
        guild = interaction.guild
        user = interaction.user
        try:
            role = (await ensure_roles(guild))[role_name]
            if role in user.roles:
                await user.remove_roles(role)
                action = "disabled"
            else:
                await user.add_roles(role)
                action = "enabled"
        except discord.Forbidden:
            log.warning("Cannot manipulate the role %s in server %s", role_name, guild.name)
            await send_temp(
                interaction,
                HIERARCHY_ERROR.format(bot_role=guild.me.top_role.name),
                seconds=60,
            )
            return

        await send_temp(interaction, f"You've **__{action}__** pings for the {role.name} role")
        log.info("User %s in server %s %s pings for %s", user.name, guild.name, action, role.name)

    @ui.button(label="TANK", emoji="🛡️")
    async def tank_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._toggle(interaction, Role.TANK.value)

    @ui.button(label="HEALER", emoji="💚")
    async def healer_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._toggle(interaction, Role.HEALER.value)

    @ui.button(label="DPS", emoji="⚔️")
    async def dps_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        await self._toggle(interaction, Role.DPS.value)
