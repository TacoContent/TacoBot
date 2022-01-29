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
import inspect

class StreamTeam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "streamteam.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "streamteam.__init__", f"Logger initialized with level {log_level.name}")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        try:
            _method = inspect.stack()[1][3]
            guild_id = after.guild.id
            if after.roles == before.roles:
                self.log.debug(guild_id, "streamteam.on_member_update", f"{_method}", f"roles are the same")
                return
            # get streamteam role
            streamteam_role = discord.utils.get(after.guild.roles, name="STREAM TEAM")
            if not streamteam_role:
                # log that the role was not found
                self.log.debug(guild_id, "streamteam.on_member_update", f"Stream Team Role Not Found")
                return
            # if streamteam role is not in after.roles or before.roles then return
            if streamteam_role not in after.roles and streamteam_role not in before.roles:
                self.log.debug(guild_id, "streamteam.on_member_update", f"{_method}", f"{streamteam_role.name} not in roles")
            # if streamteam role is in after.roles and not in before.roles then add to db
            elif streamteam_role in after.roles and streamteam_role not in before.roles:
                self.log.debug(guild_id, "streamteam.on_member_update", f"{after} added to STREAM TEAM")
            # if streamteam role is in before.roles and not in after.roles then remove from db
            elif streamteam_role in before.roles and streamteam_role not in after.roles:
                self.log.debug(guild_id, "streamteam.on_member_update", f"{after} removed from STREAM TEAM")


        except discord.errors.NotFound as nf:
            self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
        # finally:
        #     self.db.close()

    @commands.Cog.listener()
    async def on_ready(self):
        pass
    @commands.Cog.listener()
    async def on_disconnect(self):
        pass

    @commands.Cog.listener()
    async def on_resumed(self):
        pass

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        self.log.error(0, "streamteam.on_error", f"{str(event)}", traceback.format_exc())

def setup(bot):
    bot.add_cog(StreamTeam(bot))
