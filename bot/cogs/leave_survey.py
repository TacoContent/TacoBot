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


class LeaveSurvey(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "leave_survey"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "leave_survey.__init__", "Initialized")

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
                self.log.error(guild_id, "leave_survey.on_message", f"No leave_survey settings found for guild {guild_id}")
                return

            log_channel_id = int(cog_settings["log_channel_id"])
            log_channel = None
            if log_channel_id:
                log_channel = await self.bot.fetch_channel(log_channel_id)
            take_survey = False
            reason = "Did not answer the survey asking why they left."
            try:
                ctx = self.discord_helper.create_context(bot=self.bot, author=member, guild=member.guild, channe=None)
                take_survey = await self.discord_helper.ask_yes_no(ctx, member, "We are very sorry to see you leave. \n\nWould you be willing to let us know why you are leaving?","Leave Survey", timeout=60)
                if take_survey:
                    reason = await self.discord_helper.ask_text(ctx, member, "Leave Survey", "Please tell us why you are leaving.", timeout=600)
                    await self.discord_helper.sendEmbed(member, "Thank You!", "Thank you for your feedback. We will review your feedback and take action accordingly.")
            except discord.Forbidden as f:
                self.log.info(guild_id, "leave_survey.on_message", f"Failed to send message to {member.name}#{member.discriminator} ({member.id})")
            except discord.NotFound as nf:
                self.log.info(guild_id, "leave_survey.on_message", f"Failed to send message to {member.name}#{member.discriminator} ({member.id})")
            except Exception as e:
                # an error occurred while asking the user if they want to take the surveys
                self.log.error(guild_id, "leave_survey.on_member_remove", f"Error in leave_survey.ask_survey: {e}", traceback.format_exc())

            if log_channel:
                await self.discord_helper.sendEmbed(log_channel, "Leave Survey", f"{member.name}#{member.discriminator} ({member.id}) has left the server. \n\n**Reason given:**\n\n{reason}", author=member)

        except Exception as e:
            self.log.error(guild_id, "leave_survey.on_member_remove", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.ask_survey(member)
async def setup(bot):
    await bot.add_cog(LeaveSurvey(bot))
