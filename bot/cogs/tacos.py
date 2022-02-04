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
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.TACO_LOG_CHANNEL_ID = 938291623056519198
        self.JOIN_COUNT = 5
        self.REACTION_COUNT = 1
        self.BOOST_COUNT = 100

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
        await self.discord_helper.sendEmbed(ctx.channel, "Help", f"I don't know how to help with this yet.", delete_after=30)
        await ctx.message.delete()

    @tacos.command()
    async def count(self, ctx):
        try:
            # get taco count for message author
            taco_count = self.db.get_tacos_count(ctx.guild.id, ctx.author.id)
            tacos_word = "taco"
            if taco_count is None:
                taco_count = 0
            if taco_count == 0 or taco_count > 1:
                tacos_word = "tacos"
            await ctx.message.delete()
            await self.discord_helper.sendEmbed(ctx.channel, "Tacos", f"{ctx.author.mention}, You have {taco_count} {tacos_word} 🌮.\n\nThis message will delete in 30 seconds.", delete_after=30)
        except Exception as e:
            self.log.error(ctx.guild.id, "tacos.get", str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.type == discord.MessageType.premium_guild_subscription:
                # add tacos to user that boosted the server
                member = message.author
                guild_id = message.guild.id
                if member.bot:
                    return
                _method = inspect.stack()[0][3]
                self.log.debug(member.guild.id, _method, f"{member} boosted the server")
                taco_count = self.db.add_tacos(guild_id, member.id, self.BOOST_COUNT)
                log_channel = await self.discord_helper.get_or_fetch_channel(self.TACO_LOG_CHANNEL_ID)

                self.log.debug(guild_id, _method, f"🌮 added {self.BOOST_COUNT} tacos to user {member.name} for boosting the server")
                if log_channel:
                    await log_channel.send(f"{member.name} has received {self.BOOST_COUNT} tacos for boosting the server, giving them {taco_count} 🌮.")

        except Exception as ex:
            self.log.error(member.guild.id, _method, str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # remove all tacos from the user
        try:
            if member.bot:
                return
            _method = inspect.stack()[0][3]
            self.log.debug(member.guild.id, _method, f"{member} left the server")
            await self.db.remove_all_tacos(member.guild.id, member.id)
        except Exception as ex:
            self.log.error(member.guild.id, _method, str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        _method = inspect.stack()[0][3]
        guild_id = member.guild.id
        self.log.info(guild_id, _method, f"{member} joined the server")
        taco_count = self.db.add_tacos(guild_id, member.id, self.JOIN_COUNT)
        log_channel = await self.discord_helper.get_or_fetch_channel(self.TACO_LOG_CHANNEL_ID)

        self.log.debug(guild_id, _method, f"🌮 added {self.JOIN_COUNT} tacos to user {member.name} for joining the server")
        if log_channel:
            await log_channel.send(f"{member.name} has received {self.JOIN_COUNT} tacos for joining the server, giving them {taco_count} 🌮.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        try:
            guild_id = payload.guild_id
            if payload.event_type != 'REACTION_ADD':
                return

            self.log.debug(guild_id, _method, f"{payload.emoji.name} added to {payload.message_id}")
            if str(payload.emoji) == '🌮':
                user = await self.discord_helper.get_or_fetch_user(payload.user_id)
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                # if the message is from a bot, or reacted by the author, ignore it
                if message.author.bot or message.author.id == user.id:
                    return
                log_channel = await self.discord_helper.get_or_fetch_channel(self.TACO_LOG_CHANNEL_ID)
                self.log.debug(guild_id, _method, f"🌮 adding taco to user {message.author.name}")
                taco_count = self.db.add_tacos(guild_id, message.author.id, self.REACTION_COUNT)
                self.log.debug(guild_id, _method, f"🌮 added taco to user {message.author.name} successfully")
                if log_channel:
                    await log_channel.send(f"{message.author.name} has received {self.REACTION_COUNT} taco from {user.name}, giving them {taco_count} 🌮.")
                # give taco giver tacos too
                self.log.debug(guild_id, _method, f"🌮 adding taco to user {user.name}")
                taco_count = self.db.add_tacos(guild_id, user.id, self.REACTION_COUNT)
                self.log.debug(guild_id, _method, f"🌮 added taco to user {user.name} successfully")
                if log_channel:
                    await log_channel.send(f"{user.name} has received {self.REACTION_COUNT} taco for giving {message.author.name} a taco, giving them {taco_count} 🌮.")

            else:
                self.log.debug(guild_id, _method, f"{payload.emoji} not a taco")
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())

    # @setup.error
    # async def info_error(self, ctx, error):
    #     _method = inspect.stack()[1][3]
    #     if isinstance(error, discord.errors.NotFound):
    #         self.log.warn(ctx.guild.id, _method , str(error), traceback.format_exc())
    #     else:
    #         self.log.error(ctx.guild.id, _method , str(error), traceback.format_exc())
    def get_string(self, guild_id, key):
        return key

def setup(bot):
    bot.add_cog(Tacos(bot))
