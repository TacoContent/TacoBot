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
import inspect

from discord.ext.commands.cooldowns import BucketType
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)

        self.SETTINGS_SECTION = "suggestions"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "init.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "init.__init__", f"Logger initialized with level {log_level.name}")

    @commands.group(aliases=["suggest"])
    async def suggestion(self, ctx):
        try:
            guild_id = 0
            if ctx.guild is not None:
                guild_id = ctx.guild.id
            else:
                # only allow suggestions in guilds
                return
            if ctx.author.bot:
                return # ignore bots

            if ctx.invoked_subcommand is None:
                pass
        except Exception as e:
            self.log.error(guild_id, "trivia", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)
    async def create_suggestion():
        pass


def setup(bot):
    bot.add_cog(Suggestions(bot))
