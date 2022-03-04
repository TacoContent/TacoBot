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
        self.log.debug(0, "restricted.__init__", "Initialized")


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
                await self.discord_helper.notify_bot_not_initialized(message, "restricted")
                return

            # get the suggestion channel ids from settings
            restricted_channel = [c for c in restricted_settings["channels"] if str(c['id']) == str(message.channel.id)]
            if restricted_channel:
                restricted_channel = restricted_channel[0]
            # if channel.id is not in restricted_channel_ids[] return
            if not restricted_channel:
                return

            silent = True
            if 'silent' in restricted_channel:
                silent = restricted_channel['silent']

            # get allowed commands from settings
            if "allowed" in restricted_channel:
                allowed = restricted_channel["allowed"]
            else:
                allowed = []
            # get denied commands from settings
            if "denied" in restricted_channel:
                denied = restricted_channel["denied"]
            else:
                denied = []
            # get the deny message from settings
            if "deny_message" in restricted_channel:
                deny_message = restricted_channel["deny_message"]
            else:
                deny_message = "That message is not allowed in this channel."

            # if message matches the allowed[] regular expressions then continue
            if not any(re.search(r, message.content) for r in allowed) or any(re.search(r, message.content) for r in denied):
                # wait
                await asyncio.sleep(0.5)
                await message.delete()

                if not silent:
                    await self.discord_helper.sendEmbed(message.channel, "Restricted", f"{message.author.mention}, {deny_message}", delete_after=20, color=0xFF0000)
        except discord.NotFound as nf:
            self.log.info(guild_id, "restricted.on_message", f"Message not found: {nf}")
        except Exception as e:
            self.log.error(guild_id, "restricted.on_message", f"{e}", traceback.format_exc())
def setup(bot):
    bot.add_cog(Restricted(bot))
