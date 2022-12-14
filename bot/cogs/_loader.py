import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sqlite3
import sys
import os
import glob
import typing
from .lib import settings
from .lib import logger
from .lib import loglevel

class CogLoader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "cog_loader.__init__", "Initialized")


    @commands.Cog.listener()
    async def on_ready(self):

      # cogs that dont start with an underscore are loaded
      cogs = [
          f"bot.cogs.{os.path.splitext(f)[0]}"
          for f in os.listdir("bot/cogs")
          if f.endswith(".py") and not f.startswith("_")
      ]

      for extension in cogs:
          try:
              await self.bot.load_extension(extension)
          except Exception as e:
              print(f"Failed to load extension {extension}.", file=sys.stderr)
              traceback.print_exc()

def setup(bot):
    bot.add_cog(CogLoader(bot))
