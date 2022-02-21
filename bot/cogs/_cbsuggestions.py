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
        self.SETTINGS_SECTION = "suggestions"


        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "cbsuggestions.__init__", "Initialized")

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


            # get the suggestion settings from settings
            suggestion_settings = self.settings.get_settings(self.db, message.guild.id, self.SETTINGS_SECTION)
            if not suggestion_settings:
                # raise exception if there are no suggestion settings
                self.log.debug(guild_id, "cbsuggestions.on_message", f"No suggestion settings found for guild {guild_id}")
                raise Exception("No suggestion settings found")

            # get the suggestion channel ids from settings
            suggestion_channel_ids = suggestion_settings["suggestion_channel_ids"]
            # if channel.id is not in SUGGESTION_CHANNEL_IDS[] return
            if str(message.channel.id) not in suggestion_channel_ids:
                return

            # get allowed commands from settings
            allowed_commands = suggestion_settings["allowed_commands"]
            # get cb prefix from settings
            cb_prefix = suggestion_settings["cb_prefix"]

            if not message.content.startswith(cb_prefix) and not bool(re.match(allowed_commands, message.content)):
                # not a suggestion command message, remove it
                await self.discord_helper.sendEmbed(message.channel, "Suggestions", f"Please only use the `{cb_prefix}suggest <MY SUGGESTION>` command in the suggestion channel.", delete_after=30)
                await message.delete()
            else:
                # lets give them tacos if they created a suggestion
                if message.content.startswith(cb_prefix):

                    if bool(re.match(f'^\?cb\s+suggest\s(.+)?$', message.content)):
                        taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
                        if not taco_settings:
                            # raise exception if there are no tacos settings
                            raise Exception("No tacos settings found")
                        # get the suggestion taco count
                        taco_suggest_amount = taco_settings["suggest_count"]

                        taco_word = "taco"
                        if taco_suggest_amount != 1:
                            taco_word = "tacos"
                        # add the tacos to the user for suggestion
                        taco_count = self.db.add_tacos(guild_id, message.author.id, taco_suggest_amount)
                        # log the tacos suggestion
                        await self.discord_helper.tacos_log(guild_id, message.author, self.bot.user, taco_suggest_amount, taco_count, "creating a suggestion")
                        # thank them for the suggestion
                        await self.discord_helper.sendEmbed(message.channel, "Suggestions", f"{message.author.mention}, Thank you for the suggestion! We will look into it as soon as possible.\n\nI have given you {taco_suggest_amount} {taco_word}🌮.", delete_after=10)
        except Exception as e:
            self.log.error(guild_id, "cbsuggestions.on_message", f"{e}")
            self.log.error(guild_id, "cbsuggestions.on_message", f"{traceback.format_exc()}")

def setup(bot):
    bot.add_cog(SuggestionHelper(bot))
