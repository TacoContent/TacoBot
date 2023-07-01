# This cog will message the user if they leave the discord and ask them
# the reason for leaving.

from unicodedata import is_normalized
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
from .lib.messaging import Messaging


class LeaveSurvey(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.SETTINGS_SECTION = "leave_survey"

        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.group()
    @commands.has_permissions(manage_guild=True)
    async def leavesurvey(self, ctx):
        pass

    @leavesurvey.command()
    @commands.has_permissions(manage_guild=True)
    async def ask(self, ctx, member: discord.Member):
        await ctx.message.delete()
        await self.ask_survey(ctx.author)

    async def ask_survey(self, member):
        _method = inspect.stack()[0][3]
        try:
            guild_id = member.guild.id
            try:
                if member.bot:
                    return
                # get ban list and see if user is in that list
                is_banned = await member.guild.fetch_ban(member) is not None
                if is_banned:
                    return
            except discord.NotFound as nf:
                # user is not banned
                pass

            # get the leave_survey settings from settings
            cog_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not cog_settings:
                # raise exception if there are no leave_survey settings
                self.log.error(guild_id, f"{self._module}.{_method}", f"No leave_survey settings found for guild {guild_id}")
                return

            log_channel_id = int(cog_settings["log_channel_id"])
            log_channel = None
            if log_channel_id:
                log_channel = await self.bot.fetch_channel(log_channel_id)
            take_survey = False
            reason = "Did not answer the survey asking why they left."
            try:
                ctx = self.discord_helper.create_context(bot=self.bot, author=member, guild=member.guild, channe=None)
                async def response_callback(result):
                    if result:
                        reason = "No reason given."
                        try:
                            reason = await self.discord_helper.ask_text(ctx, member, "Leave Survey", "Please tell us why you are leaving.", timeout=600)
                            await self.messaging.send_embed(member, "Thank You!", "Thank you for your feedback. We will review your feedback and take action accordingly.")
                        except discord.Forbidden as f:
                            self.log.info(guild_id, f"{self._module}.{_method}", f"Failed to send message to {utils.get_user_display_name(member)} ({member.id})")
                        except discord.NotFound as nf:
                            self.log.info(guild_id, f"{self._module}.{_method}", f"Failed to send message to {utils.get_user_display_name(member)} ({member.id})")
                        except Exception as e:
                            # an error occurred while asking the user if they want to take the surveys
                            self.log.error(guild_id, f"{self._module}.{_method}", f"Error in f"{self._module}.{_method}": {e}", traceback.format_exc())

                        if log_channel:
                            await self.messaging.send_embed(
                                channel=log_channel,
                                title="Leave Survey",
                                message=f"{utils.get_user_display_name(member)} ({member.id}) has left the server. \n\n**Reason given:**\n\n{reason}",
                                author=member
                            )

                await self.discord_helper.ask_yes_no(
                    ctx=ctx,
                    targetChannel=member,
                    question="We are very sorry to see you leave. \n\nWould you be willing to let us know why you are leaving?",
                    title="Leave Survey",
                    timeout=60,
                    result_callback=response_callback)

            except discord.Forbidden as f:
                self.log.info(guild_id, f"{self._module}.{_method}", f"Failed to send message to {utils.get_user_display_name(member)} ({member.id})")
            except discord.NotFound as nf:
                self.log.info(guild_id, f"{self._module}.{_method}", f"Failed to send message to {utils.get_user_display_name(member)} ({member.id})")
            except Exception as e:
                # an error occurred while asking the user if they want to take the surveys
                self.log.error(guild_id, f"{self._module}.{_method}", f"Error in f"{self._module}.{_method}": {e}", traceback.format_exc())

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.ask_survey(member)

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
    await bot.add_cog(LeaveSurvey(bot))
