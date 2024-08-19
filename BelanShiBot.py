from datetime import datetime
from pickle import FALSE
from sys import flags
from tkinter.ttk import Label
from typing import Final, Optional
import os

import discord
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, ui, Interaction, Embed
from pyexpat.errors import messages

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
GUILD_ID: Final[int] = 368116240276914176 # Belan Shi Discord ID
TEST_ID: Final[int] = 489890364090744892 # Test Server Discord ID
VERBOSE: Final[bool] = False
DELETE_TIME: Final[int] = 3

intents = Intents.default()
intents.message_content = True
intents.reactions = True
client = Client(intents=intents)
tree = app_commands.CommandTree(client)

class RoleButtons(ui.View):
    def __init__(self, user, players):
      super().__init__()
      self.user = user
      self.players = players
      self.add_buttons()

    def add_buttons(self):
      tank_button = ui.Button(label="TANK", emoji='🛡', disabled=len(self.players[0]) > 0)
      healer_button = ui.Button(label="HEALER", emoji='💚', disabled=len(self.players[1]) > 0)
      dps_button = ui.Button(label="DPS", emoji='⚔️', disabled=len(self.players[2]) == 3)
      cancel_button = ui.Button(label="CANCEL", emoji='❌')
      confirm_button = ui.Button(label="CONFIRM", emoji='✅')
      unconfirm_button = ui.Button(label="UN-CONFIRM", emoji='↩️')

      async def tankbutton(interaction: discord.Interaction):
        if interaction.user in self.players[1] or interaction.user in self.players[2]:
          await interaction.response.send_message("You cannot be more than one role in a run!", ephemeral=True, delete_after=DELETE_TIME)
          return
        if not len(self.players[0]) == 0:
          if interaction.user == self.players[0][0]:
            self.players[0].pop()
            embed_dict = interaction.message.embeds[0].to_dict()
            for field in embed_dict["fields"]:
              if field["name"] == "TANK":
                field["value"] = f"🛡 Tank open"
            await interaction.message.edit(embed=Embed.from_dict(embed_dict))
            await interaction.response.send_message("You've removed yourself as tank!", ephemeral=True, delete_after=DELETE_TIME)
            return
          else:
            await interaction.response.send_message("Tank spot taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
            return
        else:
          await interaction.response.send_message("You've marked you want to join as tank!", ephemeral=True, delete_after=DELETE_TIME)
          self.players[0].append(interaction.user)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "TANK":
              field["value"] = f"🛡 {self.players[0][0]}"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))

      async def healerbutton(interaction: discord.Interaction):
        if interaction.user in self.players[0] or interaction.user in self.players[2]:
          await interaction.response.send_message("You cannot be more than one role in a run!", ephemeral=True, delete_after=DELETE_TIME)
          return
        if not len(self.players[1]) == 0:
          if interaction.user == self.players[1][0]:
            self.players[1].pop()
            embed_dict = interaction.message.embeds[0].to_dict()
            for field in embed_dict["fields"]:
              if field["name"] == "HEALER":
                field["value"] = f"💚 Healer open"
            await interaction.message.edit(embed=Embed.from_dict(embed_dict))
            await interaction.response.send_message("You've removed yourself as healer!", ephemeral=True, delete_after=DELETE_TIME)
            return
          else:
            await interaction.response.send_message("healer spot taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
            return
        else:
          await interaction.response.send_message("You've marked you want to join as healer!", ephemeral=True, delete_after=DELETE_TIME)
          self.players[1].append(interaction.user)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "HEALER":
              field["value"] = f"💚 {self.players[1][0]}"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))

      async def dpsbutton(interaction: discord.Interaction):
        print(self.players)
        if interaction.user in self.players[0] or interaction.user in self.players[1]:
          await interaction.response.send_message("You cannot be more than one role in a run!", ephemeral=True, delete_after=DELETE_TIME)
          return
        if interaction.user in self.players[2]:
            self.players[2].remove(interaction.user)
            embed_dict = interaction.message.embeds[0].to_dict()
            for field in embed_dict["fields"]:
              if field["name"] == "DPS":
                field["value"] = format_dps(self.players[2])
            await interaction.message.edit(embed=Embed.from_dict(embed_dict))
            await interaction.response.send_message("You've removed yourself as DPS!", ephemeral=True, delete_after=DELETE_TIME)
            return
        if len(self.players[2]) == 3:
          await interaction.response.send_message("DPS spots taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
          return
        await interaction.response.send_message("You've marked you want to join as DPS!", ephemeral=True, delete_after=DELETE_TIME)
        self.players[2].append(interaction.user)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS":
            field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))

      async def cancelbutton(interaction: discord.Interaction):
        if interaction.user == self.user:
          await interaction.message.delete()
          await interaction.response.send_message(content="Run cancelled!", ephemeral=True, delete_after=DELETE_TIME)
          return
        else:
          await interaction.response.send_message(content="You cannot cancel a run you did not start!", ephemeral=True, delete_after=DELETE_TIME)
        return

      async def confirmbutton(interaction: discord.Interaction):
        if interaction.user == self.user:
          for child in self.children:
            if type(child) == ui.Button and not (child.label == "CONFIRM" or child.label == "CANCEL"):
              child.disabled = True
          await interaction.response.send_message(content="Run confirmed!\nRole buttons deactivated", ephemeral=True, delete_after=DELETE_TIME)
          self.remove_item(confirm_button)
          self.add_item(unconfirm_button)
          await interaction.message.edit(view=self)
          return
        else:
          await interaction.response.send_message(content="You cannot confirm a run you did not start!", ephemeral=True, delete_after=DELETE_TIME)
        return

      async def unconfirmbutton(interaction: discord.Interaction):
        if interaction.user == self.user:
          for child in self.children:
            if type(child) == ui.Button and not (child.label == "CONFIRM" or child.label == "CANCEL"or child.label == "UN-CONFIRM"):
              child.disabled = False
          await interaction.response.send_message(content="Run un-confirmed!\nRole buttons activated.", ephemeral=True, delete_after=DELETE_TIME)
          self.remove_item(unconfirm_button)
          self.add_item(confirm_button)
          await interaction.message.edit(view=self)
          return
        else:
          await interaction.response.send_message(content="You cannot un-confirm a run you did not start!", ephemeral=True, delete_after=DELETE_TIME)
        return

      tank_button.callback = tankbutton
      healer_button.callback = healerbutton
      dps_button.callback = dpsbutton
      cancel_button.callback = cancelbutton
      confirm_button.callback = confirmbutton
      unconfirm_button.callback = unconfirmbutton


      self.add_item(tank_button)
      self.add_item(healer_button)
      self.add_item(dps_button)
      self.add_item(cancel_button)
      self.add_item(confirm_button)

