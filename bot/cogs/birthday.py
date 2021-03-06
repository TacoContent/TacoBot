import json
from random import random
from urllib import parse, request
import discord
import pytz
import datetime
from discord.ext import commands
import asyncio
import traceback
import sys
import os
import glob
import typing
import math
import re
import uuid

from discord.ext.commands.cooldowns import BucketType
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
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

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.SETTINGS_SECTION = "birthday"
        self.discord_helper = discordhelper.DiscordHelper(bot)
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "birthday.__init__", "Initialized")

    @commands.group(name='birthday', aliases=['bday'])
    @commands.guild_only()
    async def birthday(self, ctx):
        if ctx.invoked_subcommand is not None:
            return

        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()
            month = None
            day = None
            _ctx = ctx
            out_channel = ctx.author
            try:
                _ctx = self.discord_helper.create_context(self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild)
                month = await self.discord_helper.ask_number(_ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_month_question"),
                    1, 12, timeout=60)
                _ctx = self.discord_helper.create_context(self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild)
                day = await self.discord_helper.ask_number(_ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_day_question"),
                    1, 31, timeout=60)
            except discord.Forbidden:
                self.log.info(guild_id, "birthday.birthday", "Forbidden", traceback.format_exc())
                _ctx = ctx
                out_channel = ctx.channel
                month = await self.discord_helper.ask_number(_ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_month_question"),
                    1, 12, timeout=60)
                day = await self.discord_helper.ask_number(_ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_day_question"),
                    1, 31, timeout=60)

            user_bday_set = self.db.get_user_birthday(guild_id, ctx.author.id)
            self.db.add_user_birthday(guild_id, ctx.author.id, month, day)

            if not user_bday_set:
                taco_settings = self.get_tacos_settings(guild_id)
                taco_amount = taco_settings.get("birthday_count", 25)
                reason_msg = self.settings.get_string(guild_id, "taco_reason_birthday")
                await self.discord_helper.taco_give_user(guild_id, self.bot.user, ctx.author, reason_msg, tacotypes.TacoTypes.BIRTHDAY, taco_amount=taco_amount )

            fields = [
                { 'name': self.settings.get_string(guild_id, "month"), 'value': str(month), 'inline': True },
                { 'name': self.settings.get_string(guild_id, "day"), 'value': str(day), 'inline': True }
            ]
            await self.discord_helper.sendEmbed(out_channel,
                self.settings.get_string(guild_id, "birthday_set_title"),
                self.settings.get_string(guild_id, "birthday_set_confirm", user=ctx.author.mention),
                fields=fields, delete_after=10)
            pass
        except Exception as e:
            self.log.error(guild_id, "birthday.birthday", str(e), traceback.format_exc())
            self.discord_helper.notify_of_error(ctx)

    @birthday.command(name='check')
    @commands.guild_only()
    async def check_birthday(self, ctx):
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            if self.was_checked_today(guild_id):
                return
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id)
            # wish the users a happy birthday
            if birthdays.count() > 0:
                self.log.debug(guild_id, "birthday.check_birthday", f"Sending birthday wishes from check_birthday for {guild_id}")
                await self.send_birthday_message(ctx, birthdays)
            # track the check
            self.db.track_birthday_check(guild_id)
            await asyncio.sleep(.5)
        except Exception as e:
            self.log.error(guild_id, "birthday.check_birthday", str(e), traceback.format_exc())
            self.discord_helper.notify_of_error(ctx)

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            # raise Exception(f"No live_now settings found for guild {guildId}")
            return None
        return cog_settings

    def was_checked_today(self, guildId: int):
        try:
            return self.db.birthday_was_checked_today(guildId)
        except Exception as e:
            self.log.error(guildId, "birthday.was_checked_today", str(e), traceback.format_exc())
            return False

    def get_todays_birthdays(self, guildId: int):
        try:
            # central_tz= pytz.timezone(self.settings.timezone)
            date = datetime.datetime.now(tz=None)
            month = date.month
            day = date.day
            birthdays = self.db.get_user_birthdays(guildId, month, day)
            return birthdays
        except Exception as e:
            self.log.error(guildId, "birthday.get_todays_birthdays", str(e), traceback.format_exc())
            return []

    async def send_birthday_message(self, ctx: ComponentContext, birthdays: typing.List[typing.Dict]):
        try:
            guild_id = 0
            if ctx.guild:
                guild_id = ctx.guild.id

            if self.was_checked_today(guild_id):
                return

            # user started streaming
            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, "birthday.on_member_update", f"No live_now settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, "birthday.on_member_update", f"birthday is disabled for guild {guild_id}")
                return


            if birthdays.count() == 0:
                return

            # get all the users
            users = []
            for birthday in birthdays:
                user = ctx.guild.get_member(int(birthday['user_id'])).mention

                if user:
                    users.append(user)

            # Get a random birthday message

            # These should be pulled from database settings
            birthday_messsages = cog_settings.get("messages", [])
            birthday_images = cog_settings.get("images", [])
            output_channel_id = cog_settings.get("channel_id", "0")

            output_channel = ctx.guild.get_channel(int(output_channel_id))
            if output_channel:
                message = birthday_messsages[int(random() * len(birthday_messsages))]
                image = birthday_images[int(random() * len(birthday_images))]

                date = datetime.datetime.now(tz=None)
                month_name = date.strftime("%B")
                month_day = date.strftime("%d")
                fields = [
                    { 'name': self.settings.get_string(guild_id, "month"), 'value': month_name, 'inline': True },
                    { 'name': self.settings.get_string(guild_id, "day"), 'value': month_day, 'inline': True }
                ]
                await self.discord_helper.sendEmbed(output_channel,
                    self.settings.get_string(guild_id, "birthday_wishes_title"),
                    self.settings.get_string(guild_id, "birthday_wishes_message", message=message, users=' '.join(users)),
                    image=image, color=None, fields=fields)
            else:
                self.log.debug(guild_id, "birthday.send_birthday_message", f"Could not find channel {output_channel_id}")

        except Exception as e:
            self.log.error(guild_id, "birthday.send_birthday_message", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            guild_id = 0
            if message.guild:
                guild_id = message.guild.id
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            if self.was_checked_today(guild_id):
                return
            await asyncio.sleep(1)
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id)
            # wish the users a happy birthday
            if birthdays.count() > 0:
                self.log.debug(guild_id, "birthday.on_message", f"Sending birthday wishes from on_message for {guild_id}")
                await self.send_birthday_message(message, birthdays)
            # track the check
            self.db.track_birthday_check(guild_id)
            await asyncio.sleep(.5)
        except Exception as e:
            self.log.error(guild_id, "birthday.on_message", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        try:
            guild_id = 0
            if after.guild:
                guild_id = after.guild.id
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            if self.was_checked_today(guild_id):
                return
            await asyncio.sleep(1)
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id)
            # wish the users a happy birthday
            if birthdays.count() > 0:
                self.log.debug(guild_id, "birthday.on_member_update", f"Sending birthday wishes from on_member_update for {guild_id}")
                await self.send_birthday_message(after, birthdays)
            # track the check
            self.db.track_birthday_check(guild_id)
            await asyncio.sleep(.5)
        except Exception as e:
            self.log.error(guild_id, "birthday.on_member_update", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            guild_id = 0
            if member.guild:
                guild_id = member.guild.id
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            if self.was_checked_today(guild_id):
                return
            await asyncio.sleep(1)
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id)
            # wish the users a happy birthday
            if birthdays.count() > 0:
                self.log.debug(guild_id, "birthday.on_member_join", f"Sending birthday wishes from on_member_join for {guild_id}")
                await self.send_birthday_message(member, birthdays)
            # track the check
            self.db.track_birthday_check(guild_id)
            await asyncio.sleep(.5)
        except Exception as e:
            self.log.error(guild_id, "birthday.on_member_join", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_ready(self):
        pass
        try:
            for guild in self.bot.guilds:
                guild_id = 0
                if guild:
                    guild_id = guild.id
                # check if the birthday check is enabled
                # check if the birthday check has not ran today yet
                if self.was_checked_today(guild_id):
                    return
                await asyncio.sleep(1)
                # get if there are any birthdays today in the database
                birthdays = self.get_todays_birthdays(guild_id)
                # wish the users a happy birthday
                if birthdays.count() > 0:
                    self.log.debug(guild_id, "birthday.on_ready", f"Sending birthday wishes from on_ready for {guild_id}")
                    ctx = self.discord_helper.create_context(bot=self.bot, guild=guild)
                    await self.send_birthday_message(ctx, birthdays)
                # track the check
                self.db.track_birthday_check(guild_id)
                await asyncio.sleep(.5)
        except Exception as e:
            self.log.error(guild_id, "birthday.on_member_join", str(e), traceback.format_exc())
    def get_tacos_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings
def setup(bot):
    bot.add_cog(Birthday(bot))
