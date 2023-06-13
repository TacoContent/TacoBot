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
import inspect

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import tacotypes

class Events(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.SETTINGS_SECTION = "tacobot"
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.db = mongo.MongoDatabase()
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_ready(self):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{_method}", f"Logged in as {self.bot.user.name}:{self.bot.user.id}")
        # TODO: load this from the database
        self.log.debug(0, f"{self._module}.{_method}", f"Setting Bot Presence '🌮 Taco; Not Just For Tuesday's 🌮'")
        await self.bot.change_presence(activity=discord.Game(name="🌮 Taco; Not Just For Tuesday's 🌮"))

        self.db.migrate_game_keys()
        self.db.migrate_minecraft_whitelist()


    @commands.Cog.listener()
    async def on_guild_available(self, guild):

        # for user in guild.members:
        #     if user.bot or user.system:
        #         continue
        #     self.db.migrate_user_join(guildId=guild.id, userId=user.id)

        pass

    @commands.Cog.listener()
    async def on_disconnect(self):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{_method}", f"Bot Disconnected")

    @commands.Cog.listener()
    async def on_resumed(self):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{_method}", f"Bot Session Resumed")

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        _method = inspect.stack()[0][3]
        self.log.error(0, f"{self._module}.{_method}", f"{str(event)}", traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings

async def setup(bot):
    await bot.add_cog(Events(bot))
