import datetime
import random
from typing import Final, Optional
import os
import logging
import asyncio

import discord
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, ui, Interaction, Embed
from discord.ext import tasks

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')  # Discord bot token, SECRET
# TEST_ID: Final[int] = 368116240276914176  # Belan Shi Discord ID
TEST_ID: Final[int] = 489890364090744892  # Test Server Discord ID
DELETE_TIME: Final[int] = 10  # How long after sending an ephemeral message is deleted automatically.

intents = Intents.default()
intents.message_content = True  # Allow the bot to see message content
intents.members = True  # Allow the bot to see message content
intents.guilds = True # Allow the bot to create necessary roles
client = Client(intents=intents, allowed_mentions = discord.AllowedMentions(roles=True, users=True))
tree = app_commands.CommandTree(client)


class RoleButtons(ui.View):
  def __init__(self, user, players):
    super().__init__(timeout=None)
    self.user = user
    self.players = players
    self.add_buttons()

  def add_buttons(self):
    """Creates the clickable role, confirm and cancel buttons."""

    # ---------- Tank button ----------
    tank_button = ui.Button(label="TANK", emoji='🛡', disabled=len(self.players[0]) > 0, custom_id='tank_button')  # Creates the button object

    async def tankbutton(interaction: discord.Interaction):
      """Creates the functionality of the tank button"""

      if len(self.players[0]) > 0:
        if not interaction.user == self.players[0][0]: # If tank spot is already taken
          await interaction.response.send_message(f"Tank spot taken, sorry.\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
          return
        if interaction.user == self.players[0][0]: # If user is the signed tank
          self.players[0].remove(interaction.user)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "TANK":
              field["value"] = f"🛡 Tank open"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))
          await interaction.response.send_message(f"You've removed yourself as tank!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True,
                                                  delete_after=DELETE_TIME)
          username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
          log(f'KEY: {self.id} - {username} un-joined as TANK')
          return

      if len(self.players[1]) > 0 and interaction.user in self.players[1]: # If user is already signed up as healer
        self.players[1].remove(interaction.user)
        self.players[0].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "HEALER": field["value"] = f"💚 Healer open"
          if field["name"] == "TANK": field["value"] = f"❌ {self.players[0][0].nick if not self.players[0][0].nick==None else self.players[0][0].name}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message(f"You swapped role to tank!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} swapped from HEALER to TANK')
        return

      if len(self.players[2]) > 0 and interaction.user in self.players[2]: # If the user is already signed up as dps
        self.players[2].remove(interaction.user)
        self.players[0].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
          if field["name"] == "TANK": field["value"] = f"❌ {self.players[0][0].nick if not self.players[0][0].nick==None else self.players[0][0].name}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message(f"You've swapped role to tank!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} swapped from DPS to TANK')
        return

      # If the tank spot is open
      username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
      log(f'KEY: {self.id} - {username} joined as TANK')
      self.players[0].append(interaction.user)
      embed_dict = interaction.message.embeds[0].to_dict()
      for field in embed_dict["fields"]:
        if field["name"] == "TANK":
          field["value"] = f"❌ {self.players[0][0].nick if not self.players[0][0].nick==None else self.players[0][0].name}"
      await interaction.message.edit(embed=Embed.from_dict(embed_dict))
      await interaction.response.send_message(f"You've marked you want to join as tank!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
      await reminder(interaction, self.players)

    tank_button.callback = tankbutton  # Add functionality to the button object.
    self.add_item(tank_button)  # Add the button to the view.

    # ---------- Healer button ----------
    healer_button = ui.Button(label="HEALER", emoji='💚', disabled=len(self.players[1]) > 0, custom_id='healer_button')  # Creates the button object

    async def healerbutton(interaction: discord.Interaction):
      """Creates the functionality of the healer button"""

      if len(self.players[1]) > 0:
        if not interaction.user == self.players[1][0]: # If healer spot is already taken
          await interaction.response.send_message(f"Healer spot taken, sorry.\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
          return
        if interaction.user == self.players[1][0]: # If the user is the signed healer
          self.players[1].remove(interaction.user)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "HEALER":
              field["value"] = f"💚 Healer open"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))
          await interaction.response.send_message(f"You've removed yourself as healer!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True,
                                                  delete_after=DELETE_TIME)
          username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
          log(f'KEY: {self.id} - {username} un-joined as HEALER')
          return

      if len(self.players[0]) > 0 and interaction.user in self.players[0]:  # If user is already signed up as tank
        self.players[0].remove(interaction.user)
        self.players[1].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "TANK": field["value"] = f"🛡 Tank open"
          if field["name"] == "HEALER": field["value"] = f"❌ {self.players[1][0].nick if not self.players[1][0].nick==None else self.players[1][0].name}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message(f"You swapped role to healer!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} swapped from TANK to HEALER')
        return

      if len(self.players[2]) > 0 and interaction.user in self.players[2]:  # If the user is already signed up as dps
        self.players[2].remove(interaction.user)
        self.players[1].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
          if field["name"] == "HEALER": field["value"] = f"❌ {self.players[1][0].nick if not self.players[1][0].nick==None else self.players[1][0].name}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message(f"You've swapped role to healer!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} swapped from DPS to HEALER')
        return

      # If the healer spot is open
      username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
      log(f'KEY: {self.id} - {username} joined as HEALER')
      self.players[1].append(interaction.user)
      embed_dict = interaction.message.embeds[0].to_dict()
      for field in embed_dict["fields"]:
        if field["name"] == "HEALER":
          field["value"] = f"❌ {self.players[1][0].nick if not self.players[1][0].nick==None else self.players[1][0].name}"
      await interaction.message.edit(embed=Embed.from_dict(embed_dict))
      await interaction.response.send_message(f"You've marked you want to join as healer!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
      await reminder(interaction, self.players)

    healer_button.callback = healerbutton  # Add functionality to the button object.
    self.add_item(healer_button)  # Add the button to the view.

    # ---------- DPS button ----------
    dps_button = ui.Button(label="DPS", emoji='⚔️', disabled=len(self.players[2]) == 3, custom_id='dps_button')  # Creates the button object

    async def dpsbutton(interaction: discord.Interaction):
      """Creates the functionality of the DPS button"""

      if len(self.players[2]) == 3 and not interaction.user in self.players[2]: # If dps spots are already taken
        await interaction.response.send_message(f"DPS spots taken, sorry.\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        return

      if len(self.players[2]) > 0 and interaction.user in self.players[2]: # If the user is signed as dps
        self.players[2].remove(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS":
            field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message(f"You've removed yourself as DPS!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True,
                                                delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} un-joined as DPS')
        return

      if len(self.players[0]) > 0 and interaction.user in self.players[0]:  # If user is already signed up as tank
        self.players[0].remove(interaction.user)
        self.players[2].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "TANK": field["value"] = f"🛡 Tank open"
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message(f"You swapped role to DPS!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} swapped from TANK to DPS')
        return

      if len(self.players[1]) > 0 and interaction.user in self.players[1]:  # If the user is already signed up as healer
        self.players[1].remove(interaction.user)
        self.players[2].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "HEALER": field["value"] = f"💚 Healer open"
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message(f"You've swapped role to DPS!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} swapped from HEALER to DPS')
        return

      # If a dps spot is open
      self.players[2].append(interaction.user)
      embed_dict = interaction.message.embeds[0].to_dict()
      for field in embed_dict["fields"]:
        if field["name"] == "DPS":
          field["value"] = format_dps(self.players[2])
      await interaction.message.edit(embed=Embed.from_dict(embed_dict))
      await interaction.response.send_message(f"You've marked you want to join as DPS!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True,
                                              delete_after=DELETE_TIME)
      await reminder(interaction, self.players)
      username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
      log(f'KEY: {self.id} - {username} joined as DPS')

    dps_button.callback = dpsbutton  # Add functionality to the button object.
    self.add_item(dps_button)  # Add the button to the view.

    # ---------- Cancel button ----------
    cancel_button = ui.Button(label="CANCEL", emoji='❌', custom_id='cancel_button')  # Creates the button object

    async def cancelbutton(interaction: discord.Interaction):
      """Creates the functionality of the cancel button"""

      if interaction.user == self.user:
        await interaction.message.delete()
        await interaction.response.send_message(content=f"Run cancelled!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        interaction.channel.send("The run was cancelled.")
        log(f'KEY: {self.id} - {username} cancelled the key.')
        # TODO Should also delete any run confirmed messages.
        return
      else:
        await interaction.response.send_message(content=f"You cannot cancel a run you did not start!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True,
                                                delete_after=DELETE_TIME)
      return

    cancel_button.callback = cancelbutton  # Add functionality to the button object.
    self.add_item(cancel_button)  # Add the button to the view.

    # ---------- Confirm button ----------
    confirm_button = ui.Button(label="LOCK RUN", emoji='✅', custom_id='confirm_button')  # Creates the button object

    async def confirmbutton(interaction: discord.Interaction):
      """Creates the functionality of the confirm button"""

      if interaction.user == self.user:
        for child in self.children:
          if type(child) == ui.Button and not (child.label == "LOCK RUN" or child.label == "CANCEL"):
            child.disabled = True
        # await interaction.response.send_message(content="Run confirmed!\nRole buttons deactivated", ephemeral=True,
        #                                         delete_after=DELETE_TIME)
        # ^^^^^^ disabled: using vvvvvv instead.
        # Sends a group composition message on run confirmed. However, need a good solution for 'unconfirming' a
        # confirmed run, as this message should then be deleted. TODO Delete old message, if run is un-confirmed

        tank = '*Open*'
        healer = '*Open*'
        dps1 = '*Open*'
        dps2 = '*Open*'
        dps3 = '*Open*'

        if len(self.players[0]) > 0: tank = self.players[0][0].mention if not type(self.players[0][0]) == str else '*Reserved*'
        if len(self.players[1]) > 0: healer = self.players[1][0].mention if not type(self.players[1][0]) == str else '*Reserved*'
        if len(self.players[2]) > 0: dps1 = self.players[2][0].mention if not type(self.players[2][0]) == str else '*Reserved*'
        if len(self.players[2]) > 1: dps2 = self.players[2][1].mention if not type(self.players[2][1]) == str else '*Reserved*'
        if len(self.players[2]) > 2: dps3 = self.players[2][2].mention if not type(self.players[2][2]) == str else '*Reserved*'

        await interaction.response.send_message(content=f"Run locked!"
                                                 f"\n🛡: {tank}"
                                                 f"\n💚: {healer}"
                                                 f"\n⚔️ # 1: {dps1}"
                                                 f"\n⚔️ # 2: {dps2}"
                                                 f"\n⚔️ # 3: {dps3}",
                                                 delete_after=14000)
        self.remove_item(confirm_button)
        self.add_item(unconfirm_button)
        await interaction.message.edit(view=self)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        
        log(f'KEY: {self.id} - {username} locked the key.')
        return
      else:
        await interaction.response.send_message(content=f"You cannot lock a run you did not start!\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True,
                                                delete_after=DELETE_TIME)
      return

    confirm_button.callback = confirmbutton  # Add functionality to the button object.
    self.add_item(confirm_button)  # Add the button to the view.

    # ---------- Unconfirm button ----------
    unconfirm_button = ui.Button(label="UN-LOCK", emoji='↩️', custom_id='unconfirm_button')  # Creates the button object

    async def unconfirmbutton(interaction: discord.Interaction):
      """Creates the functionality of the unconfirm button"""
      if interaction.user == self.user:
        for child in self.children:
          if type(child) == ui.Button and not (child.label == "CONFIRM" or child.label == "CANCEL" or child.label == "UN-CONFIRM"):
            if child.label == "TANK" and not "*Reserved*" in self.players[0]: child.disabled = False
            if child.label == "HEALER" and not "*Reserved*" in self.players[1]: child.disabled = False
            if child.label == "DPS" and (len(self.players[2]) - self.players[2].count("*Reserved*")) < 3: child.disabled = False
        await interaction.response.send_message(content=f"Run un-locked!\nRole buttons activated.\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True,
                                                delete_after=DELETE_TIME)
        username = interaction.user.nick if not interaction.user.nick==None else interaction.user.name
        log(f'KEY: {self.id} - {username} un-locked the key.')
        self.remove_item(unconfirm_button)
        self.add_item(confirm_button)
        await interaction.message.edit(view=self)
        return
      else:
        await interaction.response.send_message(content=f"You cannot un-lock a run you did not start!\n-# *This message disappears in {DELETE_TIME} seconds*",
                                                ephemeral=True, delete_after=DELETE_TIME)
      return

    unconfirm_button.callback = unconfirmbutton  # Add functionality to the button object.
    # self.add_item(unconfirm_button) # Notably not added to the view, as that is part of the confirm button functionality

# --------- Key Command ---------
# @tree.command(guild=discord.Object(id=TEST_ID)) # Adds command to test server
@tree.command()                                 # Adds command globally
@app_commands.rename(dungeon_name='dungeon-name', key_level='key-level', tank='tank', healer='healer',
                     dps='missing-dps')
async def key(
    interaction: discord.Interaction,
    dungeon_name: str,
    key_level: int,
    tank: Optional[int] = 1,
    healer: Optional[int] = 1,
    dps: Optional[int] = 3,
    time: Optional[str] = None):
  """Creates a group people can join using ui buttons
  :param dungeon_name: Name of the dungeon
  :param key_level: Level of the key - >99 means any key level
  :param tank: Missing tank?
  :param healer: Missing healer?
  :param dps: How many dps needed?
  :param time: At a specific time?
  """
  await check_roles(interaction) # Check if the roles exists, and create them if they don't.
  
  if interaction.guild_id == 570190869609709569 and interaction.channel.id != 1342184148156284938: # Quack's guild server
    await interaction.response.send_message(content=f"Wrong channel\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
    return

  if interaction.guild_id == 489890364090744892 and interaction.channel.id != 786705743336046593: # Test server
    await interaction.response.send_message(content=f"Wrong channel, Gala...\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
    return
  if interaction.guild_id == 368116240276914176 and interaction.channel.id != 374937731744268289: # Belan Shi
    await interaction.response.send_message(content=f"Wrong channel, Maya...\n-# *This message disappears in {DELETE_TIME} seconds*", ephemeral=True, delete_after=DELETE_TIME)
    return

  log(f"NEW KEY on server {interaction.guild.name}: {interaction.user.name} created a new key with parameters:\n"
    f"                                dungeon_name={dungeon_name}, key_level={key_level}, tank={tank}, healer={healer}, dps={dps}") # Primitive logging

  if dps <= -1:  # Disallow negative number of DPS players
    await interaction.response.send_message(content=f"Illegal argument: `dps` must be a non-negative integer\n-# *This message disappears in {DELETE_TIME} seconds*",
                                            ephemeral=True)
    return
  else:
    # Using 2d array to store players and reserved places. Accessing is currently hardcoded array indices. TODO Improve?
    tank_player = ["*Reserved*"] * (1 - tank)
    heal_player = ["*Reserved*"] * (1 - healer)
    dps_players = ["*Reserved*"] * (3 - dps)
    players = [tank_player, heal_player, dps_players]

    content_var, embed_var = await format_message(interaction, dungeon_name, key_level, tank, healer, dps, time,
                                                  dps_players)
    await interaction.response.send_message(content=content_var, embed=embed_var,
                                            view=RoleButtons(interaction.user, players))

# ---------- Helper functions for the key command ----------
async def reminder(interaction: discord.Interaction, players: list):
  if isGroupFull(players):
    waitTime = 600
    if (datetime.datetime.now(datetime.timezone.utc).timestamp()-interaction.message.created_at.timestamp()) > waitTime:
      message = f"""The key group you made in {interaction.guild.name} has been filled!\n# [Click here to see it!]({interaction.message.jump_url}) \n-# This reminder is sent to you, because you made the group more than {waitTime/60} minutes ago."""
      await interaction.message.mentions[0].send(message)
  return

def isGroupFull(players: list):
  if len(players[0]) > 0 and len(players[1]) > 0 and len(players[2]) > 2: return True 
  return False

def format_dps(dps_players=None):
  """Formats the 3 lines of DPS text for the embed
  :return formatted string containing reserved/open/player names based on signup and creation details.
  """
  if dps_players is None:
    dps_players = []
  if len(dps_players) == 3:
    dps1 = dps_players[0] if isinstance(dps_players[0],str) else dps_players[0].nick if not dps_players[0].nick==None else dps_players[0].name
    dps2 = dps_players[1] if isinstance(dps_players[1],str) else dps_players[1].nick if not dps_players[1].nick==None else dps_players[1].name
    dps3 = dps_players[2] if isinstance(dps_players[2],str) else dps_players[2].nick if not dps_players[2].nick==None else dps_players[2].name
    return f"❌ # 1: {dps1}\n❌ # 2: {dps2}\n❌ # 3: {dps3}\n"
  elif len(dps_players) == 2:
    dps1 = dps_players[0] if isinstance(dps_players[0],str) else dps_players[0].nick if not dps_players[0].nick==None else dps_players[0].name
    dps2 = dps_players[1] if isinstance(dps_players[1],str) else dps_players[1].nick if not dps_players[1].nick==None else dps_players[1].name
    return f"❌ # 1: {dps1}\n❌ # 2: {dps2}\n⚔️ # 3: *Open*\n"
  elif len(dps_players) == 1:
    dps1 = dps_players[0] if isinstance(dps_players[0],str) else dps_players[0].nick if not dps_players[0].nick==None else dps_players[0].name
    return f"❌ # 1: {dps1}\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  elif len(dps_players) == 0:
    return f"⚔️ # 1: *Open*\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  return None

def random_desc():
  descs = [
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
    "It's going to be a *special* run"
  ]
  return random.choice(descs)

async def check_roles(interaction):
  log(f'Checking if roles must be added to server: {interaction.guild.name}')
  if discord.utils.get(interaction.guild.roles, name = 'Tank') == None: 
    log(f'  Creating missing role Tank on server {interaction.guild.name}')
    await interaction.guild.create_role(name='Tank')
  if discord.utils.get(interaction.guild.roles, name = 'Healer') == None: 
    log(f'  Creating missing role Healer on server {interaction.guild.name}')
    await interaction.guild.create_role(name='Healer')
  if discord.utils.get(interaction.guild.roles, name = 'DPS') == None: 
    log(f'  Creating missing role DPS on server {interaction.guild.name}')
    await interaction.guild.create_role(name='DPS')

async def format_message(interaction, dungeon_name, key_level, tank, healer, dps, time, dps_players, tank_player=None,
                         healer_player=None):
  """Formats the embed and the content of the message
  :return two variables: the content_var (message content) & embed_var (content of the embed)
  """
  embed_var = discord.Embed(
    title=f"{interaction.user.nick if not interaction.user.nick==None else interaction.user.name} want to run a {dungeon_name} +{key_level if key_level<99 else '*any*'}{' at ' + time if not time is None else ''}!",
    description=random_desc(), color=0x00ff00 if 0 <= key_level < 5 else 0xffff00 if 5 <= key_level <= 7 else 0xff0000)
  embed_var.add_field(name="TANK",
                      value=f"{'❌ *Reserved*' if tank == 0 else {tank_player.nick} if not tank_player is None else '🛡 Tank open'}",
                      inline=False)
  embed_var.add_field(name="HEALER",
                      value=f"{'❌ *Reserved*' if healer == 0 else {healer_player.nick} if not healer_player is None else '💚 Healer open'}",
                      inline=False)
  embed_var.add_field(name="DPS", value=format_dps(dps_players), inline=False)
  embed_var.add_field(name='', value="-# Want to receive pings? Use `/roles` and pick which!", inline=False)
  tank_role = discord.utils.get(interaction.guild.roles, name = 'Tank')
  healer_role = discord.utils.get(interaction.guild.roles, name = 'Healer')
  dps_role = discord.utils.get(interaction.guild.roles, name = 'DPS')
  content_var = (
    f"{interaction.user.mention} wants to run a {dungeon_name} +{key_level if key_level<99 else '*any*'}{' at ' + time if not time is None else ''}!"
    f"\nThey need "
    f"{tank_role.mention+' ' if tank else ''}"
    f"{healer_role.mention+' ' if healer else ''}"
    f"{str(dps) + ' x ' + dps_role.mention+' ' if dps is None or dps > 0 else ''}"
    f"{'nothing...?' if (not tank and not healer and not dps) else ''}")
  return content_var, embed_var

# --------- Roles Command ---------

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
@tree.command()                                 # Adds command globally
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
  
@tree.command(guild=discord.Object(id=TEST_ID)) # Adds command to test server
# @tree.command()                                 # Adds command globally
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

# ---------- Bot setup ----------
@client.event
async def on_guild_join(guild):
  log(f'Checking if roles must be added to newly joined server: {guild.name}')
  if discord.utils.get(guild.roles, name = 'Tank') == None: 
    log(f'  Creating missing role Tank on server {guild.name}')
    await guild.create_role(name='Tank')
  if discord.utils.get(guild.roles, name = 'Healer') == None: 
    log(f'  Creating missing role Healer on server {guild.name}')
    await guild.create_role(name='Healer')
  if discord.utils.get(guild.roles, name = 'DPS') == None: 
    log(f'  Creating missing role DPS on server {guild.name}')
    await guild.create_role(name='DPS')

  log(f'Sending welcome message in {guild.name}')
  channel = guild.system_channel
  if channel.permissions_for(guild.me).send_messages:
    await channel.send(f"""
Hello! You've added the __Belan Shi Bot__ to your server. Here's how it works.

It has added 3 roles to your server `Tank`, `Healer`, & `DPS`. These are the roles it will ping. They're intended to be assigned based on player preference.\n 
Anyone can call the `/roles` command, and select the roles they wish to receive pings from. Clicking the roles buttons when you already have the role, removes the role, disabling pings again.

`/key` is the command to start a Mythic Plus run. It has two things you must to decide, and 4 optional ones.
**REQUIRED** `dungeon-name` - which is the name of the dungeon you wanna run. You can type in `any` if you don't have a specific in mind.
**REQUIRED** `key-level` - which is just what level the keystone is. You can type any number greater than `99` if you don't care which level.
*OPTIONAL* `tank` - How many tanks do you need? Basically `0` if you already have a tank or `1` is you need one.
*OPTIONAL* `healer` - Same as tanks, how many healers do you need, `0` or `1`
*OPTIONAL* `missing-dps` - how many dps are you missing. `0` - `3`
*OPTIONAL* `time` - If there's a specific time you'd like to run the key.

Leaving the optional ones empty, creates a group that needs all roles. 

When you write `/key`, Discord will help filling in the things you need with a handy little UI on your chatbox. If you've done all the things right, the bot will post a sign-up post, kinda like we know it from our raid and m+ sign up. As the creator, you can :x: `CANCEL` and :white_check_mark: `LOCK RUN` a run. Cancelling it will delete the sign up post. Locking it will lock the sign up buttons, and post the team in a new message.
      """)

@client.event
async def on_guild_remove(guild):
  log(f'I was removed from guild {guild.name}')

@client.event
async def on_guild_role_delete(role):
  if role.name == 'Tank' or role.name == 'Healer' or role.name == 'DPS':
    log(f'{role.guild.name} deleted the {role.name} role. Recreating it, informing server.')
    await role.guild.create_role(name=role.name)
      
@client.event
async def on_ready() -> None:
  # tree.clear_commands(guild=None) # Should clear all phantom commands globally
  await tree.sync(guild=discord.Object(id=TEST_ID)) # Syncs command tree to test server
  await tree.sync()                                 # Syncs command tree globally
  log(f'{client.user} successfully logged in with ID: {client.user.id}')

def log(log_message):
  logging.info(f'{log_message}')
  # time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  # print(f'{time} - {log_message}')


def main() -> None:
  logging.basicConfig(
    filename="bot.log",
    encoding="utf-8",
    filemode="a",
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
  )
  client.run(token=TOKEN)


if __name__ == '__main__':
  main()
