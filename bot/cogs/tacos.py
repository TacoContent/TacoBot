import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing

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

class Tacos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(self.settings)
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "tacos.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "tacos.__init__", f"Logger initialized with level {log_level.name}")

    @commands.group()
    async def tacos(self, ctx):
        pass

    @tacos.command()
    async def help(self, ctx):
        # todo: add help command
        await self.discord_helper.sendEmbed(ctx.channel, "Help", f"I don't know how to help with this yet.", delete_after=20)
        await ctx.message.delete()
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id
        if payload.event_type != 'REACTION_ADD':
            return

        self.log.debug(guild_id, _method, f"{payload.emoji.name} added to {payload.message_id}")
        if str(payload.emoji) == '🌮':
            user = await self.get_or_fetch_user(payload.user_id)
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            # guild = self.bot.get_guild(guild_id)
            log_channel = await self.get_or_fetch_channel(938291623056519198)
            self.log.debug(guild_id, _method, f"{payload.emoji} adding taco to user {message.author.name}")
            taco_count = self.db.add_tacos(guild_id, message.author.id, 1)
            self.log.debug(guild_id, _method, f"{payload.emoji} added taco to user {message.author.name} successfully")
            if log_channel:
                self.log.debug(guild_id, _method, f"{payload.emoji} sending message to log channel")
                await log_channel.send(f"{message.author.name} has received 1 taco from {user.name}, giving them {taco_count} 🌮.")
            # await self.discord_helper.sendEmbed(reaction.message.channel, "Tacos", f"{user.mention} has been added to the tacos list.", delete_after=20)
        else:
            self.log.debug(guild_id, _method, f"{payload.emoji} not a taco")

    # @setup.error
    # async def info_error(self, ctx, error):
    #     _method = inspect.stack()[1][3]
    #     if isinstance(error, discord.errors.NotFound):
    #         self.log.warn(ctx.guild.id, _method , str(error), traceback.format_exc())
    #     else:
    #         self.log.error(ctx.guild.id, _method , str(error), traceback.format_exc())
    def get_string(self, guild_id, key):
        return key

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None

    async def get_or_fetch_user(self, userId: int):
        _method = inspect.stack()[1][3]
        try:
            if userId:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_channel(self, channelId: int):
        _method = inspect.stack()[1][3]
        try:
            if channelId:
                chan = self.bot.get_channel(channelId)
                if not chan:
                    chan = await self.bot.fetch_channel(channelId)
                return chan
            else:
                return  None
        except discord.errors.NotFound as nf:
            self.log.warn(0, _method, str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, _method, str(ex), traceback.format_exc())
            return None
def setup(bot):
    bot.add_cog(Tacos(bot))
