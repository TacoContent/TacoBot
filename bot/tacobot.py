import discord
import math
import asyncio
import aiohttp
import json
from discord.ext import commands

from random import randint
import traceback
import sqlite3
import sys
import os
import glob
import typing
import inspect

from .cogs.lib import utils
from .cogs.lib import settings
# from .cogs.lib import sqlite
from .cogs.lib import mongo
from .cogs.lib import logger
from .cogs.lib import loglevel
from .cogs.lib import dbprovider
from discord_slash import SlashCommand

class TacoBot():
    DISCORD_TOKEN = os.environ['DISCORD_TOKEN']

    def __init__(self):
        self.settings = settings.Settings()
        print(f"APP VERSION: {self.settings.APP_VERSION}")
        self.client = discord.Client()

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        self.initDB()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "voice.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "voice.__init__", f"Logger initialized with level {log_level.name}")

        self.bot = commands.Bot(
            command_prefix=self.get_prefix,
            case_insensitive=True,
            intents=discord.Intents.all()
        )
        self.bot.remove_command("help")

        # cogs that dont start with an underscore are loaded
        cogs = [ f"bot.cogs.{os.path.splitext(f)[0]}" for f in os.listdir("bot/cogs") if f.endswith(".py") and not f.startswith("_") ]

        for extension in cogs:
            try:
                self.bot.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

        slash = SlashCommand(self.bot, override_type = True, sync_commands = True)

        self.bot.run(self.DISCORD_TOKEN)

    def initDB(self):
        pass

    def get_prefix(self, client, message):
        try:
            _method = inspect.stack()[0][3]
            # default prefixes
            # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
            prefixes = ['.taco ', '?taco ', '!taco ']
            # get the prefix for the guild.
            if message.guild:
                guild_id = message.guild.id
                # get settings from db
                settings = self.settings.get_settings(self.db, guild_id, "tacobot")
                if not settings:
                    raise Exception("No bot settings found")
                prefixes = settings['command_prefixes']
                # # log the prefixes that we are launching with for this guild
                # self.log.debug(0, _method, f"Prefixes for guild {message.guild.name} are {prefixes}")

            elif not message.guild:
                # get the prefix for the DM using 0 for the guild_id
                settings = self.settings.get_settings(self.db, 0, "tacobot")
                if not settings:
                    raise Exception("No bot settings found")
                prefixes = settings['command_prefixes']
                # # log the prefixes that we are launching with for DMs
                # self.log.debug(0, _method, f"Prefixes for DM are {prefixes}")

            # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
            # Do `return prefixes` if you don't want to allow mentions instead of prefix.
            return commands.when_mentioned_or(*prefixes)(client, message)
        except Exception as e:
            self.log.error(0, _method, f"Failed to get prefixes: {e}")
            return commands.when_mentioned_or(*prefixes)(client, message)
