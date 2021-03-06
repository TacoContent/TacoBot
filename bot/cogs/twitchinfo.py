# this cog will DM the user if they have not yet told the bot what their twitch name is if they interact with the bot.

from ctypes import Union

import requests
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
from discord_slash.utils.manage_components import (
    create_button,
    create_actionrow,
    create_select,
    create_select_option,
    wait_for_component,
)
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
from .lib import tacotypes

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
        self.log.debug(0, "twitchinfo.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        pass

    @commands.group()
    async def twitch(self, ctx):
        pass

    @twitch.command()
    @commands.guild_only()
    async def help(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
            await ctx.message.delete()
        await self.discord_helper.sendEmbed(
            ctx.channel,
            self.settings.get_string(guild_id, "help_title", bot_name=self.settings.name),
            self.settings.get_string(guild_id, "help_module_message", bot_name=self.settings.name, command="twitch"),
            footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
            color=0xFF0000,
            delete_after=30,
        )

    @twitch.command(aliases=["invite-bot"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def invite_bot(self, ctx, *, user: typing.Union[discord.Member, discord.User] = None):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
            channel = ctx.channel
            await ctx.message.delete()

        if user == None or user == "":
            # specify channel
            return
        twitch_info = self.db.get_user_twitch_info(user.id)
        twitch_name = None
        if twitch_info:
            twitch_name = twitch_info["twitch_name"]
        else:
            # user does not have twitch info must call twitch.set_user first
            twitch_name = await self.set_user(ctx, user)

        if twitch_name:
            # add the twitch name to the twitch_channels collection
            # send http request to nodered tacobot api to add the channel to the bot
            url = f"https://nodered.bit13.local/tacobot/guild/{guild_id}/invite/{twitch_name}"
            result = requests.post(url, headers={"X-AUTH-TOKEN": str(self.bot.id)})
            if result.status_code == 200:
                await self.discord_helper.sendEmbed(
                    channel,
                    "Invite Bot",
                    f"Invited @OurTacoBot to {twitch_name}",
                    footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                    color=0xFF0000,
                    delete_after=30,
                )

    @twitch.command()
    async def get(self, ctx, member: typing.Union[discord.Member, discord.User] = None):
        check_member = member

        if check_member is None:
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
        # if ctx.author is administrator, then we can get the twitch name from the database
        if twitch_info is None:
            if ctx.author.guild_permissions.administrator or check_member is None:
                twitch_name = await self.discord_helper.ask_text(
                    alt_ctx,
                    ctx.author,
                    "Twitch Name",
                    "I do not have a twitch name set for {who}, please respond with the twitch name.",
                    60,
                )
                if not twitch_name is None:
                    self.db.set_user_twitch_info(ctx.author.id, None, twitch_name.lower().strip())
        else:
            twitch_name = twitch_info["twitch_name"]
        if not twitch_name is None:
            await self.discord_helper.sendEmbed(
                ctx.author,
                "Twitch Name",
                f"The Twitch name for {who} has been set to `{twitch_name}`.\n\nhttps://twitch.tv/{twitch_name}\n\nIf your twitch name changes in the future, you can use `.taco twitch set` in a discord channel, or `.twitch set` in the DM with me to set it.",
                color=0x00FF00,
            )

    @twitch.command(aliases=["set-user"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_user(self, ctx, user: discord.Member, twitch_name: str = None):
        try:
            _method = inspect.stack()[0][3]
            guild_id = 0
            channel = ctx.author
            if ctx.guild:
                guild_id = ctx.guild.id
                channel = ctx.channel
                await ctx.message.delete()

            # if user is None:
            #     user = await self.discord_helper.ask_member(ctx, "User", "Please respond with the user you want to set the twitch name for.")

            if twitch_name is None:
                twitch_name = await self.discord_helper.ask_text(
                    ctx, ctx.author, "Twitch Name", "Please respond with the twitch name you want to set for the user."
                )

            if twitch_name is not None and user is not None:
                twitch_name = utils.get_last_section_in_url(twitch_name.lower().strip())
                self.db.set_user_twitch_info(user.id, None, twitch_name)
                await self.discord_helper.sendEmbed(
                    channel,
                    "Success",
                    f"{ctx.author.mention}, The Twitch name has been set to {twitch_name} for {user.name}#{user.discriminator}.",
                    color=0x00FF00,
                    delete_after=30,
                )
            return twitch_name
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @twitch.command()
    async def set(self, ctx, twitch_name: str = None):
        try:
            _method = inspect.stack()[0][3]
            guild_id = 0
            resp_channel = ctx.author
            if ctx.guild:
                guild_id = ctx.guild.id
                resp_channel = ctx.channel
                await ctx.message.delete()

            if twitch_name is None:
                # try DM. if that doesnt work, use channel that they used...
                try:
                    resp_channel = ctx.author
                    twitch_name = await self.discord_helper.ask_text(
                        ctx,
                        ctx.author,
                        self.settings.get_string(guild_id, "twitch_ask_title"),
                        self.settings.get_string(guild_id, "twitch_ask_message", user=ctx.author.mention),
                        timeout=60,
                    )
                except discord.errors.Forbidden:
                    resp_channel = ctx.channel
                    twitch_name = await self.discord_helper.ask_text(
                        ctx,
                        ctx.channel,
                        self.settings.get_string(guild_id, "twitch_ask_title"),
                        self.settings.get_string(guild_id, "twitch_ask_message", user=ctx.author.mention),
                        timeout=60,
                    )

            self.log.debug(0, _method, f"{ctx.author} requested to set twitch name {twitch_name}")
            if twitch_name is not None:
                twitch_name = utils.get_last_section_in_url(twitch_name.lower().strip())
                found_twitch = self.db.get_user_twitch_info(ctx.author.id)
                if found_twitch is None:
                    # only set if we haven't set it already.
                    taco_settings = self.get_tacos_settings(guild_id)
                    taco_amount = taco_settings.get("twitch_count", 25)
                    reason_msg = self.settings.get_string(guild_id, "taco_reason_twitch")
                    await self.discord_helper.taco_give_user(
                        guild_id,
                        self.bot.user,
                        ctx.author,
                        reason_msg,
                        tacotypes.TacoTypes.TWITCH,
                        taco_amount=taco_amount,
                    )

                self.db.set_user_twitch_info(ctx.author.id, None, twitch_name)

                await self.discord_helper.sendEmbed(
                    resp_channel,
                    self.settings.get_string(guild_id, "twitch_set_title"),
                    self.settings.get_string(
                        guild_id, "twitch_set_message", user=ctx.author.mention, twitch_name=twitch_name
                    ),
                    color=0x00FF00,
                    delete_after=30,
                )
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    def get_tacos_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


def setup(bot):
    bot.add_cog(TwitchInfo(bot))
