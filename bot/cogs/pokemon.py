# this is a helper for the myuu bot

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

class Pokemon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "pokemon.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "pokemon.__init__", f"Logger initialized with level {log_level.name}")

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.author.bot:
                return

            p_settings = self.settings.get_settings(self.db, message.guild.id, "pokemon")
            if not p_settings:
                # log that we are not configured
                self.log.debug(message.guild.id, "pokemon.on_message", "Settings for pokemon is configured")
                return

            # if channel.id is not in SUGGESTION_CHANNEL_IDS[] return
            if str(message.channel.id) not in p_settings['pokemon_channel_ids']:
                print(f"{json.dumps(p_settings['pokemon_channel_ids'])}")
                self.log.debug(message.guild.id, "pokemon.on_message", f"Channel {message.channel.id} is not in the list of pokemon channels")
                return

            if message.content.startswith(p_settings['pokemon_prefix']):
                self.log.debug(message.guild.id, "pokemon.on_message", f"Message starts with {p_settings['pokemon_prefix']} so we will remove it.")
                await message.delete()

        except Exception as e:
            self.log.error(0, "pokemon.on_message", f"{e}")
            self.log.error(0, "pokemon.on_message", f"{traceback.format_exc()}")

def setup(bot):
    bot.add_cog(Pokemon(bot))
