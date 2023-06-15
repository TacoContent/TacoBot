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
from .lib.system_actions import SystemActions

class NewAccountCheck(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(self.bot)
        self.SETTINGS_SECTION = "account_age_check"
        self.MINIMUM_ACCOUNT_AGE = 30 # days
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.group(name="new-account")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def new_account_check(self, ctx, *args) -> None:
        pass

    @new_account_check.command(name="set-minimum-age", aliases=["set-min-age", "set-min", "sma"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_minimum_account_age(self, ctx, minimum_age: int) -> None:
        """Set the minimum account age in days"""
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            self.db.set_setting(guildId=guild_id, name=self.SETTINGS_SECTION, key="minimum_account_age", value=minimum_age)
            self.db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.MINIMUM_ACCOUNT_AGE_SET,
                data={
                    "minimum_age": str(minimum_age),
                    "set_by": str(ctx.author.id)
                }
            )
            await self.discord_helper.send_embed(
                channel=ctx.channel,
                title="Minimum account age set",
                message=f"Minimum account age: {minimum_age} days\nSet by: {ctx.author.mention}",
                delete_after=15
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{str(e)}", traceback.format_exc())

    @new_account_check.command(name="whitelist-add")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def whitelist_add(self, ctx, user_id: int) -> None:
        """Add a user to the whitelist to allow them to join if their account is newer than the minimum account age"""
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            self.db.add_user_to_join_whitelist(guild_id=guild_id, user_id=user_id, added_by=ctx.author.id)
            self.db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.JOIN_WHITELIST_ADD,
                data={
                    "user_id": str(user_id),
                    "added_by": str(ctx.author.id)
                }
            )
            await self.discord_helper.send_embed(
                channel=ctx.channel,
                title="User added to join whitelist",
                message=f"User ID: {user_id}\nAdded by: {ctx.author.mention}",
                delete_after=15
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{str(e)}", traceback.format_exc())



    @new_account_check.command(name="whitelist-remove")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def whitelist_remove(self, ctx, user_id: int) -> None:
        """Remove a user from the join whitelist"""
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            self.db.remove_user_from_join_whitelist(guild_id=guild_id, user_id=user_id)
            self.db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.JOIN_WHITELIST_REMOVE,
                data={
                    "user_id": str(user_id),
                    "removed_by": str(ctx.author.id)
                }
            )
            await self.discord_helper.send_embed(
                channel=ctx.channel,
                title="User removed from join whitelist",
                message=f"User ID: {user_id}\nRemoved by: {ctx.author.mention}",
                delete_after=15
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{str(e)}", traceback.format_exc())


    @commands.Cog.listener()
    async def on_ready(self) -> None:
        pass
        # self.MINIMUM_ACCOUNT_AGE = self.settings.get_setting(self.SETTINGS_SECTION, "minimum_account_age", 30)
    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs) -> None:
        _method = inspect.stack()[0][3]
        self.log.error(0, f"{self._module}.{_method}", f"{str(event)}", traceback.format_exc())


    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        guild_id = member.guild.id
        _method = inspect.stack()[0][3]
        try:
            # check if the member is in the white list
            whitelist = self.db.get_user_join_whitelist(guild_id=guild_id)

            # if they are in the whitelist, let them in
            if member.id in [x["user_id"] for x in whitelist]:
                return

            self.log.debug(guild_id, f"{self._module}.{_method}", f"Member {utils.get_user_display_name(member)} joined {member.guild.name}")
            # check if the member has an account that is newer than the threshold
            member_created = member.created_at.timestamp()
            now = datetime.datetime.now().timestamp()
            age = now - member_created
            age_days = math.floor(age / 86400)
            cog_settings = self.get_cog_settings(guildId=guild_id)
            minimum_account_age = cog_settings.get("minimum_account_age", self.MINIMUM_ACCOUNT_AGE)
            if age_days < minimum_account_age:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"Member {utils.get_user_display_name(member)} (ID: {member.id}) account age ({age_days} days) is less than {minimum_account_age} days.")
                message = f"New Account: account age ({age_days} days) is less than required minimum of {minimum_account_age} days."
                self.db.track_system_action(guild_id=guild_id, action=SystemActions.NEW_ACCOUNT_KICK, data={ "user_id": str(member.id), "reason": message, "account_age": age_days})
                # kick the member
                await member.kick(reason=message)
            return
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", str(e), traceback.format_exc())

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
    await bot.add_cog(NewAccountCheck(bot))
