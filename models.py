"""Pure state/logic for a key group. No Discord API calls happen here."""
from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field

import discord

from config import ANY_KEY_LEVEL
from content import FLAVOR_TEXTS

DPS_SLOTS = 3


class Role(enum.Enum):
    TANK = "Tank"
    HEALER = "Healer"
    DPS = "DPS"

    @property
    def full_message(self) -> str:
        return "DPS spots taken, sorry." if self is Role.DPS else f"{self.value} spot taken, sorry."


ROLE_NAMES: tuple[str, ...] = tuple(role.value for role in Role)


class SignupResult(enum.Enum):
    JOINED = enum.auto()
    LEFT = enum.auto()
    SWAPPED = enum.auto()
    FULL = enum.auto()


@dataclass(frozen=True)
class SignupOutcome:
    result: SignupResult
    role: Role
    previous: Role | None = None


@dataclass
class KeyGroup:
    creator: discord.abc.User
    dungeon_name: str
    key_level: int
    time: str | None
    flavor_text: str
    tank_reserved: bool
    healer_reserved: bool
    dps_reserved: int
    tank: discord.abc.User | None = None
    healer: discord.abc.User | None = None
    dps: list[discord.abc.User] = field(default_factory=list)
    locked: bool = False
    lock_message: discord.PartialMessage | None = None

    @classmethod
    def create(cls, creator, dungeon_name: str, key_level: int, time: str | None,
               *, tank: int, healer: int, dps: int) -> "KeyGroup":
        """`tank`, `healer` and `dps` are how many of each role are still *needed*."""
        return cls(
            creator=creator,
            dungeon_name=dungeon_name,
            key_level=key_level,
            time=time,
            flavor_text=random.choice(FLAVOR_TEXTS),
            tank_reserved=tank == 0,
            healer_reserved=healer == 0,
            dps_reserved=DPS_SLOTS - dps,
        )

    # ---------- Display helpers ----------
    @property
    def label(self) -> str:
        level = "*any*" if self.key_level >= ANY_KEY_LEVEL else self.key_level
        at = f" at {self.time}" if self.time else ""
        return f"{self.dungeon_name} +{level}{at}"

    @property
    def dps_needed(self) -> int:
        return DPS_SLOTS - self.dps_reserved

    # ---------- Signup logic ----------
    def role_of(self, user) -> Role | None:
        if self.tank is not None and self.tank.id == user.id:
            return Role.TANK
        if self.healer is not None and self.healer.id == user.id:
            return Role.HEALER
        if any(p.id == user.id for p in self.dps):
            return Role.DPS
        return None

    def is_full(self, role: Role) -> bool:
        if role is Role.TANK:
            return self.tank_reserved or self.tank is not None
        if role is Role.HEALER:
            return self.healer_reserved or self.healer is not None
        return self.dps_reserved + len(self.dps) >= DPS_SLOTS

    def is_group_full(self) -> bool:
        return all(self.is_full(role) for role in Role)

    def toggle(self, user, role: Role) -> SignupOutcome:
        """Click on a role button: leave it if already in it, otherwise join (swapping if needed)."""
        current = self.role_of(user)
        if current is role:
            self._remove(user, role)
            return SignupOutcome(SignupResult.LEFT, role, current)
        if self.is_full(role):
            return SignupOutcome(SignupResult.FULL, role, current)
        if current is not None:
            self._remove(user, current)
        self._add(user, role)
        result = SignupResult.SWAPPED if current is not None else SignupResult.JOINED
        return SignupOutcome(result, role, current)

    def _add(self, user, role: Role) -> None:
        if role is Role.TANK:
            self.tank = user
        elif role is Role.HEALER:
            self.healer = user
        else:
            self.dps.append(user)

    def _remove(self, user, role: Role) -> None:
        if role is Role.TANK:
            self.tank = None
        elif role is Role.HEALER:
            self.healer = None
        else:
            self.dps = [p for p in self.dps if p.id != user.id]
