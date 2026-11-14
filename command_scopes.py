"""Reads commands.toml: which slash commands are registered on which servers."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

import discord
from discord import app_commands

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).with_name("commands.toml")
DEFAULT_SERVER = "test"  # Where commands missing from the file go


class CommandConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Scope:
    """`guild_ids is None` means global."""
    guild_ids: frozenset[int] | None

    @property
    def is_global(self) -> bool:
        return self.guild_ids is None

    def includes(self, guild_id: int) -> bool:
        return self.guild_ids is None or guild_id in self.guild_ids


@dataclass(frozen=True)
class CommandScopes:
    servers: dict[str, int]
    commands: dict[str, Scope]

    def scope_for(self, command: str) -> Scope:
        if command in self.commands:
            return self.commands[command]
        return Scope(frozenset({self.servers[DEFAULT_SERVER]}))

    def known_guild_ids(self) -> set[int]:
        """Every server named in the file, so commands removed from a server get cleared there."""
        ids = set(self.servers.values())
        for scope in self.commands.values():
            ids |= scope.guild_ids or set()
        return ids


def load(path: Path = CONFIG_PATH) -> CommandScopes:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CommandConfigError(f"{path.name} is missing") from None
    except tomllib.TOMLDecodeError as e:
        raise CommandConfigError(f"{path.name} is not valid TOML: {e}") from None

    servers: dict[str, int] = {}
    for name, value in data.get("servers", {}).items():
        if not isinstance(value, int):
            raise CommandConfigError(f"[servers] {name} must be a server ID (a number), got {value!r}")
        servers[name] = value
    if DEFAULT_SERVER not in servers:
        raise CommandConfigError(f"[servers] must define '{DEFAULT_SERVER}' (used for unlisted commands)")

    def resolve(command: str, entry) -> int:
        if isinstance(entry, int):
            return entry
        if isinstance(entry, str) and entry in servers:
            return servers[entry]
        raise CommandConfigError(f"[commands] {command}: unknown server {entry!r} (add it under [servers])")

    commands: dict[str, Scope] = {}
    for command, value in data.get("commands", {}).items():
        if value == "global":
            commands[command] = Scope(None)
        elif isinstance(value, list):
            commands[command] = Scope(frozenset(resolve(command, e) for e in value))
        else:
            raise CommandConfigError(f"[commands] {command} must be \"global\" or a list of servers, got {value!r}")
    return CommandScopes(servers, commands)


def apply(tree: app_commands.CommandTree, scopes: CommandScopes) -> None:
    """Move every globally added command to the servers commands.toml says it belongs on.

    Cogs add their commands globally; this is the single place that decides where they end up.
    """
    loaded = {cmd.name for cmd in tree.get_commands()}
    for name in scopes.commands.keys() - loaded:
        log.warning("commands.toml lists /%s, but no loaded extension provides it", name)

    for command in tree.get_commands():
        scope = scopes.scope_for(command.name)
        if command.name not in scopes.commands:
            log.warning("/%s is not in commands.toml; registering it on the '%s' server only",
                        command.name, DEFAULT_SERVER)
        if scope.is_global:
            log.info("/%s: global", command.name)
            continue
        tree.remove_command(command.name)
        for guild_id in sorted(scope.guild_ids):
            tree.add_command(command, guild=discord.Object(id=guild_id))
        log.info("/%s: servers %s", command.name, ", ".join(map(str, sorted(scope.guild_ids))) or "none (disabled)")
