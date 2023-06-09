import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider
from .lib import tacotypes

import inspect

class JoinLeaveTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "join_leave.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        _method = inspect.stack()[0][3]
        # remove all tacos from the user
        guild_id = member.guild.id
        try:
            if member.bot:
                return

            _method = inspect.stack()[0][3]
            self.log.debug(guild_id, _method, f"{member} left the server")
            self.db.remove_all_tacos(guild_id, member.id)
            self.db.track_tacos_log(
                guildId=guild_id,
                toUserId=member.id,
                fromUserId=self.bot.user.id,
                count=0,
                reason="leaving the server",
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(tacotypes.TacoTypes.LEAVE_SERVER)
            )
            self.db.track_user_join_leave(guildId=guild_id, userId=member.id, join=False)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        _method = inspect.stack()[0][3]
        guild_id = member.guild.id
        try:
            if member.bot:
                return

            await self.discord_helper.taco_give_user(guild_id, self.bot.user, member,
                self.settings.get_string(guild_id, "taco_reason_join"),
                tacotypes.TacoTypes.JOIN_SERVER )
            self.db.track_user_join_leave(guildId=guild_id, userId=member.id, join=True)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())

async def setup(bot):
    await bot.add_cog(JoinLeaveTracker(bot))
