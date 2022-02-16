# this cog will DM the user if they have not yet told the bot what their twitch name is if they interact with the bot.

from ctypes import Union
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
import collections

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


class TwitchInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "twitchinfo"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "twitchinfo.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "twitchinfo.__init__", f"Logger initialized with level {log_level.name}")

    @commands.Cog.listener()
    async def on_message(self, message):
        pass

    @commands.group()
    async def twitch(self, ctx):
        pass

    @twitch.command()
    async def help(self, ctx):
        # todo: add help command
        await self.discord_helper.sendEmbed(ctx.channel, "Help", f"I don't know how to help with this yet.", delete_after=30)
        # only delete if the message is in a guild channel
        if ctx.guild:
            await ctx.message.delete()


    @twitch.command()
    async def get(self, ctx, member: typing.Union[discord.Member, discord.User] = None):
        if member is None:
            member = ctx.author
            who = "you"
        else:
            who = f"{member.name}#{member.discriminator}"

        if member.bot:
            return
        guild_id = 0
        channel = ctx.author
        if ctx.guild:
            channel = ctx.channel
            guild_id = ctx.guild.id
            await ctx.message.delete()

        ctx_dict = {"bot": self.bot, "author": ctx.author, "guild": None, "channel": None}
        alt_ctx = collections.namedtuple("Context", ctx_dict.keys())(*ctx_dict.values())

        twitch_name = None
        twitch_info = self.db.get_user_twitch_info(member.id)
        if twitch_info is None:
            twitch_name = await self.discord_helper.ask_text(alt_ctx, "Twitch Name", "You have not yet told me your twitch name, please respond with your twitch name.", 60)
            if not twitch_name is None:
                self.db.set_user_twitch_info(ctx.author.id, None, twitch_name.lower().strip())
        else:
            twitch_name = twitch_info['twitch_name']
        if not twitch_name is None:
            await self.discord_helper.sendEmbed(ctx.author, "Twitch Name", f"The Twitch name for {who} has been set to `{twitch_name}`.\n\nIf the twitch name changes in the future, you can use `.taco twitch set` in a discord channel, or `.twitch set` in the DM with me.", color=0x00ff00)


    @twitch.command()
    async def set(self, ctx, twitch_name: str = None):
        try:
            _method = inspect.stack()[0][3]
            guild_id = 0
            channel = ctx.author
            if ctx.guild:
                guild_id = ctx.guild.id
                channel = ctx.channel
                await ctx.message.delete()

            if twitch_name is None:
                twitch_name = await self.discord_helper.ask_text(ctx, "Twitch Name", "You asked to set your twitch username, please respond with your twitch username.", 60)
            self.log.debug(0, _method, f"{ctx.author} requested to set twitch name {twitch_name}")
            self.db.set_user_twitch_info(ctx.author.id, None, twitch_name.lower().strip())
            await self.discord_helper.sendEmbed(channel, "Success", f"Your Twitch name has been set to {twitch_name}.\n\nIf you change your twitch name in the future, you can use `.taco twitch set` in a discord channel, or `.twitch set` in the DM with me.", color=0x00ff00, delete_after=30)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

def setup(bot):
    bot.add_cog(TwitchInfo(bot))
