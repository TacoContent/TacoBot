# this is for restricted channels that only allow specific commands in chat.
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

class Restricted(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "restricted"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "restricted.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "restricted.__init__", f"Logger initialized with level {log_level.name}")


    @commands.Cog.listener()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        try:
            # if in a DM, ignore
            if message.guild is None:
                return
            # if the message is from a bot, ignore
            if message.author.bot:
                return

            guild_id = message.guild.id

            # {
            #   channels: [
            #   {
            #       id: "",
            #       allowed: ["", ""],
            #       denied: ["", ""],
            #       deny_message: "",
            #   ]
            # }

            # get the suggestion settings from settings
            restricted_settings = self.settings.get_settings(self.db, message.guild.id, self.SETTINGS_SECTION)
            if not restricted_settings:
                # raise exception if there are no suggestion settings
                self.log.debug(guild_id, "restricted.on_message", f"No suggestion settings found for guild {guild_id}")
                self.discord_helper.notify_bot_not_initialized(message, "restricted")
                return

            # get the suggestion channel ids from settings
            restricted_channel = [c for c in restricted_settings["channels"] if str(c['id']) == str(message.channel.id)]
            if restricted_channel:
                restricted_channel = restricted_channel[0]
            # if channel.id is not in restricted_channel_ids[] return
            if not restricted_channel:
                return

            # get allowed commands from settings
            allowed = restricted_channel["allowed"]
            # if message matches the allowed[] regular expressions then continue
            if not any(re.search(r, message.content) for r in allowed):
                await self.discord_helper.sendEmbed(message.channel, "Restricted", f"{message.author.mention}, {restricted_channel['deny_message']}", delete_after=30)
                await message.delete()

        except Exception as e:
            self.log.error(guild_id, "restricted.on_message", f"{e}")
            self.log.error(guild_id, "restricted.on_message", f"{traceback.format_exc()}")
def setup(bot):
    bot.add_cog(Restricted(bot))
