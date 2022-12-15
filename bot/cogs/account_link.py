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

from discord.ext.commands.cooldowns import BucketType
from interactions import ComponentContext
# from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
# from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure
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

class AccountLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.db = mongo.MongoDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.invites = {}

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "account_link.__init__", "Initialized")

    @commands.command()
    @commands.guild_only()
    async def link(self, ctx, *, code: str = None):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
            await ctx.message.delete()

        if code:
            try:
                result = self.db.link_twitch_to_discord_from_code(ctx.author.id, code)
                if result:
                    # try DM, if that fails, use the channel that it originated in
                    try:
                        await ctx.author.send(f"I used the code `{code}` to link your discord account to your twitch account. Thank you!")
                    except discord.Forbidden:
                        await ctx.channel.send(f"{ctx.author.mention}, I used the code `{code}` to link your discord account to your twitch account. Thank you!", delete_after=10)
                else:
                    try:
                        await ctx.author.send(f"I couldn't find a verification code with that value. Please try again.")
                    except discord.Forbidden:
                        await ctx.channel.send(f"{ctx.author.mention}, I couldn't find a verification code with that value. Please try again.", delete_after=10)
            except ValueError as ve:
                try:
                    await ctx.author.send(f"{ve}")
                except discord.Forbidden:
                    await ctx.channel.send(f"{ctx.author.mention}, {ve}", delete_after=10)
            except Exception as e:
                self.log.error(guild_id, "account_link.link", str(e), traceback.format_exc())
                await self.discord_helper.notify_of_error(ctx)
        else:
            try:
                # generate code
                code = utils.get_random_string(length=6)
                # save code to db
                result = self.db.set_twitch_discord_link_code(ctx.author.id, code)
                notice_message = f"I've generated a verification code for you. Please use `!taco link {code}` in <https://www.twitch.tv/ourtaco> or <https://www.twitch.tv/ourtacobot> chat to link your discord account to your twitch account."
                if result:
                    try:
                        await ctx.author.send(notice_message)
                    except discord.Forbidden:
                        await ctx.channel.send(f"{ctx.author.mention}, {notice_message}", delete_after=10)
                else:
                    try:
                        await ctx.author.send("I couldn't save your code. Please try again.")
                    except discord.Forbidden:
                        await ctx.channel.send(f"{ctx.author.mention}, I couldn't save your code. Please try again.", delete_after=10)
            except ValueError as ver:
                try:
                    await ctx.author.send(f"{ve}")
                except discord.Forbidden:
                    await ctx.channel.send(f"{ctx.author.mention}, {ve}", delete_after=10)
            except Exception as e:
                self.log.error(guild_id, "account_link.link", str(e), traceback.format_exc())
                await self.discord_helper.notify_of_error(ctx)


async def setup(bot):
    await bot.add_cog(AccountLink(bot))
