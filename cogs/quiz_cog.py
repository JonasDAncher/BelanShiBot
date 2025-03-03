import datetime
import random
from typing import Final, Optional
import os
import logging
import asyncio

import discord
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, ui, Interaction, Embed
from discord.ext import tasks, commands

# TEST_ID: Final[int] = 368116240276914176  # Belan Shi Discord ID
TEST_ID: Final[int] = 489890364090744892  # Test Server Discord ID
DELETE_TIME: Final[int] = 10  # How long after sending an ephemeral message is deleted automatically.

class quizCog(commands.Cog):
  # ---------- Quiz Command ----------
  class Quiz(ui.View):
    def __init__(self, interaction: discord.Interaction, quizmaster):
      super().__init__(timeout=None)
      self.quiz()
      self.quizmaster = quizmaster

    def quiz(self):
      """The main quiz method."""
      participant = dict()
      a = []; b = []; c = []; d = []

      async def start_quizzing(interaction: discord.Interaction):
          # --------- Questions & Answers ---------
          questions = [
              "What langauge is this bot written in?",
              "What is the guild called?",
              "This is a test question, the correct answer is wow",
              "Who sucks?"
          ]
          # The options for each question. Using array index to access
          options = [
              ["Java", "Python", "C#", "C++"],
              ["Belan Shi", "Echo", "Liquid", "Method"],
              ["4","movies", "potatoe", "WoW"],
              ["1", "Gala's great", "Maya sucks", "2"]
          ]
          # In the form question_number : correct_option
          # Used to access the correct options index, based on question_number
          answers = {
              0: 1,
              1: 0,
              2: 3,
              3: 2
          }

          # --------- Manipulating the embed ---------
          
          # The int tracking which question the quiz is on.
          self.question_number = 0
          self.timer_time = 5
          self.pause_time = 5
          embed_var = interaction.message.embeds[0]
          embed_var.add_field(name="",value="``` ```") # Spacer
          embed_var.add_field(name=f"Question # **{self.question_number+1} / {len(questions)}**",
                              value=f"**{questions[self.question_number]}**", inline=False)
          embed_var.add_field(name="1", value=f"> *{options[self.question_number][0]}*", inline=True)
          embed_var.add_field(name="2", value=f"> *{options[self.question_number][1]}*", inline=True)
          embed_var.add_field(name="",value="",inline=False) # New line
          embed_var.add_field(name="3", value=f"> *{options[self.question_number][2]}*", inline=True)
          embed_var.add_field(name="4", value=f"> *{options[self.question_number][3]}*", inline=True)
          embed_var.add_field(name="TIMER", value=f"{self.timer_time} seconds left to answer!", inline=False)
          await interaction.message.edit(embed=embed_var)


          @tasks.loop(count=self.pause_time+1)
          async def pause_timer(self):
              """Pauses the quiz on revealed answers."""
              embed_dict = interaction.message.embeds[0].to_dict()
              for field in embed_dict["fields"]:
                  if field["name"] == "TIMER": field["value"] = f"Next question in {self.pause_time} seconds..."
              await interaction.message.edit(embed=Embed.from_dict(embed_dict))
              self.pause_time -= 1
              await asyncio.sleep(1)

          @pause_timer.after_loop
          async def progress():
              """Simply progresses the quiz to the next question, once the pause timer has ended."""
              await next_question(self)
          
          @tasks.loop(count=self.timer_time+1)
          async def timer(self):
              """Timer showing how long there's left to answer question."""
              embed_dict = interaction.message.embeds[0].to_dict()
              for field in embed_dict["fields"]:
                  if field["name"] == "TIMER": field["value"] = f"{self.timer_time} seconds left to answer!"
              await interaction.message.edit(embed=Embed.from_dict(embed_dict))
              self.timer_time -= 1
              await asyncio.sleep(1)  # Sleep for better flow

          @timer.after_loop
          async def times_up():
              """Disables buttons, and awards points based on correct answers."""
              await asyncio.sleep(1)  # Sleep for better flow
              for button in self.children:
                  if type(button) == ui.Button: button.disabled=True
              await interaction.message.edit(view=self)
              award_points()
              # Determines if the quiz should move to next question, or terminate; revealing the winner.
              self.question_number += 1
              if self.question_number <= len(questions)-1:
                  print("revealing answer...")
                  await reveal_answer(self)
              else:
                  print("ending quiz...")
              await finish_quiz()

          async def reveal_answer(self):
              """Reveals the answer by striking-out the wrong ones, and bolding the correct"""
              embed_dict = interaction.message.embeds[0].to_dict()
              for field in embed_dict["fields"]: # No switch, so long if-elif
                  if answers[self.question_number-1]==0:
                      if field["name"] == "1": field["value"] = f"> **>> {options[self.question_number-1][0]} <<**"
                      if field["name"] == "2": field["value"] = f"> ~~*{options[self.question_number-1][1]}*~~"
                      if field["name"] == "3": field["value"] = f"> ~~*{options[self.question_number-1][2]}*~~"
                      if field["name"] == "4": field["value"] = f"> ~~*{options[self.question_number-1][3]}*~~"
                  elif answers[self.question_number-1]==1:
                      if field["name"] == "1": field["value"] = f"> ~~*{options[self.question_number-1][0]}*~~"
                      if field["name"] == "2": field["value"] = f"> **>> {options[self.question_number-1][1]} <<**"
                      if field["name"] == "3": field["value"] = f"> ~~*{options[self.question_number-1][2]}*~~"
                      if field["name"] == "4": field["value"] = f"> ~~*{options[self.question_number-1][3]}*~~"
                  elif answers[self.question_number-1]==2:
                      if field["name"] == "1": field["value"] = f"> ~~*{options[self.question_number-1][0]}*~~"
                      if field["name"] == "2": field["value"] = f"> ~~*{options[self.question_number-1][1]}*~~"
                      if field["name"] == "3": field["value"] = f"> **>> {options[self.question_number-1][2]} <<**"
                      if field["name"] == "4": field["value"] = f"> ~~*{options[self.question_number-1][3]}*~~"
                  elif answers[self.question_number-1]==3:
                      if field["name"] == "1": field["value"] = f"> ~~*{options[self.question_number-1][0]}*~~"
                      if field["name"] == "2": field["value"] = f"> ~~*{options[self.question_number-1][1]}*~~ "
                      if field["name"] == "3": field["value"] = f"> ~~*{options[self.question_number-1][2]}*~~"
                      if field["name"] == "4": field["value"] = f"> **>> {options[self.question_number-1][3]} <<**"
              await interaction.message.edit(embed=Embed.from_dict(embed_dict))
              try: # Have to check if timer has already been used. If it has, just restart it
                  await pause_timer.start(self)
              except:
                  pause_timer.restart(self)
                  

          async def finish_quiz():
              """Terminates the quiz, clean the embed, and show winner & leaderboard."""
              self.remove_item(a_button); self.remove_item(b_button); self.remove_item(c_button); self.remove_item(d_button); # Remove all buttons
              if len(participant) > 0: # If there's any players, get the player with the highest score
                  winner = max(participant, key=participant.get)
                  points = participant[winner]
              else:
                  winner = interaction.user
                  points = 0
              # Destroying all fields, cuz it's easier...
              embed_dict = interaction.message.embeds[0].to_dict()
              embed_dict["fields"] = []
              embed_var=Embed.from_dict(embed_dict)

              # Rebuilding the embed cuz removing specific fields is a pain
              embed_var.add_field(name="",value="``` ```", inline=False) # Spacer
              embed_var.add_field(name=f"🎉 The winner is {winner.nick if not winner.nick==None else winner.name} with {points} point{'' if points==1 else 's'}! 🎉", value="", inline=False)

              embed_var.add_field(name="",value="Want to see how you did?", inline=False) 

              # Build leaderboard
              result = ""
              for key, value in sorted(participant.items(), key=lambda x: x[1]): 
                  result = result + "{} : {}\n".format(key.nick if not key.nick==None else key.name, value)
              embed_var.add_field(name="*Leaderboard:*", value=f"{result}")
              await interaction.message.edit(view=self, embed=Embed.from_dict(embed_dict))
              return

          def award_points(): # Can't use match case in discord.py
              """Awards points to the users who answered correctly, then clears answer arrays."""
              correct_answer = answers[self.question_number]
              if correct_answer == 0:
                  for player in a:
                      participant[player] = participant[player]+1
              if correct_answer == 1:
                  for player in b:
                      participant[player] = participant[player]+1
              if correct_answer == 2:
                  for player in c:
                      participant[player] = participant[player]+1
              if correct_answer == 3:
                  for player in d:
                      participant[player] = participant[player]+1
              a.clear();b.clear();c.clear();d.clear()

          async def next_question(self):
              """Changes the question and options to a new question, re-enables the buttons, and begins the timer."""
              embed_dict = interaction.message.embeds[0].to_dict()
              for field in embed_dict["fields"]:
                  if field["name"] == f"Question # **{self.question_number} / {len(questions)}**": 
                      field["name"] = f"Question # **{self.question_number+1} / {len(questions)}**"
                      field["value"] = f"**{questions[self.question_number]}**"
                  if field["name"] == "1": field["value"] = f"> *{options[self.question_number][0]}*"
                  if field["name"] == "2": field["value"] = f"> *{options[self.question_number][1]}*"
                  if field["name"] == "3": field["value"] = f"> *{options[self.question_number][2]}*"
                  if field["name"] == "4": field["value"] = f"> *{options[self.question_number][3]}*"
              await interaction.message.edit(view=self)
              await asyncio.sleep(1) # Sleep for better flow
              for button in self.children:
                  if type(button) == ui.Button: button.disabled=False
              await interaction.message.edit(view=self)
              # Reset the timers
              self.timer_time = 5
              self.pause_time = 5

              await asyncio.sleep(1) # Sleep for better flow
              try: # Have to check if timer has been run before, if it has just restart.
                  await timer.start(self)
              except:
                  timer.restart(self)

          await asyncio.sleep(1) # Sleep for better flow
          await interaction.message.edit(embed=embed_var)
          await timer.start(self)

      # --------- Answer Buttons ---------
      a_button = ui.Button(label="",emoji='1️⃣', custom_id='answer_a_button')
      async def answera(interaction: discord.Interaction):
          if interaction.user not in participant: participant[interaction.user] = 0 # If participant is new, add to participants with zero points
          answer(interaction.user,0)
          await interaction.response.send_message(content=f"You answered 1️⃣", ephemeral=True, delete_after=3)

      b_button = ui.Button(label="",emoji='2️⃣', custom_id='answer_b_button')
      async def answerb(interaction: discord.Interaction):
          if interaction.user not in participant: participant[interaction.user] = 0 # If participant is new, add to participants with zero points
          answer(interaction.user,1)
          await interaction.response.send_message(content=f"You answered 2️⃣", ephemeral=True, delete_after=3)
      
      c_button = ui.Button(label="",emoji='3️⃣', custom_id='answer_c_button')
      async def answerc(interaction: discord.Interaction):
          if interaction.user not in participant: participant[interaction.user] = 0 # If participant is new, add to participants with zero points
          answer(interaction.user,2)
          await interaction.response.send_message(content=f"You answered 3️⃣", ephemeral=True, delete_after=3)

      d_button = ui.Button(label="",emoji='4️⃣', custom_id='answer_d_button')
      async def answerd(interaction: discord.Interaction):
          if interaction.user not in participant: participant[interaction.user] = 0 # If participant is new, add to participants with zero points
          answer(interaction.user,3)
          await interaction.response.send_message(content=f"You answered 4️⃣", ephemeral=True, delete_after=3)

      start_button = ui.Button(label="Start?", emoji='🏁', custom_id='start_button')
      async def start(interaction: discord.Interaction):
          if not interaction.user == self.quizmaster:
              username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
              await interaction.response.send_message(content=f"You're not the Quizmaster, {username}...", ephemeral=True, delete_after=DELETE_TIME)
          else:
              self.remove_item(start_button)
              self.add_item(a_button)
              self.add_item(b_button)
              self.add_item(c_button)
              self.add_item(d_button)
              await interaction.response.send_message(content=f"You've started the quiz.\n-# *This message disappears in {5} seconds*", ephemeral=True, delete_after=5)
              await interaction.message.edit(view=self)
              await start_quizzing(interaction)
  
      start_button.callback = start
      a_button.callback = answera
      b_button.callback = answerb
      c_button.callback = answerc
      d_button.callback = answerd
      self.add_item(start_button)

      # --------- Helpers ---------
      def answer(user, guess):
          if guess == 0:
              if user in b: b.remove(user)
              if user in c: c.remove(user)
              if user in d: d.remove(user)
              a.append(user)
          elif guess == 1:
              if user in a: a.remove(user)
              if user in c: c.remove(user)
              if user in d: d.remove(user)
              b.append(user)
          elif guess == 2:
              if user in a: a.remove(user)
              if user in b: b.remove(user)
              if user in d: d.remove(user)
              c.append(user)
          elif guess == 3:
              if user in a: a.remove(user)
              if user in b: b.remove(user)
              if user in c: c.remove(user)
              d.append(user)

    @commands.command(guild=discord.Object(id=TEST_ID)) # Adds command to test server
    # @commands.command()                                 # Adds command globally
    async def quiz(interaction: discord.Interaction):
      """Starts a round of quiz!"""
      quizmaster_name = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
      answer_time = 5
      reward = 1
      content_var = f"""A quiz has started! Your Quizmaster is... __{quizmaster_name}__"""
      embed_var = discord.Embed(
          title=f"""{quizmaster_name} has started a quiz!""",
          description=f"""
      Everyone can join in, you just have to press the buttons on each question.\n
      You'll have __{answer_time}__ second(s) to answer each question. If you change your mind, just press a new answer!\n
      Each correct answer gives {reward} point(s)! If you have the most by the end, you're the winner!
      """
      )

      view_var = Quiz(interaction, interaction.user)

      await interaction.response.send_message(
          content=content_var,
          embed=embed_var,
          view=view_var
      )

  def log(log_message):
    logging.info(f'{log_message}')
    # time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # print(f'{time} - {log_message}')
