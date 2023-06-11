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
import re

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

            # check if message has a link to the image in it
            media_regex = r"(https:\/\/)((?:cdn|media)\.discordapp\.(?:net|com))\/attachments\/\d+\/\d+\/\w+\.(png|jpe?g|gif|webp)"

            # get the settings from settings
            cog_settings = self.get_cog_settings(guild_id)

            food_channel_list = [c for c in cog_settings.get("channels", []) if str(c["id"]) == str(message.channel.id)]
            food_channel = None
            if food_channel_list:
                food_channel = food_channel_list[0]

            if not food_channel:
                return

            # if the message is not a photo, ignore
            matches = re.search(media_regex, message.content, re.MULTILINE | re.DOTALL | re.UNICODE | re.IGNORECASE)
            if not message.attachments and matches is None:
                self.log.debug(guild_id, "food_photo.on_message", f"Message {message.id} does not contain a photo")
                return

            # # check if the user posted a photo in the channel within the last 5 minutes
            # # if so, ignore
            # now = datetime.datetime.utcnow()
            # five_minutes_ago = now - datetime.timedelta(minutes=5)
            # async for m in message.channel.history(limit=100, after=five_minutes_ago):
            #     if m.author == message.author and m.attachments:
            #         # check if the bot has already added reactions to the message
            #         # if so, ignore
            #         for r in food_channel['reactions']:
            #             if r in [r.emoji for r in m.reactions]:
            #                 self.log.debug(guild_id, "food_photo.on_message", f"User {message.author} already posted a photo in the last 5 minutes")
            #                 self.log.debug(guild_id, "food_photo.on_message", f"Bot already reacted to message {m.id}")
            #                 return

            # this SHOULD get the amount from the `tacos` settings, but it doesn't
            amount = int(food_channel["tacos"] if "tacos" in food_channel else 5)
            amount = amount if amount > 0 else 5

            reason_msg = f"Food photo in #{message.channel.name}"

            for r in food_channel["reactions"]:
                await message.add_reaction(r)

            # if the message is a photo, add tacos to the user
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=message.author,
                reason=reason_msg,
                give_type=tacotypes.TacoTypes.FOOD_PHOTO,
                taco_amount=amount,
            )

            # track the message in the database
            image_url = message.attachments[0].url if message.attachments else matches.group(0)
            self.db.track_food_post(
                guildId=guild_id,
                userId=message.author.id,
                messageId=message.id,
                channelId=message.channel.id,
                message=message.content,
                image=image_url,
            )

            pass
        except Exception as e:
            self.log.error(0, "food_photo.on_message", str(e), traceback.format_exc())
            traceback.print_exc()

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
    await bot.add_cog(FoodPhoto(bot))
