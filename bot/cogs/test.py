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
import datetime

import inspect

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import tacotypes

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "test"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "test.__init__", "Initialized")

    @commands.group()
    async def test(self, ctx):
        pass

    @test.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def msg(self, ctx):
        guild_id = ctx.guild.id
        channel = ctx.channel
        await ctx.message.delete()

        await self.discord_helper.send_embed(
            channel,
            "Test",
            "This is a test message",
            author=ctx.author,
            fields=[
                {
                    "name": "Field 1",
                    "value": "Value 1",
                },
                {
                    "name": "Field 2",
                    "value": "Value 2",
                },
                {
                    "name": "Field 3",
                    "value": "Value 3",
                },
            ],
            delete_after=5
        )

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

async def setup(bot):
    await bot.add_cog(TestCog(bot))
