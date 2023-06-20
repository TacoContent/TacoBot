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
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo

import inspect


class MessagePreview(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "message_preview"

        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        guild_id = 0
        _method = inspect.stack()[0][3]
        try:
            # if in a DM, ignore
            if message.guild is None:
                return
            # if the message is from a bot, ignore
            if message.author.bot:
                return
            guild_id = message.guild.id

            pattern = re.compile(r'https:\/\/discord(?:app)?\.com\/channels\/(\d+)\/(\d+)\/(\d+)$', flags=re.MULTILINE | re.IGNORECASE)
            match = pattern.search(message.content)
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
                        await message.delete()
                    else:
                        self.log.debug(0, f"{self._module}.{_method}", f"Could not find message ({message_id}) in channel ({channel_id})")
                else:
                    self.log.debug(0, f"{self._module}.{_method}", f"Could not find channel ({channel_id})")
            else:
                self.log.debug(0, f"{self._module}.{_method}", f"Guild ({ref_guild_id}) does not match this guild ({guild_id})")
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    async def create_message_preview(self, ctx, message) -> discord.Message:
        _method = inspect.stack()[0][3]
        try:
            guild_id = message.guild.id
            target_channel = ctx.channel
            author = message.author
            message_content = message.content
            message_url = message.jump_url
            created = message.created_at
            embed_content = ""
            embed_title = self.settings.get_string(guild_id, "message_preview_title")
            embed_thumbnail = None
            embed_color = None
            fields = []
            file_attachments = []
            embed_image = None
            if message.embeds:
                e = message.embeds[0]
                if e.description != "" and e.description is not None:
                    embed_content = e.description
                if e.title != "" and e.title is not None:
                    embed_title = e.title
                if e.color is not None:
                    embed_color = e.color


                if message.attachments:
                    for a in message.attachments:
                        self.log.debug(guild_id, f"{self._module}.{_method}", f"Found attachment: {a.url}")
                        file_attachments.append(discord.File(a.url))

                for f in e.fields:
                    fields.append({ "name": f.name, "value": f.value, "inline": f.inline })
                if e.thumbnail:
                    embed_thumbnail = e.thumbnail.url
                if e.image:
                    embed_image = e.image.url

            # create the message preview
            embed = await self.discord_helper.send_embed(target_channel,
                embed_title,
                message=f"{message_content}\n\n{embed_content}",
                thumbnail=embed_thumbnail,
                fields=fields,
                url=message_url,
                author=author,
                color=embed_color,
                image=embed_image,
                files=file_attachments,
                footer=self.settings.get_string(guild_id, "message_preview_footer", created=created.strftime('%Y-%m-%d %H:%M:%S')))
            return embed
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())
            raise e


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
    await bot.add_cog(MessagePreview(bot))
