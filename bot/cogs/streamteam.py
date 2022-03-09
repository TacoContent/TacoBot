import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import inspect
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


class StreamTeam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "streamteam"
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "streamteam.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        _method = inspect.stack()[0][3]
        try:
            guild_id = payload.guild_id
            if guild_id is None or guild_id == 0:
                return
            if payload.event_type != 'REACTION_REMOVE':
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if user.bot:
                return

            # get the streamteam settings from settings
            streamteam_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not streamteam_settings:
                # raise exception if there are no streamteam settings
                self.log.error(guild_id, "streamteam.on_message", f"No streamteam settings found for guild {guild_id}")
                await self.discord_helper.notify_bot_not_initialized(message, "streamteam")
                return

            # get the reaction emoji
            emoji = streamteam_settings["emoji"]
            team_name = streamteam_settings["name"]
            # get the message ids to check
            watch_message_ids = streamteam_settings["message_ids"]
            # get the log channel id
            log_channel_id = streamteam_settings["log_channel"]
            if log_channel_id:
                log_channel = await self.discord_helper.get_or_fetch_channel(log_channel_id)

            # check if the message that is reacted to is in the list of message ids and the emoji is one that is configured.
            if str(message.id) in watch_message_ids and str(payload.emoji) in emoji:
                # add user to the stream team requests
                self.db.remove_stream_team_request(guild_id, user.id)
                twitch_user = self.db.get_user_twitch_info(user.id)
                twitch_name = "UNKNOWN"
                if twitch_user:
                    twitch_name = twitch_user['twitch_name']

                if log_channel:
                    await self.discord_helper.sendEmbed(log_channel,
                        self.setttings.get_string(guild_id, "streamteam_removal_tile"),
                        self.settings.get_string(guild_id, "streamteam_removal_message",
                            user=f"{user.name}#{user.discriminator}",
                            team_name=team_name,
                            twitch_name=twitch_name), color=0xff0000)

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        try:
            guild_id = payload.guild_id
            # ignore if not in a guild
            if guild_id is None or guild_id == 0:
                return
            if payload.event_type != 'REACTION_ADD':
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if user.bot:
                return

            # get the streamteam settings from settings
            streamteam_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not streamteam_settings:
                # raise exception if there are no streamteam settings
                self.log.error(guild_id, "streamteam.on_message", f"No streamteam settings found for guild {guild_id}")
                await self.discord_helper.notify_bot_not_initialized(message, "streamteam")
                return

            # get the reaction emoji
            emoji = streamteam_settings["emoji"]
            team_name = streamteam_settings["name"]
            # get the message ids to check
            watch_message_ids = streamteam_settings["message_ids"]
            # get the log channel id
            log_channel_id = streamteam_settings["log_channel"]
            if log_channel_id:
                log_channel = await self.discord_helper.get_or_fetch_channel(log_channel_id)

            # check if the message that is reacted to is in the list of message ids and the emoji is one that is configured.
            if str(message.id) in watch_message_ids and str(payload.emoji) in emoji:
                # add user to the stream team requests
                self.db.add_stream_team_request(guild_id, f"{user.name}#{user.discriminator}", user.id)
                unknown = self.settings.get_string(guild_id, "unknown")
                # send a message to the user and ask them their twitch name if it is not yet set
                twitch_name = unknown
                twitch_user = self.db.get_user_twitch_info(user.id)
                if not twitch_user:
                    try:
                        ctx_dict = {"bot": self.bot, "author": user, "guild": None, "channel": None}
                        ctx = collections.namedtuple("Context", ctx_dict.keys())(*ctx_dict.values())
                        twitch_name = await self.discord_helper.ask_text(ctx, user,
                            self.settings.get_string(guild_id, "twitch_name_title"),
                            self.settings.get_string(guild_id, "twitch_name_question", team_name=team_name),
                            timeout=60)
                        if twitch_name:
                            twitch_name = utils.get_last_section_in_url(twitch_name.lower().strip())

                            self.log.debug(0, _method, f"{user} requested to set twitch name {twitch_user}")
                            self.db.set_user_twitch_info(user.id, None, twitch_name)
                            await self.discord_helper.sendEmbed(user,
                                self.settings.get_string(guild_id, "success"),
                                self.settings.get_string(guild_id, "streamteam_set_twitch_name_message", twitch_name=twitch_name),
                                color=0x00ff00)
                    except discord.Forbidden as e:
                        # cant send them a message. Put it in the channel...
                        await self.discord_helper.sendEmbed(channel,
                            self.settings.get_string(guild_id, "error"),
                            self.settings.get_string(guild_id, "twitch_name_dm_error", user=user.mention),
                            footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                            color=0xff0000, delete_after=30)

                else:
                    twitch_name = twitch_user['twitch_name']

                if log_channel:
                    twitch_name = unknown if twitch_name is None else twitch_name
                    await self.discord_helper.sendEmbed(log_channel,
                        self.setttings.get_string(guild_id, "streamteam_join_tile"),
                        self.settings.get_string(guild_id, "streamteam_join_message",
                            user=user, team_name=team_name, twitch_name=twitch_name),
                        color=0x00ff00)
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())


    @commands.Cog.listener()
    async def on_disconnect(self):
        pass

    @commands.Cog.listener()
    async def on_resumed(self):
        pass

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        self.log.error(0, "streamteam.on_error", f"{str(event)}", traceback.format_exc())

    @commands.group()
    @commands.guild_only()
    async def team(self, ctx):
        pass

    @team.command()
    @commands.guild_only()
    async def invite(self, ctx, twitchName: str = None):
        try:
            guild_id = ctx.guild.id

            if twitchName is None:
                twitchName = self.db.get_user_twitch_info(ctx.author.id)['twitch_name']
            if twitchName is None:
                try:
                    await self.discord_helper.sendEmbed(ctx.author,
                        self.settings.get_string(guild_id, "error"),
                        self.settings.get_string(guild_id, "streamteam_invite_no_twitch_name_message"),
                        color=0xff0000)
                    return
                except discord.Forbidden:
                    # if we cant send to user, then we send to channel
                    await self.discord_helper.sendEmbed(ctx.channel,
                        self.settings.get_string(guild_id, "error"),
                        self.settings.get_string(guild_id, "streamteam_invite_no_twitch_name_message"),
                        footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                        color=0xff0000, delete_after=30)
                    return

            await self._invite_user(ctx, ctx.author, twitchName)

        except Exception as ex:
            self.log.error(guild_id, "streamteam.invite", str(ex), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @team.command(aliases=["invite-user"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def invite_user(self, ctx, user: discord.User, twitchName: str):
        await self._invite_user(ctx, user, twitchName)

    async def _invite_user(self, ctx, user: discord.User, twitchName: str):
        try:
            guild_id = ctx.guild.id
            # get the streamteam settings from settings
            streamteam_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not streamteam_settings:
                # raise exception if there are no streamteam settings
                self.log.error(guild_id, "streamteam.on_message", f"No streamteam settings found for guild {guild_id}")
                await self.discord_helper.notify_bot_not_initialized(ctx, "streamteam")
                return
            unknown = self.settings.get_string(guild_id, "unknown")
            log_channel_id = streamteam_settings["log_channel"]
            if log_channel_id:
                log_channel = await self.discord_helper.get_or_fetch_channel(log_channel_id)
            team_name = streamteam_settings["name"]

            self.db.set_user_twitch_info(user.id, None, twitchName)
            self.db.add_stream_team_request(ctx.guild.id, twitchName, user.id)

            await self.discord_helper.sendEmbed(ctx.channel,
                self.settings.get_string(guild_id, "success"),
                self.settings.get_string(guild_id, "streamteam_invite_success_message", user=f"{user.name}#{user.discriminator}", team_name=team_name, twitch_name=twitchName),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                color=0x00ff00, delete_after=30)

            if log_channel:
                twitch_name = unknown if twitch_name is None else twitch_name
                await self.discord_helper.sendEmbed(log_channel,
                    self.settings.get_string(guild_id, "streamteam_join_title"),
                    self.settings.get_string(guild_id, "streamteam_join_message", user=f"{user.name}#{user.discriminator}", team_name=team_name, twitch_name=twitchName),
                    color=0x00ff00)

        except Exception as ex:
            self.log.error(ctx.guild.id, "streamteam.invite", str(ex), traceback.format_exc())
            await self.discord_helper.notify_of_error(ctx)

    @team.command()
    @commands.guild_only()
    async def help(self, ctx):
        guild_id = 0
        if ctx.guild:
            guild_id = ctx.guild.id
            await ctx.message.delete()
        await self.discord_helper.sendEmbed(ctx.channel,
            self.settings.get_string(guild_id, "help_title", bot_name=self.settings.name),
            self.settings.get_string(guild_id, "help_module_message", bot_name=self.settings.name, command="team"),
            footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
            color=0xff0000, delete_after=30)
        pass

def setup(bot):
    bot.add_cog(StreamTeam(bot))
