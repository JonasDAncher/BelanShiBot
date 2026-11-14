"""Static text content: flavour lines, welcome message and quiz questions."""
from __future__ import annotations

from dataclasses import dataclass

FLAVOR_TEXTS: tuple[str, ...] = (
    "Are you ready for a team building exercise?",
    "Time to beat the record death count!",
    "It'll be fiiiiine.",
    "Got the glue ready?",
    "Where are you oompa loompas going?",
    "Watch out for the ledges.",
    "That's not what she said!",
    "It's like a group full of dad jokes.",
    "Remember to buy shoes!",
    "Did you know, visibility in lava is very bad.",
    "Remember to moisturize!",
    "Found a breedable gnome yet?",
    "It's gonna be a kind of magic!",
    "Spears.",
    "You can see trees with eyes.",
    "Your mom's a hoe.",
    "It's going to be a *special* run",
)

WELCOME_MESSAGE = """\
Hello! You've added the __Belan Shi Bot__ to your server. Here's how it works.

It has added 3 roles to your server: `Tank`, `Healer`, & `DPS`. These are the roles it will ping. They're intended to be assigned based on player preference.

Anyone can call the `/roles` command and select the roles they wish to receive pings for. Clicking a role button when you already have the role removes it, disabling pings again.

`/key` is the command to start a Mythic Plus run. It has two things you must decide, and 4 optional ones.
**REQUIRED** `dungeon-name` - the name of the dungeon you wanna run. You can type `any` if you don't have a specific one in mind.
**REQUIRED** `key-level` - the level of the keystone. Use any number of `99` or above if you don't care which level.
*OPTIONAL* `tank` - How many tanks do you need? `0` if you already have a tank, or `1` if you need one.
*OPTIONAL* `healer` - Same as tanks: `0` or `1`.
*OPTIONAL* `missing-dps` - How many DPS are you missing? `0` - `3`.
*OPTIONAL* `time` - If there's a specific time you'd like to run the key.

Leaving the optional ones empty creates a group that needs all roles.

When you write `/key`, Discord will help you fill in the options with a handy little UI. If you've done everything right, the bot will post a sign-up message, much like our raid and M+ sign-ups. As the creator, you can :x: `CANCEL` and :white_check_mark: `LOCK RUN`. Cancelling deletes the sign-up post. Locking disables the sign-up buttons and posts the team in a new message.
"""


@dataclass(frozen=True)
class QuizQuestion:
    prompt: str
    options: tuple[str, str, str, str]
    answer: int  # Index of the correct option (0-3)

    def __post_init__(self) -> None:
        if len(self.options) != 4 or not 0 <= self.answer < 4:
            raise ValueError(f"Invalid quiz question: {self.prompt!r}")


QUIZ_QUESTIONS: tuple[QuizQuestion, ...] = (
    QuizQuestion("What language is this bot written in?", ("Java", "Python", "C#", "C++"), answer=1),
    QuizQuestion("What is the guild called?", ("Belan Shi", "Echo", "Liquid", "Method"), answer=0),
    QuizQuestion("This is a test question, the correct answer is wow", ("4", "movies", "potato", "WoW"), answer=3),
    QuizQuestion("Who sucks?", ("1", "Gala's great", "Maya sucks", "2"), answer=2),
)
