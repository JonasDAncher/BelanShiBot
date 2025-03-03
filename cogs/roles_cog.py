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

class rolesCog(commands.Cog):
  class AssignRoles(ui.View):
    def __init__(self, interaction):
      super().__init__(timeout=None)
      self.interaction = interaction
      self.assign_roles()


    def assign_roles(self):
      # ---------- Helper function ----------
      async def add_remove_role(interaction: discord.Interaction, role):
        try:
          if role in interaction.user.roles: # If user has role, remove role
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(content=f"You've **__disabled__** pings for the {role} role\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
            log(f'User {interaction.user.name} in server {interaction.guild.name} disabled pings for {role}')
            return
          else: # If user is missing role, add it
            await interaction.user.add_roles(role)
            await interaction.response.send_message(content=f"You've **__enabled__** pings for the {role} role\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
            log(f'User {interaction.user.name} in server {interaction.guild.name} enabled pings for {role}')
            return
        except:
          await interaction.response.send_message(ephemeral=True,
                                                  delete_after=60,
                                                  content=f"""
  ***Error***: I cannot manipulate the `{role}` role. Likely because it's above the `Belan Shi Bot` role.\n
  All three of the `Tank`, `Healer`, & `DPS` roles should be lower in the hierachy than the `Belan Shi Bot` role.\n
  If you are __not__ a server admin, you should inform one of the issue.\n
  -# *This message disappears in 2 minutes*""")
          log(f'Cannot manipulate the role {role} in server {interaction.guild.name}. Error message has informed caller.')

      # ---------- Tank Role Assign ----------
      tank_role_button = ui.Button(label="TANK", emoji='🛡', custom_id='tank_role_button')
      async def tankrolebutton(interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name = "Tank")
        await add_remove_role(interaction, role)
      tank_role_button.callback = tankrolebutton
      # ---------- Healer Role Assign ----------
      healer_role_button = ui.Button(label="HEALER", emoji='💚', custom_id='healer_role_button')
      async def healerrolebutton(interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name = "Healer")
        await add_remove_role(interaction, role)
      healer_role_button.callback = healerrolebutton
      # ---------- DPS Role Assign ----------
      dps_role_button = ui.Button(label="DPS", emoji='⚔️', custom_id='dps_role_button')
      async def dpsrolebutton(interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name = "DPS")
        await add_remove_role(interaction, role)
      dps_role_button.callback = dpsrolebutton

      # Assign buttons to view
      self.add_item(tank_role_button)
      self.add_item(healer_role_button)
      self.add_item(dps_role_button)

  # @tree.command(guild=discord.Object(id=TEST_ID)) # Adds command to test server
  @commands.command()                                 # Adds command globally
  async def roles(interaction: discord.Interaction):
    """Creates a message with buttons to self-assign roles"""
    content_var = """**You can self-assign roles using the buttons below, enabling their pings**
  Click the buttons corrosponding to the role, you wish to receive pings for, when a `/key` run is started!
  Press any role you __already__ have, to disable pings again.\n
  -# *This message disappears in 2 minutes*"""
    bsb_role = discord.utils.get(interaction.guild.roles, name = "Belan Shi Bot")  
    roles = [discord.utils.get(interaction.guild.roles, name = "Tank"),
            discord.utils.get(interaction.guild.roles, name = "Healer"),
            discord.utils.get(interaction.guild.roles, name = "DPS"),
            bsb_role]
    if max(roles) == bsb_role:
      await interaction.response.send_message(content=content_var, 
                                              view=AssignRoles(interaction), 
                                              ephemeral=True, 
                                              delete_after=120)
      log(f'User {interaction.user.name} in server {interaction.guild.name} called the /roles command')
    else:
      await interaction.response.send_message(content=f"""
  ***Error***: All three of the `Tank`, `Healer`, & `DPS` roles should be lower in the hierachy than the `Belan Shi Bot` role.\n
  If you are __not__ a server admin, you should inform one of the issue.\n
  -# *This message disappears in 2 minutes*""")
      logging.error(f'User {interaction.user.name} in server {interaction.guild.name} called the /roles command resulting in an error due to incorrecet role hierachy')

  def log(log_message):
    logging.info(f'{log_message}')
    # time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # print(f'{time} - {log_message}')
