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
    embed_var = discord.Embed(title="Title", description="Desc", color=0x00ff00)
    embed_var.add_field(name="Field1", value="hi", inline=False)
    embed_var.add_field(name="Field2", value="hi2", inline=False)
    await message.channel.send(embed=embed_var)
  except Exception as e:
    print(e)

@tree.command(name='group', guild=discord.Object(id=TEST_ID))
# @app_commands.rename(dungeon_name='dungeon-name', key_level='key-level', tank='tank', healer='healer', dps='missing-dps')
async def group(
    interaction,
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
  embed_var = discord.Embed(title=f'{interaction.user} want to run a {dungeon_name} +{key_level}', description="Desc", color=0x00ff00)
  embed_var.add_field(name="TANK", value=f'{tank or False}', inline=False)
  embed_var.add_field(name="HEALER", value=f'{healer or False}', inline=False)
  embed_var.add_field(name="DPS", value=f'Missing {dps or 3} DPS', inline=False)
  await interaction.response.send_message(embed=embed_var)

@client.event
async def on_ready() -> None:
  await tree.sync(guild=discord.Object(id=TEST_ID))
  print(f'{client.user} succesfully logged in with ID: {client.user.id}')

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