import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import random
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

class Trivia(commands.Cog):
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
        self.log.debug(0, "trivia.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "trivia.__init__", f"Logger initialized with level {log_level.name}")

        self.bot.loop.create_task(self.trivia_init())
    async def trivia_init(self):
        await self.bot.wait_until_ready()
        channel = await self.discord_helper.get_or_fetch_channel(935318426677825536)
        while not self.bot.is_closed:
            time = random.randint(60,300)
            chance = random.randint(1,1)
            if chance == 1:
                await self.run_trivia(channel)

            await asyncio.sleep(time)

    async def run_trivia(self, channel):
        self.log.debug(0, "trivia.run_trivia", "Starting trivia")
        await channel.send("Starting trivia")

def setup(bot):
    bot.add_cog(Trivia(bot))
