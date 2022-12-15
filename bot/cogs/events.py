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

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.SETTINGS_SECTION = "tacobot"
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "events.__init__", "Initialized")


    @commands.Cog.listener()
    async def on_ready(self):
        self.log.debug(0, "events.on_ready", f"Logged in as {self.bot.user.name}:{self.bot.user.id}")
        # TODO: load this from the database
        self.log.debug(0, "events.on_ready", f"Setting Bot Presence '🌮 Taco; Not Just For Tuesday's 🌮'")
        await self.bot.change_presence(activity=discord.Game(name="🌮 Taco; Not Just For Tuesday's 🌮"))

    @commands.Cog.listener()
    async def on_disconnect(self):
        self.log.debug(0, "events.on_disconnect", f"Bot Disconnected")

    @commands.Cog.listener()
    async def on_resumed(self):
        self.log.debug(0, "events.on_resumed", f"Bot Session Resumed")

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        self.log.error(0, "events.on_error", f"{str(event)}", traceback.format_exc())


async def setup(bot):
    await bot.add_cog(Events(bot))
