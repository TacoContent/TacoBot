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
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.SETTINGS_SECTION = "account_link"
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.db = mongo.MongoDatabase()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.invites = {}

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.command()
    @commands.guild_only()
    async def link(self, ctx, *, code: typing.Union[str,None] = None):
        _method = inspect.stack()[0][3]
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
                        await ctx.author.send(
                            self.settings.get_string(guild_id, "account_link_success_message", code=code)
                        )
                    except discord.Forbidden:
                        await ctx.channel.send(
                            f'{ctx.author.mention}, {self.settings.get_string(guildId=guild_id, key="account_link_success_message", code=code)}',
                            delete_after=10)
                else:
                    try:
                        await ctx.author.send(self.settings.get_string(guild_id, key="account_link_unknown_code_message"))
                    except discord.Forbidden:
                        await ctx.channel.send(f'{ctx.author.mention}, {self.settings.get_string(guildId=guild_id, key="account_link_unknown_code_message")}', delete_after=10)
            except ValueError as ve:
                try:
                    await ctx.author.send(f"{ve}")
                except discord.Forbidden:
                    await ctx.channel.send(f"{ctx.author.mention}, {ve}", delete_after=10)
            except Exception as e:
                self.log.error(guild_id, f"{self._module}.{_method}", str(e), traceback.format_exc())
                await self.discord_helper.notify_of_error(ctx)
        else:
            try:
                # generate code
                code = utils.get_random_string(length=6)
                # save code to db
                result = self.db.set_twitch_discord_link_code(ctx.author.id, code)
                notice_message = self.settings.get_string(guild_id, "account_link_notice_message", code=code)
                if result:
                    try:
                        await ctx.author.send(notice_message)
                    except discord.Forbidden:
                        await ctx.channel.send(f"{ctx.author.mention}, {notice_message}", delete_after=10)
                else:
                    try:
                        await ctx.author.send(self.settings.get_string(guild_id, "account_link_save_error_message"))
                    except discord.Forbidden:
                        await ctx.channel.send(f'{ctx.author.mention}, {self.settings.get_string(guildId=guild_id, key="account_link_save_error_message")}', delete_after=10)
            except ValueError as ver:
                try:
                    await ctx.author.send(f"{ve}")
                except discord.Forbidden:
                    await ctx.channel.send(f"{ctx.author.mention}, {ve}", delete_after=10)
            except Exception as e:
                self.log.error(guild_id, f"{self._module}.{_method}", str(e), traceback.format_exc())
                await self.discord_helper.notify_of_error(ctx)

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings

async def setup(bot):
    await bot.add_cog(AccountLink(bot))
