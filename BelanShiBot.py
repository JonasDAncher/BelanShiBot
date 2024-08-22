from typing import Final, Optional
import os

import discord
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, ui, Interaction, Embed, SelectOption, TextStyle

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')  # Discord bot token, SECRET
# TEST_ID: Final[int] = 368116240276914176  # Belan Shi Discord ID
TEST_ID: Final[int] = 489890364090744892  # Test Server Discord ID
DELETE_TIME: Final[int] = 10  # How long after sending an ephemeral message is deleted automatically.

intents = Intents.default()
intents.message_content = True  # Allow the bot to see message content
client = Client(intents=intents)
tree = app_commands.CommandTree(client)

# ---------- Key command section ----------
class RoleButtons(ui.View):
  def __init__(self, user, players):
    super().__init__()
    self.user = user
    self.players = players
    self.add_buttons()

  def add_buttons(self):
    """Creates the clickable role, confirm and cancel buttons."""

    # ---------- Tank button ----------
    tank_button = ui.Button(label="TANK", emoji='🛡', disabled=len(self.players[0]) > 0)  # Creates the button object

    async def tankbutton(interaction: discord.Interaction):
      """Creates the functionality of the tank button"""

      if interaction.user.nick in self.players[1] or interaction.user.nick in self.players[2]:
        await interaction.response.send_message("You cannot be more than one role in a run!", ephemeral=True,
                                                delete_after=DELETE_TIME)
        return
      if not len(self.players[0]) == 0:
        if interaction.user.nick == self.players[0][0]:
          self.players[0].remove(interaction.user.nick)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "TANK":
              field["value"] = f"🛡 Tank open"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))
          await interaction.response.send_message("You've removed yourself as tank!", ephemeral=True,
                                                  delete_after=DELETE_TIME)
          return
        else:
          await interaction.response.send_message("Tank spot taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
          return
      else:
        await interaction.response.send_message("You've marked you want to join as tank!", ephemeral=True,
                                                delete_after=DELETE_TIME)
        self.players[0].append(interaction.user.nick)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "TANK":
            field["value"] = f"🛡 {self.players[0][0]}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))

    tank_button.callback = tankbutton  # Add functionality to the button object.
    self.add_item(tank_button)  # Add the button to the view.

    # ---------- Healer button ----------
    healer_button = ui.Button(label="HEALER", emoji='💚', disabled=len(self.players[1]) > 0)  # Creates the button object

    async def healerbutton(interaction: discord.Interaction):
      """Creates the functionality of the healer button"""

      if interaction.user.nick in self.players[0] or interaction.user.nick in self.players[2]:
        await interaction.response.send_message("You cannot be more than one role in a run!", ephemeral=True,
                                                delete_after=DELETE_TIME)
        return
      if not len(self.players[1]) == 0:
        if interaction.user.nick == self.players[1][0]:
          self.players[1].remove(interaction.user.nick)
          embed_dict = interaction.message.embeds[0].to_dict()
          for field in embed_dict["fields"]:
            if field["name"] == "HEALER":
              field["value"] = f"💚 Healer open"
          await interaction.message.edit(embed=Embed.from_dict(embed_dict))
          await interaction.response.send_message("You've removed yourself as healer!", ephemeral=True,
                                                  delete_after=DELETE_TIME)
          return
        else:
          await interaction.response.send_message("healer spot taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
          return
      else:
        await interaction.response.send_message("You've marked you want to join as healer!", ephemeral=True,
                                                delete_after=DELETE_TIME)
        self.players[1].append(interaction.user.nick)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "HEALER":
            field["value"] = f"💚 {self.players[1][0]}"
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))

    healer_button.callback = healerbutton  # Add functionality to the button object.
    self.add_item(healer_button)  # Add the button to the view.

    # ---------- DPS button ----------
    dps_button = ui.Button(label="DPS", emoji='⚔️', disabled=len(self.players[2]) == 3)  # Creates the button object

    async def dpsbutton(interaction: discord.Interaction):
      """Creates the functionality of the DPS button"""

      print(self.players)
      if interaction.user.nick in self.players[0] or interaction.user.nick in self.players[1]:
        await interaction.response.send_message("You cannot be more than one role in a run!", ephemeral=True,
                                                delete_after=DELETE_TIME)
        return
      if interaction.user.nick in self.players[2]:
        self.players[2].remove(interaction.user.nick)
        embed_dict = interaction.message.embeds[0].to_dict()
        for field in embed_dict["fields"]:
          if field["name"] == "DPS":
            field["value"] = format_dps(self.players[2])
        await interaction.message.edit(embed=Embed.from_dict(embed_dict))
        await interaction.response.send_message("You've removed yourself as DPS!", ephemeral=True,
                                                delete_after=DELETE_TIME)
        return
      if len(self.players[2]) == 3:
        await interaction.response.send_message("DPS spots taken, sorry.", ephemeral=True, delete_after=DELETE_TIME)
        return
      await interaction.response.send_message("You've marked you want to join as DPS!", ephemeral=True,
                                              delete_after=DELETE_TIME)
      self.players[2].append(interaction.user.nick)
      embed_dict = interaction.message.embeds[0].to_dict()
      for field in embed_dict["fields"]:
        if field["name"] == "DPS":
          field["value"] = format_dps(self.players[2])
      await interaction.message.edit(embed=Embed.from_dict(embed_dict))

    dps_button.callback = dpsbutton  # Add functionality to the button object.
    self.add_item(dps_button)  # Add the button to the view.

    # ---------- Cancel button ----------
    cancel_button = ui.Button(label="CANCEL", emoji='❌')  # Creates the button object

    async def cancelbutton(interaction: discord.Interaction):
      """Creates the functionality of the cancel button"""

      if interaction.user == self.user:
        await interaction.message.delete()
        await interaction.response.send_message(content="Run cancelled!", ephemeral=True, delete_after=DELETE_TIME)
        # TODO Should also delete any run confirmed messages.
        return
      else:
        await interaction.response.send_message(content="You cannot cancel a run you did not start!", ephemeral=True,
                                                delete_after=DELETE_TIME)
      return

    cancel_button.callback = cancelbutton  # Add functionality to the button object.
    self.add_item(cancel_button)  # Add the button to the view.

    # ---------- Confirm button ----------
    confirm_button = ui.Button(label="CONFIRM", emoji='✅')  # Creates the button object

    async def confirmbutton(interaction: discord.Interaction):
      """Creates the functionality of the confirm button"""

      if interaction.user == self.user:
        for child in self.children:
          if type(child) == ui.Button and not (child.label == "CONFIRM" or child.label == "CANCEL"):
            child.disabled = True
        # await interaction.response.send_message(content="Run confirmed!\nRole buttons deactivated", ephemeral=True,
        #                                         delete_after=DELETE_TIME)
        # ^^^^^^ disabled: using vvvvvv instead.
        # Sends a group composition message on run confirmed. However, need a good solution for 'unconfirming' a
        # confirmed run, as this message should then be deleted. TODO Delete old message, if run is un-confirmed
        await interaction.response.send_message(content=f"Run confirmed!"
                                                 f"\n🛡: {self.players[0][0] if 0 < len(self.players[0]) else '*Open*'}"
                                                 f"\n💚: {self.players[1][0] if 0 < len(self.players[1]) else '*Open*'}"
                                                 f"\n⚔️ # 1: {self.players[2][0] if 0 < len(self.players[2]) else '*Open*'}"
                                                 f"\n⚔️ # 2: {self.players[2][1] if 1 < len(self.players[2]) else '*Open*'}"
                                                 f"\n⚔️ # 3: {self.players[2][2] if 2 < len(self.players[2]) else '*Open*'}")
        self.remove_item(confirm_button)
        self.add_item(unconfirm_button) # Currently disabled re-enables buttons that start as disabled due to reserved
        await interaction.message.edit(view=self)
        return
      else:
        await interaction.response.send_message(content="You cannot confirm a run you did not start!", ephemeral=True,
                                                delete_after=DELETE_TIME)
      return

    confirm_button.callback = confirmbutton  # Add functionality to the button object.
    self.add_item(confirm_button)  # Add the button to the view.

    # ---------- Unconfirm button ----------
    unconfirm_button = ui.Button(label="UN-CONFIRM", emoji='↩️')  # Creates the button object

    async def unconfirmbutton(interaction: discord.Interaction):
      """Creates the functionality of the unconfirm button"""

      if interaction.user == self.user:
        for child in self.children:
          if type(child) == ui.Button and not (
              child.label == "CONFIRM" or child.label == "CANCEL" or child.label == "UN-CONFIRM"):
            child.disabled = False
        await interaction.response.send_message(content="Run un-confirmed!\nRole buttons activated.", ephemeral=True,
                                                delete_after=DELETE_TIME)
        self.remove_item(unconfirm_button)
        self.add_item(confirm_button)
        await interaction.message.edit(view=self)
        return
      else:
        await interaction.response.send_message(content="You cannot un-confirm a run you did not start!",
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
  :param key_level: Level of the key
  :param tank: Missing tank?
  :param healer: Missing healer?
  :param dps: How many dps is missing?
  :param time: At a specific time?
  """
  print(
    f"{interaction.user.name} ({interaction.user.id}) used /key with parameters:\n"
    f"  dungeon_name={dungeon_name}, key_level={key_level}, tank={tank}, healer={healer}, dps={dps}\n"
    f"-------")  # Primitive logging

  if dps <= -1:  # Disallow negative number of DPS players
    await interaction.response.send_message(content="Illegal argument: `dps` must be a positive integer",
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
    return f"⚔️ # 1: {dps_players[0]}\n⚔️ # 2: {dps_players[1]}\n⚔️ # 3: {dps_players[2]}\n"
  elif len(dps_players) == 2:
    return f"⚔️ # 1: {dps_players[0]}\n⚔️ # 2: {dps_players[1]}\n⚔️ # 3: *Open*\n"
  elif len(dps_players) == 1:
    return f"⚔️ # 1: {dps_players[0]}\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  elif len(dps_players) == 0:
    return f"⚔️ # 1: *Open*\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  return None


async def format_message(interaction, dungeon_name, key_level, tank, healer, dps, time, dps_players, tank_player=None,
                         healer_player=None):
  """Formats the embed and the content of the message
  :return two variables: the content_var (message content) & embed_var (content of the embed)
  """
  embed_var = discord.Embed(
    title=f"{interaction.user.nick if not 'None' else interaction.user.name} want to run a {dungeon_name} +{key_level}{' at ' + time if not time is None else ''}!",
    description="Desc", color=0x00ff00 if 0 <= key_level < 5 else 0xffff00 if 5 <= key_level <= 7 else 0xff0000)
  embed_var.add_field(name="TANK",
                      value=f"{'🛡 *Reserved*' if tank == 0 else {tank_player} if not tank_player is None else '🛡 Tank open'}",
                      inline=False)
  embed_var.add_field(name="HEALER",
                      value=f"{'💚 *Reserved*' if healer == 0 else {healer_player} if not healer_player is None else '💚 Healer open'}",
                      inline=False)
  embed_var.add_field(name="DPS", value=format_dps(dps_players), inline=False)

  content_var = (
    f"{interaction.user.mention} want to run a {dungeon_name} +{key_level}{' at ' + time if not time is None else ''}!"
    f"\nThey need "
    f"{'<@&805438949341659137> ' if tank else ''}"
    f"{'<@&805439339302748200> ' if healer else ''}"
    f"{str(dps) + ' x ' + '<@&805439297309245531>' if dps == None or dps > 0 else ''}"
    # f"{'<@&805437880821612604> ' if not tank else ''}"
    # f"{'<@&1275027330045055048> ' if not healer else ''}"
    # f"{str(dps) + ' x ' + '<@&757298292789870672>' if dps == None or dps > 0 else ''}"
    f"{'nothing...?' if tank and healer and dps == 0 else ''}")

  return content_var, embed_var

# ---------- Application section ----------

class ClassDropdown(ui.Select):
  def __init__(self):
    class_options = [
      SelectOption(label='Death Knight'),
      SelectOption(label='Demon Hunter'),
      SelectOption(label='Druid'),
      SelectOption(label='Evoker'),
      SelectOption(label='Hunter'),
      SelectOption(label='Mage'),
      SelectOption(label='Monk'),
      SelectOption(label='Paladin'),
      SelectOption(label='Priest'),
      SelectOption(label='Rogue'),
      SelectOption(label='Shaman'),
      SelectOption(label='Warlock'),
      SelectOption(label='Warrior')
    ]

    super().__init__(placeholder='Choose your mains class...', min_values=1, max_values=1, options=class_options)
  async def callback(self, interaction: Interaction):
    await interaction.response.send_message(self.values[0])

# Unused, can be swapped in instead of char_mainspec and char_offspec
class RoleDropdown(ui.Select):
  def __init__(self):
    class_options = [
      SelectOption(label='Tank'),
      SelectOption(label='Healer'),
      SelectOption(label='DPS')
    ]

    super().__init__(placeholder='Choose spec...', min_values=1, max_values=1, options=class_options)
  async def callback(self, interaction: Interaction):
    await interaction.response.send_message(self.values[0])

class ApplicationButton(ui.View):
  def __init__(self):
    super().__init__()

class ApplicationForm(ui.Modal):
  def __init__(self, user):
    super().__init__()
    self.user = user

  async def submit_button(self, interaction: Interaction):
    if not interaction.user == self.user:
      await interaction.response.send_message("Only the applicant can submit the application...", ephemeral=True)
    else:
      await interaction.response.send_message(
                                              "Application submitted!\n"
                                              "An officer will contact you as soon as possible.\n"
                                              "Thank you for applying!",
                                              ephemeral=True
      )
      await interaction.message.reply("MISSING IMPLEMENTATION") # TODO implement the formatting of the full application.

  # ---------- TextInputs ----------
  # Currently, modals only support 5 TextInputs per modal, meaning
  # the application would have to be done in 4-5 different modals.
  # This probably isn't the most user-friendly, and I'm parking
  # this feature for now.

  # Player information
  name = ui.TextInput(label='*OPTIONAL* Your Name', placeholder='Enter your name here...', required=False)
  age = ui.TextInput(label='*OPTIONAL* Your Age', placeholder='Enter your age here...', required=False)
  country = ui.TextInput(label='*OPTIONAL* Your Country', placeholder='Enter your country here...', required=False)

  # Character information
  char_name = ui.TextInput(label='Character Name', placeholder='Enter your main character\'s name...')
  # char_class = ClassDropdown()
  char_class = ui.TextInput(label='Character Class', placeholder='Enter your main character\'s class...')
  char_mainspec = ui.TextInput(label='Main Spec', placeholder='Enter your main spec...')
  char_offspec = ui.TextInput(label='Off Spec', placeholder='Enter your off spec...')

  # How did you find us?
  find_us = ui.TextInput(label='How did you find Belan Shi guild?', placeholder='guildsofwow.com, forums, referral, etc...')

  # Guild rules
  guild_rules = ui.TextInput(label='Have you read our guild rules and which of the rules appeal to you the most?')

  # Expectations of joining
  expectations = ui.TextInput(label='What are you expectations when joining this guild?', style=TextStyle.long)

  # Attendance of guild activities
  attend_activities = ui.TextInput(label='Are you able to attend the guild activities such as raids and mythic plus, as per our current schedule?')

  # Past notable achievements
  notable_achievements = ui.TextInput(label='From your past WoW ventures, what is your most notable achievement?', style=TextStyle.long)

  # Anything else to add
  additional = ui.TextInput(label='Anything else to add?', placeholder='We appreciate a good bee joke...', required=False, style=TextStyle.long)


@tree.command(guild=discord.Object(id=TEST_ID))
async def apply() -> None:
  raise Exception()

# ---------- Bot setup ----------
@client.event
async def on_ready() -> None:
  # tree.clear_commands(guild=None) # Should clear all phantom commands globally
  # await tree.sync()
  # await tree.sync(guild=discord.Object(id=TEST_ID)) # Syncs command tree to test server
  await tree.sync()                                 # Syncs command tree globally
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
# @client.event
# async def on_reaction_add(reaction, user):
#   message = reaction.message
#   channel = discord.utils.get(message.guild.channels, name="general")
#   if message.channel.id == channel.id:
#         print(f"User {user} reacted with {reaction} to message ID: {reaction.message.id}")
