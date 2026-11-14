"""The /roles command."""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import ROLE_PICKER_LIFETIME
from utils import ensure_roles, human_duration, send_temp
from views.role_picker import HIERARCHY_ERROR, RolePickerView

log = logging.getLogger(__name__)

PICKER_TEXT = """\
**You can self-assign roles using the buttons below, enabling their pings**
Click the buttons corresponding to the roles you wish to receive pings for when a `/key` run is started!
Press any role you __already__ have to disable pings again.

-# *This message disappears in {lifetime}*"""


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="roles", description="Creates a message with buttons to self-assign ping roles")
    @app_commands.guild_only()
    async def roles(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        try:
            roles = await ensure_roles(guild)
        except discord.HTTPException:
            log.exception("Could not create the ping roles in %s", guild.name)
            await send_temp(interaction, "I couldn't create the ping roles. I need the **Manage Roles** permission.", seconds=60)
            return

        # Role.is_assignable() is False if the role sits above the bot's top role (or the bot lacks Manage Roles)
        if not all(role.is_assignable() for role in roles.values()):
            await send_temp(
                interaction,
                HIERARCHY_ERROR.format(bot_role=guild.me.top_role.name),
                seconds=120,
            )
            log.error(
                "User %s in server %s called /roles but the role hierarchy is wrong",
                interaction.user.name, guild.name,
            )
            return

        await interaction.response.send_message(
            content=PICKER_TEXT.format(lifetime=human_duration(ROLE_PICKER_LIFETIME)),
            view=RolePickerView(),
            ephemeral=True,
            delete_after=ROLE_PICKER_LIFETIME,
        )
        log.info("User %s in server %s called the /roles command", interaction.user.name, guild.name)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roles(bot))