def format_dps(dps_players = []):
  if len(dps_players) == 3:
    return f"⚔️ # 1: {dps_players[0]}\n⚔️ # 2: {dps_players[1]}\n⚔️ # 3: {dps_players[2]}\n"
  elif len(dps_players) == 2:
    return f"⚔️ # 1: {dps_players[0]}\n⚔️ # 2: {dps_players[1]}\n⚔️ # 3: *Open*\n"
  elif len(dps_players) == 1:
    return f"⚔️ # 1: {dps_players[0]}\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  elif len(dps_players) == 0:
    return f"⚔️ # 1: *Open*\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  return None

async def format_embed(interaction, dungeon_name, key_level, tank, healer, dps, time, dps_players, tank_player = None, healer_player = None):
  embed_var = discord.Embed(title=f"{interaction.user.nick if not 'None' else interaction.user.name} want to run a {dungeon_name} +{key_level}{' at '+time if not time is None else ''}!",
                            description="Desc", color=0x00ff00 if 0 <= key_level < 5 else 0xffff00 if 5 <= key_level <= 7 else 0xff0000)
  embed_var.add_field(name="TANK", value=f"{'🛡 *Reserved*' if tank == 0 else {tank_player} if not tank_player is None else '🛡 Tank open'}", inline=False)
  embed_var.add_field(name="HEALER", value=f"{'💚 *Reserved*' if healer == 0 else {healer_player} if not healer_player is None else '💚 Healer open'}", inline=False)
  embed_var.add_field(name="DPS", value=format_dps(dps_players), inline=False)

  content_var = (f"{interaction.user.mention} want to run a {dungeon_name} +{key_level}{' at '+time if not time is None else ''}!"
                 f"\nThey need "
                 f"{'<@&805437880821612604> ' if not tank else ''}"
                 f"{'<@&1275027330045055048> ' if not healer else ''}"
                 f"{str(dps) + ' x ' + '<@&757298292789870672>' if dps == None or dps > 0 else ''}"
                 f"{'nothing...?' if tank and healer and dps == 0 else ''}")

  return content_var, embed_var

@tree.command(guild=discord.Object(id=TEST_ID))
@app_commands.rename(dungeon_name='dungeon-name', key_level='key-level', tank='tank', healer='healer', dps='missing-dps')
async def key(
    interaction: discord.Interaction,
    dungeon_name: str,
    key_level: int,
    tank: Optional[int] = 1,
    healer: Optional[int] = 1,
    dps: Optional[int] = 3,
    time: Optional[str] = None):
  """Creates a group people can join
  :param dungeon_name: Name of the dungeon
  :param key_level: Level of the key
  :param tank: Missing tank?
  :param healer: Missing healer?
  :param dps: How many dps is missing?
  :param time: At a specific time?
  """
  print(f"{interaction.user.name} ({interaction.user.id}) used /key with parameters: dungeon_name={dungeon_name}, key_level={key_level}, tank={tank}, healer={healer}, dps={dps}")
  if dps<=-1:
    await interaction.response.send_message(content="Illegal argument: `dps` must be a positive integer", ephemeral=True)
    return
  else:
    tank_player = ["*Reserved*"] * (1 - tank)
    heal_player = ["*Reserved*"] * (1 - healer)
    dps_players = ["*Reserved*"] * (3 - dps)
    players = [tank_player,heal_player,dps_players]
    print(players)

    content_var, embed_var = await format_embed(interaction, dungeon_name, key_level, tank, healer, dps, time, dps_players)
    await interaction.response.send_message(content=content_var, embed=embed_var, view=RoleButtons(interaction.user, players))

@client.event
async def on_reaction_add(reaction, user):
  message = reaction.message
  channel = discord.utils.get(message.guild.channels, name="general")
  if message.channel.id == channel.id:
        print(f"User {user} reacted with {reaction} to message ID: {reaction.message.id}")

@client.event
async def on_ready() -> None:
  await tree.sync(guild=discord.Object(id=TEST_ID))
  print(f'{client.user} successfully logged in with ID: {client.user.id}')


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



