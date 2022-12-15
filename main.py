import discord
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import bot.tacobot as bot

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

tacobot = bot.TacoBot(intents=discord.Intents.all())
tacobot.run(DISCORD_TOKEN)
