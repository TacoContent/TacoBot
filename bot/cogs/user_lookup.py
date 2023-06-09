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
from .lib import dbprovider
from .lib import tacotypes

class UserLookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "user_lookup"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "user_lookup.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        try:
            if guild is None:
                return
            # pull this from the settings and see if we should do the import of all users

            enabled = False
            cog_settings = self.get_cog_settings(guild.id)
            if cog_settings is not None:
                enabled = cog_settings.get("full_import_enabled", False)

            if not enabled:
                return

            self.log.debug(guild.id, "user_lookup.on_guild_available", f"Guild {guild.id} is available")
            for member in guild.members:
                self.log.debug(guild.id, "user_lookup.on_guild_available", f"Tracking user {member.name} in guild {guild.name}")
                avatar_url: typing.Union[str,None] = member.avatar.url if member.avatar is not None else None

                self.db.track_user(guild.id, member.id, member.name, member.discriminator, avatar_url, member.display_name, member.created_at, member.bot, member.system)
        except Exception as e:
            self.log.error(guild.id, "user_lookup.on_guild_available", f"{e}", traceback.format_exc())

    # on events, get the user id and username and store it in the database
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            if member is None or member.guild is None:
                return
            self.log.debug(member.guild.id, "user_lookup.on_member_join", f"User {member.id} joined guild {member.guild.id}")
            self.db.track_user(member.guild.id, member.id, member.name, member.discriminator, member.avatar.url, member.display_name, member.created_at, member.bot, member.system)
        except Exception as e:
            self.log.error(member.guild.id, "user_lookup.on_member_join", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        try:
            if after is None or after.guild is None:
                return
            self.log.debug(after.guild.id, "user_lookup.on_member_update", f"User {after.id} updated in guild {after.guild.id}")
            self.db.track_user(after.guild.id, after.id, after.name, after.discriminator, after.avatar.url, after.display_name, after.created_at, after.bot, after.system)
        except Exception as e:
            self.log.error(after.guild.id, "user_lookup.on_member_update", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message is None or message.guild is None:
                return
            member = message.author
            self.db.track_user(message.guild.id, member.id, member.name, member.discriminator, member.avatar.url, member.display_name, member.created_at, member.bot, member.system)
        except Exception as e:
            self.log.error(message.guild.id, "user_lookup.on_message", f"{e}", traceback.format_exc())


    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No wdyctw settings found for guild {guildId}")
        return cog_settings

async def setup(bot):
    await bot.add_cog(UserLookup(bot))
