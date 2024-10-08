import datetime
import random
from typing import Final, Optional
import os

import discord
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, ui, Interaction, Embed

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')  # Discord bot token, SECRET
# TEST_ID: Final[int] = 368116240276914176  # Belan Shi Discord ID
TEST_ID: Final[int] = 489890364090744892  # Test Server Discord ID
DELETE_TIME: Final[int] = 10  # How long after sending an ephemeral message is deleted automatically.

intents = Intents.default()
intents.message_content = True  # Allow the bot to see message content
intents.members = True  # Allow the bot to see message content
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
          await interaction.response.send_message("Tank spot taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
          return
        if interaction.user == self.players[0][0]: # If user is the signed tank
          self.players[0].remove(interaction.user)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "TANK":
              field["value"] = f"🛡 Tank open"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))
          await interaction.response.send_message("You've removed yourself as tank!", ephemeral=True,
                                                  delete_after=DELETE_TIME)
          username = interaction.user.nick if not None else interaction.user.name
          print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} un-joined as TANK")
          return

      if len(self.players[1]) > 0 and interaction.user in self.players[1]: # If user is already signed up as healer
        self.players[1].remove(interaction.user)
        self.players[0].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "HEALER": field["value"] = f"💚 Healer open"
          if field["name"] == "TANK": field["value"] = f"❌ {self.players[0][0].nick if not None else '*Reserved*'}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You swapped role to tank!", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not 'None' else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} swapped from HEALER to TANK")
        return

      if len(self.players[2]) > 0 and interaction.user in self.players[2]: # If the user is already signed up as dps
        self.players[2].remove(interaction.user)
        self.players[0].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
          if field["name"] == "TANK": field["value"] = f"❌ {self.players[0][0].nick if not None else '*Reserved*'}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You've swapped role to tank!", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not 'None' else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} swapped from DPS to TANK")
        return

      # If the tank spot is open
      username = interaction.user.nick if not None else interaction.user.name
      print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} joined as TANK")
      self.players[0].append(interaction.user)
      embed_dict = interaction.message.embeds[0].to_dict()
      for field in embed_dict["fields"]:
        if field["name"] == "TANK":
          field["value"] = f"❌ {self.players[0][0].nick if not None else '*Reserved*'}"
      await interaction.message.edit(embed=Embed.from_dict(embed_dict))
      await interaction.response.send_message("You've marked you want to join as tank!", ephemeral=True, delete_after=DELETE_TIME)

    tank_button.callback = tankbutton  # Add functionality to the button object.
    self.add_item(tank_button)  # Add the button to the view.

    # ---------- Healer button ----------
    healer_button = ui.Button(label="HEALER", emoji='💚', disabled=len(self.players[1]) > 0, custom_id='healer_button')  # Creates the button object

    async def healerbutton(interaction: discord.Interaction):
      """Creates the functionality of the healer button"""

      if len(self.players[1]) > 0:
        if not interaction.user == self.players[1][0]: # If healer spot is already taken
          await interaction.response.send_message("Healer spot taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
          return
        if interaction.user == self.players[1][0]: # If the user is the signed healer
          self.players[1].remove(interaction.user)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "HEALER":
              field["value"] = f"💚 Healer open"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))
          await interaction.response.send_message("You've removed yourself as healer!", ephemeral=True,
                                                  delete_after=DELETE_TIME)
          username = interaction.user.nick if not 'None' else interaction.user.name
          print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} un-joined as HEALER")
          return

      if len(self.players[0]) > 0 and interaction.user in self.players[0]:  # If user is already signed up as tank
        self.players[0].remove(interaction.user)
        self.players[1].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "TANK": field["value"] = f"🛡 Tank open"
          if field["name"] == "HEALER": field["value"] = f"❌ {self.players[1][0].nick if not None else '*Reserved*'}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You swapped role to healer!", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not 'None' else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} swapped from TANK to HEALER")
        return

      if len(self.players[2]) > 0 and interaction.user in self.players[2]:  # If the user is already signed up as dps
        self.players[2].remove(interaction.user)
        self.players[1].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
          if field["name"] == "HEALER": field["value"] = f"❌ {self.players[1][0].nick if not None else '*Reserved*'}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You've swapped role to healer!", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not 'None' else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} swapped from DPS to HEALER")
        return

      # If the healer spot is open
      username = interaction.user.nick if not 'None' else interaction.user.name
      print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} joined as HEALER")
      self.players[1].append(interaction.user)
      embed_dict = interaction.message.embeds[0].to_dict()
      for field in embed_dict["fields"]:
        if field["name"] == "HEALER":
          field["value"] = f"❌ {self.players[1][0].nick if not None else '*Reserved*'}"
      await interaction.message.edit(embed=Embed.from_dict(embed_dict))
      await interaction.response.send_message("You've marked you want to join as healer!", ephemeral=True, delete_after=DELETE_TIME)

    healer_button.callback = healerbutton  # Add functionality to the button object.
    self.add_item(healer_button)  # Add the button to the view.

    # ---------- DPS button ----------
    dps_button = ui.Button(label="DPS", emoji='⚔️', disabled=len(self.players[2]) == 3, custom_id='dps_button')  # Creates the button object

    async def dpsbutton(interaction: discord.Interaction):
      """Creates the functionality of the DPS button"""

      if len(self.players[2]) == 3 and not interaction.user in self.players[2]: # If dps spots are already taken
        await interaction.response.send_message("DPS spots taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
        return

      if len(self.players[2]) > 0 and interaction.user in self.players[2]: # If the user is signed as dps
        self.players[2].remove(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS":
            field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You've removed yourself as DPS!", ephemeral=True,
                                                delete_after=DELETE_TIME)
        username = interaction.user.nick if not 'None' else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} un-joined as DPS")
        return

      if len(self.players[0]) > 0 and interaction.user in self.players[0]:  # If user is already signed up as tank
        self.players[0].remove(interaction.user)
        self.players[2].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "TANK": field["value"] = f"🛡 Tank open"
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You swapped role to DPS!", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not 'None' else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} swapped from TANK to DPS")
        return

      if len(self.players[1]) > 0 and interaction.user in self.players[1]:  # If the user is already signed up as healer
        self.players[1].remove(interaction.user)
        self.players[2].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "HEALER": field["value"] = f"💚 Healer open"
          if field["name"] == "DPS": field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You've swapped role to DPS!", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not 'None' else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} swapped from HEALER to DPS")
        return

      # If a dps spot is open
      await interaction.response.send_message("You've marked you want to join as DPS!", ephemeral=True,
                                              delete_after=DELETE_TIME)
      username = interaction.user.nick if not 'None' else interaction.user.name
      print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} joined as DPS")
      self.players[2].append(interaction.user)
      embed_dict = interaction.message.embeds[0].to_dict()
      for field in embed_dict["fields"]:
        if field["name"] == "DPS":
          field["value"] = format_dps(self.players[2])
      await interaction.message.edit(embed=Embed.from_dict(embed_dict))

    dps_button.callback = dpsbutton  # Add functionality to the button object.
    self.add_item(dps_button)  # Add the button to the view.

    # ---------- Cancel button ----------
    cancel_button = ui.Button(label="CANCEL", emoji='❌', custom_id='cancel_button')  # Creates the button object

    async def cancelbutton(interaction: discord.Interaction):
      """Creates the functionality of the cancel button"""

      if interaction.user == self.user:
        await interaction.message.delete()
        await interaction.response.send_message(content="Run cancelled!", ephemeral=True, delete_after=DELETE_TIME)
        username = interaction.user.nick if not None else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} cancelled the key.")
        # TODO Should also delete any run confirmed messages.
        return
      else:
        await interaction.response.send_message(content="You cannot cancel a run you did not start!", ephemeral=True,
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
                                                 f"\n⚔️ # 3: {dps3}")
        self.remove_item(confirm_button)
        self.add_item(unconfirm_button)
        await interaction.message.edit(view=self)
        username = interaction.user.nick if not None else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} locked the key.")
        return
      else:
        await interaction.response.send_message(content="You cannot lock a run you did not start!", ephemeral=True,
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
        await interaction.response.send_message(content="Run un-locked!\nRole buttons activated.", ephemeral=True,
                                                delete_after=DELETE_TIME)
        username = interaction.user.nick if not None else interaction.user.name
        print(f"{datetime.datetime.now()} - KEY: {self.id} - {username} un-locked the key.")
        self.remove_item(unconfirm_button)
        self.add_item(confirm_button)
        await interaction.message.edit(view=self)
        return
      else:
        await interaction.response.send_message(content="You cannot un-lock a run you did not start!",
                                                ephemeral=True, delete_after=DELETE_TIME)
      return

    unconfirm_button.callback = unconfirmbutton  # Add functionality to the button object.
    # self.add_item(unconfirm_button) # Notably not added to the view, as that is part of the confirm button functionality


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
  :param dps: How many dps is missing?
  :param time: At a specific time?
  """
  if interaction.guild_id == 489890364090744892 and interaction.channel.id != 786705743336046593:
    await interaction.response.send_message(content="Wrong channel, Gala...", ephemeral=True, delete_after=DELETE_TIME)
    return
  if interaction.guild_id == 368116240276914176 and interaction.channel.id != 374937731744268289:
    await interaction.response.send_message(content="Wrong channel, Maya...", ephemeral=True, delete_after=DELETE_TIME)
    return

  print(f"{datetime.datetime.now()} - NEW KEY: {interaction.user.nick} created a new key with parameters:\n"
    f"  dungeon_name={dungeon_name}, key_level={key_level}, tank={tank}, healer={healer}, dps={dps}\n"
    f"-------") # Primitive logging

  if dps <= -1:  # Disallow negative number of DPS players
    await interaction.response.send_message(content="Illegal argument: `dps` must be a non-negative integer",
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
def format_dps(dps_players=None):
  """Formats the 3 lines of DPS text for the embed
  :return formatted string containing reserved/open/player names based on signup and creation details.
  """
  if dps_players is None:
    dps_players = []
  if len(dps_players) == 3:
    dps1 = dps_players[0].nick if not isinstance(dps_players[0],str) else dps_players[0]
    dps2 = dps_players[1].nick if not isinstance(dps_players[1],str) else dps_players[1]
    dps3 = dps_players[2].nick if not isinstance(dps_players[2],str) else dps_players[2]
    return f"❌ # 1: {dps1}\n❌ # 2: {dps2}\n❌ # 3: {dps3}\n"
  elif len(dps_players) == 2:
    dps1 = dps_players[0].nick if not isinstance(dps_players[0],str) else dps_players[0]
    dps2 = dps_players[1].nick if not isinstance(dps_players[1],str) else dps_players[1]
    return f"❌ # 1: {dps1}\n❌ # 2: {dps2}\n⚔️ # 3: *Open*\n"
  elif len(dps_players) == 1:
    dps1 = dps_players[0].nick if not isinstance(dps_players[0],str) else dps_players[0]
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
    "Your mom's a hoe."
  ]
  return random.choice(descs)

async def format_message(interaction, dungeon_name, key_level, tank, healer, dps, time, dps_players, tank_player=None,
                         healer_player=None):
  """Formats the embed and the content of the message
  :return two variables: the content_var (message content) & embed_var (content of the embed)
  """
  embed_var = discord.Embed(
    title=f"{interaction.user.nick if not None else interaction.user.name} want to run a {dungeon_name} +{key_level if key_level<99 else '*any*'}{' at ' + time if not time is None else ''}!",
    description=random_desc(), color=0x00ff00 if 0 <= key_level < 5 else 0xffff00 if 5 <= key_level <= 7 else 0xff0000)
  embed_var.add_field(name="TANK",
                      value=f"{'❌ *Reserved*' if tank == 0 else {tank_player.nick} if not tank_player is None else '🛡 Tank open'}",
                      inline=False)
  embed_var.add_field(name="HEALER",
                      value=f"{'❌ *Reserved*' if healer == 0 else {healer_player.nick} if not healer_player is None else '💚 Healer open'}",
                      inline=False)
  embed_var.add_field(name="DPS", value=format_dps(dps_players), inline=False)
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


# ---------- Bot setup ----------
@client.event
async def on_ready() -> None:
  # tree.clear_commands(guild=None) # Should clear all phantom commands globally
  # await tree.sync(guild=discord.Object(id=TEST_ID)) # Syncs command tree to test server
  await tree.sync()                                 # Syncs command tree globally
  print(f'{datetime.datetime.now()} - {client.user} successfully logged in with ID: {client.user.id}')


def main() -> None:
  client.run(token=TOKEN)


if __name__ == '__main__':
  main()

# ---------------- OLD STUFF ----------------

# @client.event
# async def on_message(message: Message) -> None:
#   if message.author == client.user:
#     return
#
#   username = str(message.author)
#   user_message = str(message.content)
#   channel = str(message.channel)
#
#   print(f'[{channel}] {username}: {user_message}')
#   await send_message(message, user_message)

# async def send_message(message: Message, user_message: str) -> None:
#   if not user_message:
#     print('Bad message, empty, missing intents')
#     return
#
#   if is_private := user_message[0] == '?':
#     user_message = user_message[1:]
#
#   try:
#     await message.channel.send(content=f"You wrote: {user_message}")
#   except Exception as e:
#     print(e)

# @tree.command(guild=discord.Object(id=TEST_ID))
# async def testbutton(interaction: discord.Interaction):
#   view_var = RoleButtons(True,True,2)
#   await interaction.response.send_message(view=view_var)
#
# @client.event
# async def on_reaction_add(reaction, user):
#   message = reaction.message
#   channel = discord.utils.get(message.guild.channels, name="general")
#   if message.channel.id == channel.id:
#         print(f"User {user} reacted with {reaction} to message ID: {reaction.message.id}")
