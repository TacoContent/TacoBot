# this is for restricted channels that only allow specific commands in chat.
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
import re

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


class MessagePreview(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "message_preview"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "message_preview.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        try:
            # if in a DM, ignore
            if message.guild is None:
                return
            # if the message is from a bot, ignore
            if message.author.bot:
                return
            guild_id = message.guild.id

            pattern = re.compile(r'https:\/\/discord(?:app)?\.com\/channels\/(\d+)/(\d+)/(\d+)')
            match = pattern.match(message.content)
            if not match:
                return

            ref_guild_id = int(match.group(1))
            channel_id = int(match.group(2))
            message_id = int(match.group(3))
            channel = self.bot.get_channel(channel_id)
            if ref_guild_id == guild_id:
                if channel:
                    ref_message = await channel.fetch_message(message_id)
                    if ref_message:
                        await self.create_message_preview(message, ref_message)
                    else:
                        self.log.debug(0, "message_preview.on_message", f"Could not find message ({message_id}) in channel ({channel_id})")
                else:
                    self.log.debug(0, "message_preview.on_message", f"Could not find channel ({channel_id})")
            else:
                self.log.debug(0, "message_preview.on_message", f"Guild ({ref_guild_id}) does not match this guild ({guild_id})")
        except Exception as e:
            self.log.error(guild_id, "restricted.on_message", f"{e}", traceback.format_exc())

    async def create_message_preview(self, ctx, message):
        try:
            target_channel = ctx.channel
            author = message.author
            message_content = message.content
            message_url = message.jump_url


            # create the message preview
            embed = await self.discord_helper.sendEmbed(target_channel, "Message Preview", message=message_content, url=message_url, author=author, footer="Message Preview")
        except Exception as e:
            self.log.error(ctx.guild.id, "message_preview.create_message_preview", f"{e}", traceback.format_exc())
def setup(bot):
    bot.add_cog(MessagePreview(bot))
