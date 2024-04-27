import asyncio
import datetime
import inspect
import json
import os
import traceback
import typing
from random import random

import discord
import pytz
from bot.cogs.lib import discordhelper, logger, settings
from bot.cogs.lib.enums import loglevel, tacotypes
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.mongodb.birthdays import BirthdaysDatabase
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


class Birthday(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.SETTINGS_SECTION = "birthday"
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.birthdays_db = BirthdaysDatabase()
        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @app_commands.guild_only()
    @app_commands.command(name="birthday", description="Add your birthday")
    async def birthday_app(self, interaction: discord.Interaction, month: int, day: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            guild_id = 0
            if interaction.guild:
                guild_id = interaction.guild.id
            else:
                return

            user = interaction.user
            user_bday_set = self.birthdays_db.get_user_birthday(guild_id, user.id)
            self.birthdays_db.add_user_birthday(guild_id, user.id, month, day)

            if not user_bday_set:
                taco_settings = self.get_tacos_settings(guild_id)
                taco_amount = taco_settings.get("birthday_count", 25)
                reason_msg = self.settings.get_string(guild_id, "taco_reason_birthday")
                await self.discord_helper.taco_give_user(
                    guild_id,
                    self.bot.user,
                    user,
                    reason_msg,
                    tacotypes.TacoTypes.BIRTHDAY,
                    taco_amount=taco_amount,
                )

            fields = [
                {"name": self.settings.get_string(guild_id, "month"), "value": str(month), "inline": True},
                {"name": self.settings.get_string(guild_id, "day"), "value": str(day), "inline": True},
            ]

            # TODO: change to full interaction response
            await interaction.response.send_message(
                content=f"I have set your birthday to {month}/{day}. Run the command again to change if this is incorrect.",
                ephemeral=True,
            )

            # await interaction.response.send_message(
            #     content=self.settings.get_string(guild_id, "birthday_set_confirm", user=user.mention),
            #     embed=self.discord_helper.create_embed(
            #         title=self.settings.get_string(guild_id, "birthday_set_title"),
            #         description=self.settings.get_string(guild_id, "birthday_set_confirm", user=user.mention),
            #         fields=fields,
            #     ),
            #     ephemeral=True,
            # )


            # await self.messaging.send_embed(
            #     out_channel,
            #     self.settings.get_string(guild_id, "birthday_set_title"),
            #     self.settings.get_string(guild_id, "birthday_set_confirm", user=ctx.author.mention),
            #     fields=fields,
            #     delete_after=10,
            # )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=interaction.channel.id if interaction.channel else None,
                userId=user.id,
                command="birthday",
                subcommand=None,
                args=[{"type": "slash_command"}, {"month": month}, {"day": day}],
            )
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.group(name="birthday", aliases=["bday"])
    @commands.guild_only()
    async def birthday(self, ctx):
        _method = inspect.stack()[0][3]
        if ctx.invoked_subcommand is not None:
            return

        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()
            month = None
            day = None
            _ctx = ctx
            out_channel = ctx.author
            try:
                _ctx = self.discord_helper.create_context(
                    self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild
                )
                month = await self.discord_helper.ask_number(
                    _ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_month_question"),
                    1,
                    12,
                    timeout=60,
                )
                _ctx = self.discord_helper.create_context(
                    self.bot, author=ctx.author, channel=ctx.author, guild=ctx.guild
                )
                day = await self.discord_helper.ask_number(
                    _ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_day_question"),
                    1,
                    31,
                    timeout=60,
                )
            except discord.Forbidden:
                self.log.info(guild_id, f"{self._module}.{self._class}.{_method}", "Forbidden", traceback.format_exc())
                _ctx = ctx
                out_channel = ctx.channel
                month = await self.discord_helper.ask_number(
                    _ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_month_question"),
                    1,
                    12,
                    timeout=60,
                )
                day = await self.discord_helper.ask_number(
                    _ctx,
                    self.settings.get_string(guild_id, "birthday_set_title"),
                    self.settings.get_string(guild_id, "birthday_set_day_question"),
                    1,
                    31,
                    timeout=60,
                )

            user_bday_set = self.birthdays_db.get_user_birthday(guild_id, ctx.author.id)
            self.birthdays_db.add_user_birthday(guild_id, ctx.author.id, month, day)

            if not user_bday_set:
                taco_settings = self.get_tacos_settings(guild_id)
                taco_amount = taco_settings.get("birthday_count", 25)
                reason_msg = self.settings.get_string(guild_id, "taco_reason_birthday")
                await self.discord_helper.taco_give_user(
                    guild_id,
                    self.bot.user,
                    ctx.author,
                    reason_msg,
                    tacotypes.TacoTypes.BIRTHDAY,
                    taco_amount=taco_amount,
                )

            fields = [
                {"name": self.settings.get_string(guild_id, "month"), "value": str(month), "inline": True},
                {"name": self.settings.get_string(guild_id, "day"), "value": str(day), "inline": True},
            ]
            await self.messaging.send_embed(
                out_channel,
                self.settings.get_string(guild_id, "birthday_set_title"),
                self.settings.get_string(guild_id, "birthday_set_confirm", user=ctx.author.mention),
                fields=fields,
                delete_after=10,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="birthday",
                subcommand=None,
                args=[{"type": "command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @birthday.command(name="check")
    @commands.guild_only()
    async def check_birthday(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()

            await asyncio.sleep(3)
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            if self.was_checked_today(guild_id):
                return
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id) or []
            await self.clear_birthday_role(ctx)
            # wish the users a happy birthday
            if len(birthdays) > 0:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Sending birthday wishes from check_birthday for {guild_id}",
                )
                await self.send_birthday_message(ctx, birthdays)
                await self.add_user_to_birthday_role(ctx, birthdays)
            # track the check
            self.birthdays_db.track_birthday_check(guild_id)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="birthday",
                subcommand="check",
                args=[{"type": "command"}],
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    def was_checked_today(self, guildId: int):
        _method = inspect.stack()[0][3]
        try:
            return self.birthdays_db.birthday_was_checked_today(guildId)
        except Exception as e:
            self.log.error(guildId, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return False

    def get_todays_birthdays(self, guildId: int):
        _method = inspect.stack()[0][3]
        try:
            date = datetime.datetime.now(tz=pytz.timezone(self.settings.timezone))
            month = date.month
            day = date.day
            birthdays = self.birthdays_db.get_user_birthdays(guildId, month, day)
            return birthdays
        except Exception as e:
            self.log.error(guildId, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return []

    async def add_user_to_birthday_role(self, ctx: Context, birthdays: typing.List[typing.Dict]):
        _method = inspect.stack()[0][3]
        # add all birthday users to the birthday role from settings.role
        birthday_role = None
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
            else:
                return

            await asyncio.sleep(0.5)
            if self.was_checked_today(guild_id):
                return

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No birthday settings found for guild {guild_id}",
                )
                return

            # is it enabled?
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"birthday is disabled for guild {guild_id}"
                )
                return

            # get the role from the settings
            role_id = cog_settings.get("role", None)
            if not role_id:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No birthday role found for guild {guild_id}"
                )
                return
            birthday_role = discord.utils.get(ctx.guild.roles, id=int(role_id))
            if not birthday_role:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Could not find birthday role {role_id} for guild {guild_id}",
                )
                return

            for birthday in birthdays:
                user_id = int(birthday["user_id"])
                member = await self.discord_helper.get_or_fetch_member(guildId=guild_id, userId=user_id)
                if member:
                    await self.discord_helper.add_remove_roles(
                        user=member, check_list=[], add_list=[birthday_role.id], remove_list=[], allow_everyone=True
                    )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    async def clear_birthday_role(self, ctx: Context):
        # clear all users from the birthday role from settings.role
        _method = inspect.stack()[0][3]
        # add all birthday users to the birthday role from settings.role
        birthday_role = None
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
            else:
                return

            await asyncio.sleep(0.5)
            if self.was_checked_today(guild_id):
                return

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No birthday settings found for guild {guild_id}",
                )
                return

            # is it enabled?
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"birthday is disabled for guild {guild_id}"
                )
                return

            # get the role from the settings
            role_id = cog_settings.get("role", None)
            if not role_id:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"No birthday role found for guild {guild_id}"
                )
                return
            birthday_role = discord.utils.get(ctx.guild.roles, id=int(role_id))
            if not birthday_role:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Could not find birthday role {role_id} for guild {guild_id}",
                )
                return
            # remove all users from the role
            for member in birthday_role.members:
                await self.discord_helper.add_remove_roles(
                    user=member, check_list=[], add_list=[], remove_list=[birthday_role.id], allow_everyone=True
                )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return

    async def send_birthday_message(self, ctx: Context, birthdays: typing.List[typing.Dict]):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id

            await asyncio.sleep(0.5)
            if self.was_checked_today(guild_id):
                return

            # user started streaming
            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No live_now settings found for guild {guild_id}",
                )
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"birthday is disabled for guild {guild_id}"
                )
                return

            if len(birthdays) == 0:
                return

            # get all the users
            users = []
            for birthday in birthdays:
                user = await self.discord_helper.get_or_fetch_member(guildId=guild_id, userId=int(birthday["user_id"]))
                # user = ctx.guild.get_member(int(birthday["user_id"])).mention

                if user:
                    users.append(user.mention)

            # Get a random birthday message

            # These should be pulled from database settings
            birthday_messsages = cog_settings.get("messages", [])
            birthday_images = cog_settings.get("images", [])
            output_channel_id = cog_settings.get("channel_id", "0")

            # output_channel = ctx.guild.get_channel(int(output_channel_id))
            output_channel = await self.discord_helper.get_or_fetch_channel(channelId=int(output_channel_id))
            if output_channel:
                message = birthday_messsages[int(random() * len(birthday_messsages))]
                image = birthday_images[int(random() * len(birthday_images))]

                date = datetime.datetime.now(tz=None)
                month_name = date.strftime("%B")
                month_day = date.strftime("%d")
                fields = [
                    {"name": self.settings.get_string(guild_id, "month"), "value": month_name, "inline": True},
                    {"name": self.settings.get_string(guild_id, "day"), "value": month_day, "inline": True},
                ]
                await self.messaging.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "birthday_wishes_title"),
                    message=self.settings.get_string(guild_id, "birthday_wishes_message", message=message, users=""),
                    image=image,
                    color=None,
                    content=" ".join(users),
                    fields=fields,
                )
            else:
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"Could not find channel {output_channel_id}"
                )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if message.guild:
                guild_id = message.guild.id
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            await asyncio.sleep(1)
            if self.was_checked_today(guild_id):
                return
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id) or []
            await self.clear_birthday_role(message)
            # wish the users a happy birthday
            if len(birthdays) > 0:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Sending birthday wishes from on_message for {guild_id}",
                )
                await self.send_birthday_message(message, birthdays)
                await self.add_user_to_birthday_role(message, birthdays)
            # track the check
            self.birthdays_db.track_birthday_check(guild_id)
            await asyncio.sleep(1)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if after.guild:
                guild_id = after.guild.id
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            await asyncio.sleep(1)
            if self.was_checked_today(guild_id):
                return
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id) or []
            await self.clear_birthday_role(after)
            # wish the users a happy birthday
            if len(birthdays) > 0:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Sending birthday wishes from on_member_update for {guild_id}",
                )
                await self.send_birthday_message(after, birthdays)
                await self.add_user_to_birthday_role(after, birthdays)
            # track the check
            self.birthdays_db.track_birthday_check(guild_id)
            await asyncio.sleep(1)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if member.guild:
                guild_id = member.guild.id
            # check if the birthday check is enabled
            # check if the birthday check has not ran today yet
            await asyncio.sleep(1)
            if self.was_checked_today(guild_id):
                return
            # get if there are any birthdays today in the database
            birthdays = self.get_todays_birthdays(guild_id) or []
            await self.clear_birthday_role(member)
            # wish the users a happy birthday
            if len(birthdays) > 0:
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Sending birthday wishes from on_member_join for {guild_id}",
                )
                await self.send_birthday_message(member, birthdays)
                await self.add_user_to_birthday_role(member, birthdays)
            # track the check
            self.birthdays_db.track_birthday_check(guild_id)
            await asyncio.sleep(1)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_ready(self):
        pass
        # guild_id = 0
        # try:
        #     for guild in self.bot.guilds:
        #         if guild:
        #             guild_id = guild.id
        #         # check if the birthday check is enabled
        #         # check if the birthday check has not ran today yet
        #         if self.was_checked_today(guild_id):
        #             return
        #         await asyncio.sleep(1)
        #         # get if there are any birthdays today in the database
        #         birthdays = self.get_todays_birthdays(guild_id)
        #         # wish the users a happy birthday
        #         if len(birthdays) > 0:
        #             self.log.debug(
        #                 guild_id, "birthday.on_ready", f"Sending birthday wishes from on_ready for {guild_id}"
        #             )
        #             ctx = self.discord_helper.create_context(bot=self.bot, guild=guild)
        #             await self.send_birthday_message(ctx, birthdays)
        #         # track the check
        #         self.birthdays_db.track_birthday_check(guild_id)
        #         await asyncio.sleep(0.5)
        # except Exception as e:
        #     self.log.error(guild_id, "birthday.on_member_join", str(e), traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


async def setup(bot):
    await bot.add_cog(Birthday(bot))
