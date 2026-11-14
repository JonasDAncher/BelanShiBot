"""The /quiz command (registered on the test guild only)."""
import discord
from discord import app_commands
from discord.ext import commands

from config import QUIZ_ANSWER_TIME, QUIZ_POINTS_PER_ANSWER, TEST_GUILD_ID
from content import QUIZ_QUESTIONS
from views.quiz import QuizView


class Quiz(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="quiz", description="Starts a round of quiz!")
    @app_commands.guilds(discord.Object(id=TEST_GUILD_ID))
    @app_commands.guild_only()
    async def quiz(self, interaction: discord.Interaction) -> None:
        name = interaction.user.display_name
        embed = discord.Embed(
            title=f"{name} has started a quiz!",
            description=(
                "Everyone can join in, you just have to press the buttons on each question.\n\n"
                f"You'll have __{QUIZ_ANSWER_TIME}__ second(s) to answer each question. "
                "If you change your mind, just press a new answer!\n\n"
                f"Each correct answer gives {QUIZ_POINTS_PER_ANSWER} point(s)! "
                "If you have the most by the end, you're the winner!"
            ),
        )
        await interaction.response.send_message(
            content=f"A quiz has started! Your Quizmaster is... __{name}__",
            embed=embed,
            view=QuizView(interaction.user, QUIZ_QUESTIONS, embed),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Quiz(bot))
