import discord
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import bot.tacobot as bot


tacobot = bot.TacoBot(intents=discord.Intents.all())

