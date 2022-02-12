import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing

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

import inspect

class StreamTeam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.STREAMER_ROLE_EMOJI = "<:Streamer:938621185229480086>"
        self.STREAMER_ROLE_REQUEST_MESSAGE_ID = 938621319673692170
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "streamteam.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "streamteam.__init__", f"Logger initialized with level {log_level.name}")

    def get_stream_team_roles(self, guild):
        return [discord.utils.get(guild.roles, name="STREAMER")]

    def get_stream_team_name(self, guild, team_role_id: int):
        return "Taco"



    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        _method = inspect.stack()[0][3]
        try:
            guild_id = payload.guild_id
            # ignore if not in a guild
            if guild_id is None:
                return
            if payload.event_type != 'REACTION_ADD':
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if user.bot:
                return
            if message.id != self.STREAMER_ROLE_REQUEST_MESSAGE_ID:
                return

            if str(payload.emoji) == self.STREAMER_ROLE_EMOJI:
                # add user to the stream team requests
                self.db.add_stream_team_request(guild_id, f"{user.name}#{user.discriminator}", user.id)
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
