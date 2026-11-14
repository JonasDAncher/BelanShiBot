"""Entry point for the Belan Shi bot."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

import discord
from discord import app_commands
from discord.ext import commands

import command_scopes
import config

log = logging.getLogger("belan_shi")

CORE_EXTENSIONS = (
    "cogs.guild_events",
    "cogs.keys",
    "cogs.roles",
    "cogs.quiz",
)
DATABASE_EXTENSIONS = ("cogs.raids",)  # Only loaded when MariaDB is configured


class BelanShiBot(commands.Bot):
    db = None     # db.Database, set when the database is configured
    raids = None  # raids.service.RaidService, set by cogs.raids

    def __init__(self) -> None:
        # Slash commands + buttons only: no privileged intents needed.
        # (Enable Intents.members / message_content here if you add features that need them.)
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),
            # everyone=False stops user-supplied text (e.g. dungeon-name) from pinging @everyone
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=True, users=True),
        )

    async def setup_hook(self) -> None:
        self.tree.on_error = self.on_tree_error

        extensions = list(CORE_EXTENSIONS)
        if config.DB_ENABLED:
            from db import Database  # Imported lazily so the bot starts even without the DB driver installed
            self.db = Database()
            await self.db.connect()
            await self.db.init_schema()
            extensions += DATABASE_EXTENSIONS
        else:
            log.warning("DB_HOST/DB_USER/DB_NAME not set: /raid commands are disabled")

        for extension in extensions:
            await self.load_extension(extension)
            log.info("Loaded extension %s", extension)

        command_scopes.apply(self.tree, config.COMMAND_SCOPES)  # Where each command goes (commands.toml)

        if config.SYNC_COMMANDS:
            await self.tree.sync()  # Global commands
            # Every server in commands.toml is synced, also ones with no commands left, so removed ones disappear
            for guild_id in sorted(config.COMMAND_SCOPES.known_guild_ids()):
                try:
                    await self.tree.sync(guild=discord.Object(id=guild_id))
                except discord.HTTPException as e:  # e.g. the bot is not in that server
                    log.warning("Could not sync commands to server %s: %s", guild_id, e)
            log.info("Synced application commands")

    async def close(self) -> None:
        await super().close()
        if self.db is not None:
            await self.db.close()

    async def on_ready(self) -> None:
        log.info("%s successfully logged in with ID: %s", self.user, self.user.id)

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CheckFailure):  # NotRaidManager, MissingPermissions, ...
            message = str(error) or "You can't use that command."
        else:
            command = interaction.command.name if interaction.command else "unknown"
            log.error("Unhandled error in /%s", command, exc_info=error)
            message = "Something went wrong running that command. Please try again."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


def setup_logging() -> None:
    formatter = logging.Formatter(
        "{asctime} - {levelname} - {name} - {message}", style="{", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler = RotatingFileHandler("bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    console_handler = logging.StreamHandler()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
        root.addHandler(handler)


def main() -> None:
    setup_logging()
    if not config.TOKEN:
        log.critical("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    BelanShiBot().run(config.TOKEN, log_handler=None)  # We configured logging ourselves


if __name__ == "__main__":
    main()
