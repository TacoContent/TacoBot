import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import math
import datetime

import inspect

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider
from .lib import tacotypes

class GuildTrack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "guild_track"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "guild_track.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        try:
            if guild is None:
                return

            self.log.debug(guild.id, "guild_track.on_guild_available", f"Guild ({guild.id}) is available")
            self.db.track_guild(guild=guild)
        except Exception as e:
            self.log.error(guild.id, "guild_track.on_guild_available", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        try:
            if after is None:
                return

            self.log.debug(before.id, "guild_track.on_guild_update", f"Guild ({before.id}) is updated")
            self.db.track_guild(guild=after)
        except Exception as e:
            self.log.error(before.id, "guild_track.on_guild_update", f"{e}", traceback.format_exc())


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
    await bot.add_cog(GuildTrack(bot))
