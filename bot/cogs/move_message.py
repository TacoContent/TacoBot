# this is a cog that will allow admins to move messages to another channel
# this doesn't actually move the message. The bot will delete the original message
# and send the message to the new channel with the same content as the original.
# it will identify the original author in the new embeded message that is sent by the bot.

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
import inspect
import uuid
import datetime

from discord.ext.commands.cooldowns import BucketType
from interactions import ComponentContext
# from interactions import Button
# from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
# from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import models
from .lib import settings
from .lib import mongo
from .lib import dbprovider

class MoveMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)

        self.SETTINGS_SECTION = "move_message"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "move_message.__init__", "Initialized")

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

            react_member = await self.discord_helper.get_or_fetch_member(guild_id, user.id)
            if react_member.guild_permissions.manage_messages:
                self.log.debug(guild_id, _method, f"{user.name} reacted to message {message.id} with {str(payload.emoji)}")
                if str(payload.emoji) == '⏭️':
                    ctx = self.discord_helper.create_context(bot=self.bot, message=message, channel=channel, author=user, guild=message.guild)
                    target_channel = await self.discord_helper.ask_channel(ctx, "Choose Target Channel", "Please select the channel you want to move the message to.", timeout=60)
                    if target_channel is None:
                        return

                    await self.discord_helper.move_message(message, targetChannel=target_channel, author=message.author, who=react_member, reason="Moved by admin")
                    await message.delete()

        except Exception as e:
            self.log.error(guild_id, "move_message.on_raw_reaction_add", str(e), traceback.format_exc())
            return

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def move(self, ctx, messageId: int):
        if ctx.invoked_subcommand is not None:
            return

        try:
            _method = inspect.stack()[0][3]
            if ctx.guild is None:
                return
            await ctx.message.delete()
            guild_id = ctx.guild.id
            self.log.debug(guild_id, _method, f"{ctx.author.name} called move message {messageId}")
            channel = ctx.channel

            message = await ctx.channel.fetch_message(messageId)
            if message is None:
                await self.discord_helper.sendEmbed(channel, "Move Message", f"{ctx.author.mention}, the message id ({messageId}) was not found.", color=0xff0000, delete_after=20)
                return
            ctx = self.discord_helper.create_context(bot=self.bot, message=message, channel=channel, author=message.author, guild=ctx.guild)
            target_channel = await self.discord_helper.ask_channel(ctx, "Choose Target Channel", "Please select the channel you want to move the message to.", timeout=60)
            if target_channel is None:
                return

            await self.discord_helper.move_message(message, targetChannel=target_channel, author=message.author, who=ctx.author, reason="Moved by admin")
            await message.delete()
        except Exception as e:
            self.log.error(ctx.guild.id, "move.move", str(e), traceback.format_exc())
            return

    # @move.command()
    # @commands.has_permissions(administrator=True)
    # async def help(self, ctx):
    #     guild_id = 0
    #     if ctx.guild:
    #         guild_id = ctx.guild.id
    #         await ctx.message.delete()
    #     await self.discord_helper.sendEmbed(ctx.channel,
    #         self.settings.get_string(guild_id, "help_title", bot_name=self.settings.name),
    #         self.settings.get_string(guild_id, "help_module_message", bot_name=self.settings.name, command="move"),
    #         footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
    #         color=0xff0000, delete_after=30)
    #     pass
async def setup(bot):
    await bot.add_cog(MoveMessage(bot))
