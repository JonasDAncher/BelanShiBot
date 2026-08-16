import psycopg2
from typing import Final, Optional
import os
import logging
import asyncio
import discord
from dotenv import load_dotenv


TOKEN: Final[str] = os.getenv('POSTGRES_STRING')  # Postgres connection string


class Raid(commands.Cog):

    def get_connection():
        try:
            return psycopg2.connect(
                database="postgres",
                user="postgres",
                password="pp8wE6q9mg",
                port=42069,
            )
        except:
            return False

    con = get_connection
    if con:
        print("Success con")
    else:
        print("Sad con")