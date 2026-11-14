"""Quiz view: one coroutine drives the whole quiz instead of nested timers/closures."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

import discord
from discord import ui

from config import QUIZ_ANSWER_TIME, QUIZ_PAUSE_TIME, QUIZ_POINTS_PER_ANSWER
from content import QuizQuestion
from utils import send_temp

log = logging.getLogger(__name__)

ZERO_WIDTH = "\u200b"
NUMBER_EMOJI = ("1️⃣", "2️⃣", "3️⃣", "4️⃣")


class AnswerButton(ui.Button["QuizView"]):
    def __init__(self, index: int) -> None:
        super().__init__(emoji=NUMBER_EMOJI[index])
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.record_answer(interaction, self.index)


class QuizView(ui.View):
    def __init__(self, quizmaster: discord.abc.User, questions: Sequence[QuizQuestion],
                 base_embed: discord.Embed) -> None:
        super().__init__(timeout=None)
        self.quizmaster = quizmaster
        self.questions = questions
        self.base_embed = base_embed
        self.message: discord.Message | None = None

        self.players: dict[int, discord.abc.User] = {}
        self.scores: dict[int, int] = {}
        self.guesses: dict[int, int] = {}  # user id -> chosen option index (current question)
        self._task: asyncio.Task | None = None

    # ----- starting -----
    @ui.button(label="Start?", emoji="🏁")
    async def start_button(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.id != self.quizmaster.id:
            await send_temp(interaction, f"You're not the Quizmaster, {interaction.user.display_name}...")
            return

        self.clear_items()
        for index in range(4):
            self.add_item(AnswerButton(index))
        self.message = interaction.message
        await interaction.response.edit_message(view=self)

        self._task = asyncio.create_task(self._run())
        self._task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task) -> None:
        if not task.cancelled() and task.exception() is not None:
            log.error("Quiz task failed", exc_info=task.exception())

    # ----- answering -----
    async def record_answer(self, interaction: discord.Interaction, index: int) -> None:
        user = interaction.user
        self.players[user.id] = user
        self.scores.setdefault(user.id, 0)
        self.guesses[user.id] = index  # Pressing another button simply replaces the guess
        await interaction.response.send_message(
            f"You answered {NUMBER_EMOJI[index]}", ephemeral=True, delete_after=3
        )

    def _set_answers_enabled(self, enabled: bool) -> None:
        for item in self.children:
            if isinstance(item, AnswerButton):
                item.disabled = not enabled

    def _award_points(self, question: QuizQuestion) -> None:
        for user_id, guess in self.guesses.items():
            if guess == question.answer:
                self.scores[user_id] += QUIZ_POINTS_PER_ANSWER
        self.guesses.clear()

    # ----- the quiz loop -----
    async def _run(self) -> None:
        try:
            await self._play()
        except discord.NotFound:
            log.info("Quiz message was deleted; ending quiz")
            self.stop()

    async def _play(self) -> None:
        last = len(self.questions) - 1
        for index, question in enumerate(self.questions):
            self.guesses.clear()
            self._set_answers_enabled(True)
            for remaining in range(QUIZ_ANSWER_TIME, 0, -1):
                await self._edit(self._question_embed(index, f"{remaining} seconds left to answer!"))
                await asyncio.sleep(1)

            self._set_answers_enabled(False)
            self._award_points(question)

            upcoming = "Final results" if index == last else "Next question"
            for remaining in range(QUIZ_PAUSE_TIME, 0, -1):
                await self._edit(
                    self._question_embed(index, f"{upcoming} in {remaining} seconds...", reveal=True)
                )
                await asyncio.sleep(1)
        await self._finish()

    # ----- rendering -----
    async def _edit(self, embed: discord.Embed) -> None:
        await self.message.edit(embed=embed, view=self)

    def _question_embed(self, index: int, status: str, *, reveal: bool = False) -> discord.Embed:
        question = self.questions[index]
        embed = self.base_embed.copy()
        embed.add_field(name=ZERO_WIDTH, value="``` ```", inline=False)  # Spacer
        embed.add_field(
            name=f"Question # **{index + 1} / {len(self.questions)}**",
            value=f"**{question.prompt}**",
            inline=False,
        )
        for i, option in enumerate(question.options):
            if not reveal:
                text = f"> *{option}*"
            elif i == question.answer:
                text = f"> **>> {option} <<**"
            else:
                text = f"> ~~*{option}*~~"
            embed.add_field(name=str(i + 1), value=text, inline=True)
            if i == 1:
                embed.add_field(name=ZERO_WIDTH, value=ZERO_WIDTH, inline=False)  # New line
        embed.add_field(name="TIMER", value=status, inline=False)
        return embed

    async def _finish(self) -> None:
        self.clear_items()
        self.stop()

        embed = self.base_embed.copy()
        embed.add_field(name=ZERO_WIDTH, value="``` ```", inline=False)

        if not self.scores:
            embed.add_field(name="Nobody answered a question - no winner this time!", value=ZERO_WIDTH, inline=False)
        else:
            best = max(self.scores.values())
            winners = [self.players[uid].display_name for uid, score in self.scores.items() if score == best]
            points = f"{best} point{'' if best == 1 else 's'}"
            if len(winners) == 1:
                headline = f"🎉 The winner is {winners[0]} with {points}! 🎉"
            else:
                headline = f"🎉 It's a tie between {', '.join(winners)} with {points} each! 🎉"
            embed.add_field(name=headline[:256], value=ZERO_WIDTH, inline=False)
            embed.add_field(name=ZERO_WIDTH, value="Want to see how you did?", inline=False)

            ranked = sorted(self.scores.items(), key=lambda item: item[1], reverse=True)
            board = "\n".join(f"{self.players[uid].display_name} : {score}" for uid, score in ranked[:20])
            embed.add_field(name="*Leaderboard:*", value=board, inline=False)

        await self._edit(embed)
