from pickle import FALSE
from typing import Final, Optional
import os

import discord
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands

from responses import get_response

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
GUILD_ID: Final[int] = 368116240276914176 # Belan Shi Discord ID
TEST_ID: Final[int] = 489890364090744892 # Test Server Discord ID
# print(TOKEN)

intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)
tree = app_commands.CommandTree(client)

async def send_message(message: Message, user_message: str) -> None:
  if not user_message:
    print('Bad message, empty, missing intents')
    return

  if is_private := user_message[0] == '?':
    user_message = user_message[1:]

  try:
    embed_var = discord.Embed(title=f"interaction.user want to run a dungeon_name +key_level", description="Desc",
                              color=0x00ff00)
    embed_var.add_field(name="TANK", value=f"tank or False", inline=False)
    embed_var.add_field(name="HEALER", value=f"healer or False", inline=False)
    embed_var.add_field(name="DPS", value=f"Missing dps or 3 DPS", inline=False)
    await message.channel.send(embed=embed_var)
  except Exception as e:
    print(e)

@tree.command(guild=discord.Object(id=TEST_ID))
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f'Hi, {interaction.user.mention}')

# @app_commands.rename(dungeon_name='dungeon-name', key_level='key-level', tank='tank', healer='healer', dps='missing-dps')
@tree.command(guild=discord.Object(id=TEST_ID))
async def group(
    interaction: discord.Interaction,
    dungeon_name: str,
    key_level: int,
    tank: Optional[bool],
    healer: Optional[bool],
    dps: Optional[int]):
  """Creates a group people can join
  :param dungeon_name: Name of the dungeon
  :param key_level: Level of the key
  :param tank: Have tank?
  :param healer: Have healer?
  :param dps: How many dps is missing?
  """
  print(f"{interaction.user.name} ({interaction.user.id}) used /group with parameters: dungeon_name={dungeon_name}, key_level={key_level}, tank={tank}, healer={healer}, dps={dps}")
  embed_var = discord.Embed(title=f"{interaction.user.nick if not 'None' else interaction.user.name} want to run a {dungeon_name} +{key_level}", description="Desc", color= 0x00ff00 if 0<key_level<4 else 0xffff00 if 4<key_level<6 else 0xff0000)
  embed_var.add_field(name="TANK", value=f"{'~~🛡 Tank open~~ SPOT TAKEN' if not tank or None else '🛡 Tank open'}", inline=False)
  embed_var.add_field(name="HEALER", value=f"{'~~💚 Healer open~~ SPOT TAKEN' if not healer or None else '💚 Healer open'}", inline=False)
  embed_var.add_field(name="DPS", value=f"⚔️ Missing {dps or 3} x DPS", inline=False)
  await interaction.response.send_message(content=f"{interaction.user.mention} want to run a {dungeon_name} +{key_level}!"
                                                  f"\nThey need {'<@&805437880821612604> ' if tank else ''}"
                                                  f"{'<@&1275027330045055048> ' if healer else ''}"
                                                  f"{dps} x {'<@&757298292789870672>' if not dps == None else ''}", embed=embed_var)

@client.event
async def on_ready() -> None:
  await tree.sync(guild=discord.Object(id=TEST_ID))
  print(f'{client.user} successfully logged in with ID: {client.user.id}')

@client.event
async def on_message(message: Message) -> None:
  if message.author == client.user:
    return

  username = str(message.author)
  user_message = str(message.content)
  channel = str(message.channel)

  print(f'[{channel}] {username}: {user_message}')
  await send_message(message, user_message)

def main() -> None:
  client.run(token=TOKEN)

if __name__ == '__main__':
  main()