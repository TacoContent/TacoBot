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
import datetime

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider
from .lib import tacotypes


class FoodPhoto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "food_photo"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "food_photo.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if message.guild is not None:
                guild_id = message.guild.id
            # if the message is from a bot, ignore
            if message.author.bot:
                return
            # get the settings from settings
            food_settings = self.settings.get_settings(self.db, message.guild.id, self.SETTINGS_SECTION)
            if not food_settings:
                # raise exception if there are no settings
                self.log.debug(guild_id, "food_photo.on_message", f"No settings found for guild {guild_id}")
                await self.discord_helper.notify_bot_not_initialized(message, "food_photo")
                return

            food_channel = [c for c in food_settings["channels"] if str(c["id"]) == str(message.channel.id)]
            if food_channel:
                food_channel = food_channel[0]

            if not food_channel:
                return

            # if the message is not a photo, ignore
            if not message.attachments:
                return


            # check if the user posted a photo in the channel within the last 5 minutes
            # if so, ignore
            now = datetime.datetime.utcnow()
            five_minutes_ago = now - datetime.timedelta(minutes=5)
            async for m in message.channel.history(limit=100, after=five_minutes_ago):
                if m.author == message.author and m.attachments:
                    # check if the bot has already added reactions to the message
                    # if so, ignore
                    for r in food_channel['reactions']:
                        if r in [r.emoji for r in m.reactions]:
                            self.log.debug(guild_id, "food_photo.on_message", f"User {message.author} already posted a photo in the last 5 minutes")
                            self.log.debug(guild_id, "food_photo.on_message", f"Bot already reacted to message {m.id}")
                            return

            amount = int(food_channel["tacos"] if "tacos" in food_channel else 5)
            amount = amount if amount > 0 else 5

            reason_msg = f"Food photo in #{message.channel.name}"

            for r in food_channel['reactions']:
                await message.add_reaction(r)

            # if the message is a photo, add tacos to the user
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=message.author,
                reason=reason_msg,
                give_type=tacotypes.TacoTypes.CUSTOM,
                taco_amount=amount,
            )

            pass
        except Exception as e:
            self.log.error(0, "food_photo.on_message", f"Exception: {e}")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(FoodPhoto(bot))
