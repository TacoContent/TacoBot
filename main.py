import discord
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import bot.tacobot as bot

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True

tacobot = bot.TacoBot(intents=intents)
tacobot.run(DISCORD_TOKEN)
