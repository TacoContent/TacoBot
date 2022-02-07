# this watches channels, and requires a user to have tacos to post in the channel

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

class TacoPost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.CHANNELS = [
            { "id": 935318426677825536, "cost": 10 }, # bot-spam channel (for testing)
        ]

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "tacopost.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "tacopost.__init__", f"Logger initialized with level {log_level.name}")

    @commands.Cog.listener()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        guild_id = message.guild.id
        user = message.author
        channel = message.channel
        try:
            if message.author.bot:
                return
            # if channel.id is not in CHANNELS[].id return
            if channel.id not in [c['id'] for c in self.CHANNELS]:
                return

            prefix = await self.bot.get_prefix(message)
            # if the message starts with one of the items in the array self.bot.command_prefix, exit the function
            if any(message.content.startswith(p) for p in prefix):
                return
            # get required tacos cost for channel in CHANNELS[]
            taco_cost = [c for c in self.CHANNELS if c['id'] == channel.id][0]['cost']
            # get tacos count for user
            taco_count = self.db.get_tacos_count(guild_id, user.id)
            # if user has doesnt have enough tacos, send a message, and delete their message
            if taco_count < taco_cost:
                await self.discord_helper.sendEmbed(channel, "Not Enough Tacos", f"{user.mention}, You need {taco_cost} tacos to post in this channel.", delete_after=15)
                await message.delete()
            else:
                choice = await self.discord_helper.ask_yes_no(message, f"{user.mention}, Are you sure you want to post in this channel?\n\n**It will cost you {taco_cost} tacos 🌮.**\n\nYou currently have {taco_count} tacos 🌮.", "Use tacos to post?")
                if choice:
                    # remove the tacos from the user
                    self.db.remove_tacos(guild_id, user.id, taco_cost)
                    # send the message that tacos have been removed
                    await self.discord_helper.sendEmbed(channel, "Tacos Removed", f"{user.mention}, You have been charged {taco_cost} tacos from your account.", delete_after=10)
                else:
                    await self.discord_helper.sendEmbed(channel, "Message Removed", f"{user.mention}, You chose to not use your tacos, your message has been removed.", delete_after=10)
                    await message.delete()
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())

def setup(bot):
    bot.add_cog(TacoPost(bot))
