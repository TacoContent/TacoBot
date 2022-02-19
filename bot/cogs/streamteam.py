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
                    await self.discord_helper.sendEmbed(log_channel, "Stream Team Removal", f"{user} has requested to be removed from the **{team_name}** twitch team.\n\nTwitch Name: `{twitch_name}`", color=0x00ff00)

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

                # send a message to the user and ask them their twitch name if it is not yet set
                twitch_name = "UNKNOWN"
                twitch_user = self.db.get_user_twitch_info(user.id)
                if not twitch_user:
                    ctx_dict = {"bot": self.bot, "author": user, "guild": None, "channel": None}
                    ctx = collections.namedtuple("Context", ctx_dict.keys())(*ctx_dict.values())
                    twitch_name = await self.discord_helper.ask_text(ctx, user, "Twitch Name", f"You have requested to join the **{team_name}** twitch team, please respond with your twitch username.", 60)
                    if twitch_name:
                        twitch_name = utils.get_last_section_in_url(twitch_name.lower().strip())

                        self.log.debug(0, _method, f"{user} requested to set twitch name {twitch_user}")
                        self.db.set_user_twitch_info(user.id, None, twitch_name)
                        await self.discord_helper.sendEmbed(user, "Success", f"Your Twitch name has been recorded as `{twitch_name}`. Keep an eye out for an invite soon.\n\nGo here: https://dashboard.twitch.tv/u/{twitch_name}/settings/channel\n\nTwitch Dashboard -> Settings -> Channel -> Featured Content => Scroll to the bottom.\n\nIf you change your twitch name in the future, you can use `.taco twitch set` in a discord channel, or `.twitch set` in the DM with me.", color=0x00ff00)
                else:
                    twitch_name = twitch_user['twitch_name']

                if log_channel:
                    twitch_name = "UNKNOWN" if twitch_name is None else twitch_name
                    await self.discord_helper.sendEmbed(log_channel, "Stream Team Join", f"{user} has requested to join the **{team_name}** twitch team.\n\nTwitch Name: `{twitch_name}`", color=0x00ff00)
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
    async def team(self, ctx):
        pass

    @team.command()
    async def help(self, ctx):
        # todo: add help command
        await self.discord_helper.sendEmbed(ctx.channel, "Help", f"I don't know how to help with this yet.", delete_after=20)
        pass

def setup(bot):
    bot.add_cog(StreamTeam(bot))
