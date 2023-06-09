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
from .lib import settings
from .lib import mongo

class JoinLeaveTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "join_leave.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            guild_id = member.guild.id
            self.db.track_user_join_leave(guildId=guild_id, userId=member.id, join=True)
        except Exception as e:
            self.log.error(0, "join_leave.on_member_join", f"Exception: {e}")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            guild_id = member.guild.id
            self.db.track_user_join_leave(guildId=guild_id, userId=member.id, join=False)
        except Exception as e:
            self.log.error(0, "join_leave.on_member_remove", f"Exception: {e}")
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(JoinLeaveTracker(bot))
