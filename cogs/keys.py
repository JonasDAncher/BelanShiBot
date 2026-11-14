"""The /key command."""
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import KEY_CHANNEL_RULES
from models import KeyGroup
from utils import ensure_roles, send_temp
from views.key_signup import KeyView, build_key_content, build_key_embed

log = logging.getLogger(__name__)


class Keys(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="key", description="Create a group people can join using buttons")
    @app_commands.guild_only()
    @app_commands.rename(dungeon_name="dungeon-name", key_level="key-level", dps="missing-dps")
    @app_commands.describe(
        dungeon_name="Name of the dungeon (or 'any')",
        key_level="Level of the key - 99 or higher means any key level",
        tank="Do you need a tank? 1 = yes, 0 = no",
        healer="Do you need a healer? 1 = yes, 0 = no",
        dps="How many DPS are you missing? (0-3)",
        time="At a specific time?",
    )
    async def key(
        self,
        interaction: discord.Interaction,
        dungeon_name: app_commands.Range[str, 1, 60],
        key_level: app_commands.Range[int, 0, 999],
        tank: app_commands.Range[int, 0, 1] = 1,
        healer: app_commands.Range[int, 0, 1] = 1,
        dps: app_commands.Range[int, 0, 3] = 3,
        time: Optional[app_commands.Range[str, 1, 30]] = None,
    ) -> None:
        rule = KEY_CHANNEL_RULES.get(interaction.guild_id)
        if rule is not None and interaction.channel_id != rule.channel_id:
            await send_temp(interaction, rule.wrong_channel_message)
            return

        try:
            roles = await ensure_roles(interaction.guild)
        except discord.HTTPException:
            log.exception("Could not create the ping roles in %s", interaction.guild.name)
            await send_temp(
                interaction,
                "I couldn't create the `Tank`, `Healer` & `DPS` roles. "
                "Please give me the **Manage Roles** permission, or create them manually.",
                seconds=60,
            )
            return

        log.info(
            "NEW KEY: server=%s user=%s dungeon_name=%s key_level=%s tank=%s healer=%s dps=%s time=%s",
            interaction.guild.name, interaction.user.name, dungeon_name, key_level, tank, healer, dps, time,
        )

        group = KeyGroup.create(interaction.user, dungeon_name, key_level, time, tank=tank, healer=healer, dps=dps)
        await interaction.response.send_message(
            content=build_key_content(group, roles),
            embed=build_key_embed(group),
            view=KeyView(group),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Keys(bot))
