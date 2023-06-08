# Before: https://www.amazon.com/dp/B0042TVKZY/
# After: https://www.amazon.com/dp/B0042TVKZY/?tag=darthminos0f-20

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
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider
from .lib import tacotypes

import inspect


class MessageTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "message_track"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "message_track.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        guild_id = 0
        _method = inspect.stack()[0][3]
        try:
            # if in a DM, ignore
            if message.guild is None:
                return
            # if the message is from a bot, ignore
            if message.author.bot:
                return
            guild_id = message.guild.id

            # if message is a bot command, ignore
            # loop all command prefixes
            for prefix in await self.bot.command_prefix(message):
                if message.content.startswith(prefix):
                    return

            if self.db.is_first_message_today(guild_id, message.author.id):
                await self.give_user_first_message_tacos(guild_id, message.author.id, message.channel.id, message.id)

            # track the message in the database
            self.db.track_message(guild_id, message.author.id, message.channel.id, message.id)
        except Exception as e:
            self.log.error(guild_id, "message_track.on_message", f"{e}", traceback.format_exc())

    async def give_user_first_message_tacos(self, guild_id, user_id, channel_id, message_id):
        try:
            # create context
            # self, bot=None, author=None, guild=None, channel=None, message=None, invoked_subcommand=None, **kwargs
            # get guild from id
            guild = self.bot.get_guild(guild_id)
            # fetch member from id
            member = guild.get_member(user_id)
            # get channel
            channel = None
            message = None

            # get bot
            bot = self.bot
            ctx = self.discord_helper.create_context(
                bot=bot, guild=guild, author=member, channel=channel, message=message
            )

            # track that the user answered the question.
            self.db.track_first_message(guild_id, member.id, channel_id, message_id)

            tacos_settings = self.get_tacos_settings(guild_id)
            if not tacos_settings:
                self.log.warn(
                    guild_id,
                    "message_track.give_user_first_message_tacos",
                    f"No tacos settings found for guild {guild_id}",
                )
                return

            amount = tacos_settings.get("first_message_count", 5)

            reason_msg = self.settings.get_string(guild_id, "first_message_reason")

            await self.discord_helper.taco_give_user(
                guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.FIRST_MESSAGE, taco_amount=amount
            )

        except Exception as e:
            self.log.error(guild_id, "message_track.give_user_first_message_tacos", str(e), traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No message_track settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


async def setup(bot):
    await bot.add_cog(MessageTracker(bot))
