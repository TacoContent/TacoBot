# this is a helper for the carlbot suggestions

import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import re

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

import inspect

class SuggestionHelper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SUGGESTION_CHANNEL_ID = 938838459722907711
        self.CB_PREFIX = "?cb "
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "suggestions.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "suggestions.__init__", f"Logger initialized with level {log_level.name}")

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.author.bot:
                return
            if message.channel.id != self.SUGGESTION_CHANNEL_ID:
                return
            allowed_commands = "suggest|approve|consider|deny|implemented|suggestions"

            if not message.content.startswith(self.CB_PREFIX) and not bool(re.match(allowed_commands, message.content)):
                # not a suggestion command message, remove it
                await self.discord_helper.sendEmbed(message.channel, "Suggestions", f"Please only use the `{self.CB_PREFIX}suggest <MY SUGGESTION>` command in the suggestion channel.", delete_after=30)
                await message.delete()
        except Exception as e:
            self.log.error(0, "suggestions.on_message", f"{e}")
            self.log.error(0, "suggestions.on_message", f"{traceback.format_exc()}")

def setup(bot):
    bot.add_cog(SuggestionHelper(bot))
