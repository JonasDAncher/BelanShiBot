from pickle import FALSE
from tkinter.ttk import Label
from typing import Final, Optional
import os

import discord
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, ui, Interaction

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
GUILD_ID: Final[int] = 368116240276914176 # Belan Shi Discord ID
TEST_ID: Final[int] = 489890364090744892 # Test Server Discord ID

intents = Intents.default()
intents.message_content = True
intents.reactions = True
client = Client(intents=intents)
tree = app_commands.CommandTree(client)

class RoleButtons(ui.View):
    def __init__(self, tank, healer, dps):
      super().__init__()
      self.tank = tank
      self.healer = healer
      self.dps = dps
      self.add_buttons()

    def add_buttons(self):
      tank_button = ui.Button(emoji='🛡', disabled=self.tank)
      healer_button = ui.Button(emoji='💚', disabled=self.healer)
      dps_button = ui.Button(emoji='⚔️', disabled=self.dps <= 0)

      async def tankbutton(interaction: discord.Interaction):
        await interaction.response.send_message("Test buttons galore", ephemeral=True)

      async def healerbutton(interaction: discord.Interaction):
        await interaction.response.send_message("Test buttons galore", ephemeral=True)

      async def dpsbutton(interaction: discord.Interaction):
        await interaction.response.send_message("Test buttons galore", ephemeral=True)

      tank_button.callback = tankbutton
      healer_button.callback = healerbutton
      dps_button.callback = dpsbutton

      self.add_item(tank_button)
      self.add_item(healer_button)
      self.add_item(dps_button)


@tree.command(guild=discord.Object(id=TEST_ID))
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f'Hi, {interaction.user.mention}')

def format_dps(dps: int):
  if dps == 1:
    return f"⚔️ # 1: ***Unknown***\n⚔️ # 2: ***Unknown***\n⚔️ # 3: *Open*\n"
  elif dps == 2:
    return f"⚔️ # 1: ***Unknown***\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  elif dps == 3:
    return f"⚔️ # 1: *Open*\n⚔️ # 2: *Open*\n⚔️ # 3: *Open*\n"
  return None

@tree.command(guild=discord.Object(id=TEST_ID))
@app_commands.rename(dungeon_name='dungeon-name', key_level='key-level', tank='tank', healer='healer', dps='missing-dps')
async def key(
    interaction: discord.Interaction,
    dungeon_name: str,
    key_level: int,
    tank: Optional[bool],
    healer: Optional[bool],
    dps: Optional[int] = 3):
  """Creates a group people can join
  :param dungeon_name: Name of the dungeon
  :param key_level: Level of the key
  :param tank: Have tank?
  :param healer: Have healer?
  :param dps: How many dps is missing?
  """
  print(f"{interaction.user.name} ({interaction.user.id}) used /group with parameters: dungeon_name={dungeon_name}, key_level={key_level}, tank={tank}, healer={healer}, dps={dps}")
  if dps<=-1:
    await interaction.response.send_message(content="Illegal argument: `dps` must be a positive integer", ephemeral=True)
    return
  else:
    embed_var = discord.Embed(title=f"{interaction.user.nick if not 'None' else interaction.user.name} want to run a {dungeon_name} +{key_level}", description="Desc", color= 0x00ff00 if 0<=key_level<5 else 0xffff00 if 5<=key_level<=7 else 0xff0000)
    embed_var.add_field(name="TANK", value=f"{'~~🛡 Tank open~~ SPOT TAKEN' if tank or None else '🛡 Tank open'}", inline=False)
    embed_var.add_field(name="HEALER", value=f"{'~~💚 Healer open~~ SPOT TAKEN' if healer or None else '💚 Healer open'}", inline=False)
    # embed_var.add_field(name="DPS", value=f"{'~~⚔️ Missing 0 x DPS~~ FULL' if dps<1 else f'⚔️ Missing {dps} x DPS'}", inline=False)
    embed_var.add_field(name="DPS", value=format_dps(dps), inline=False)
    content_var = (f"{interaction.user.mention} want to run a {dungeon_name} +{key_level}!"
                   f"\nThey need "
                    f"{'<@&805437880821612604> ' if not tank else ''}"
                    f"{'<@&1275027330045055048> ' if not healer else ''}"
                    f"{str(dps)+' x '+'<@&757298292789870672>' if dps==None or dps>0 else ''}"
                    f"{'nothing...?' if tank and healer and dps==0 else ''}")
    print(embed_var.fields)

    await interaction.response.send_message(content=content_var, embed=embed_var, view=RoleButtons(tank, healer, dps))

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



