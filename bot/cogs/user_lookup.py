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
import datetime

import inspect

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import tacotypes
from .lib.member_status import MemberStatus

class UserLookup(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "user_lookup"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_guild_available(self, guild) -> None:
        _method = inspect.stack()[0][3]
        try:
            if guild is None:
                return
            # pull this from the settings and see if we should do the import of all users

            enabled = False
            cog_settings = self.get_cog_settings(guild.id)
            if cog_settings is not None:
                enabled = cog_settings.get("full_import_enabled", False)

            if not enabled:
                return

            self.log.debug(guild.id, f"{self._module}.{_method}", f"Performing full user import for guild {guild.id}")
            for member in guild.members:
                self.log.debug(guild.id, f"{self._module}.{_method}", f"Tracking user {member.name} in guild {guild.name}")
                avatar: typing.Union[str,None] = member.avatar.url if member.avatar is not None else member.default_avatar.url
                self.db.track_user(
                    guildId=guild.id,
                    userId=member.id,
                    username=member.name,
                    discriminator=member.discriminator,
                    avatar=avatar,
                    displayname=member.display_name,
                    created=member.created_at,
                    bot=member.bot,
                    system=member.system,
                    status=MemberStatus.from_discord(member.status),
                )


        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    # on events, get the user id and username and store it in the database
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        _method = inspect.stack()[0][3]
        try:
            if member is None or member.guild is None:
                return
            avatar: typing.Union[str,None] = member.avatar.url if member.avatar is not None else member.default_avatar.url
            self.log.debug(member.guild.id, f"{self._module}.{_method}", f"User {member.id} joined guild {member.guild.id}")
            self.db.track_user(
                guildId=member.guild.id,
                userId=member.id,
                username=member.name,
                discriminator=member.discriminator,
                avatar=avatar,
                displayname=member.display_name,
                created=member.created_at,
                bot=member.bot,
                system=member.system,
                status=MemberStatus.from_discord(member.status),
            )
        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after) -> None:
        _method = inspect.stack()[0][3]
        try:
            if after is None or after.guild is None:
                return
            avatar: typing.Union[str,None] = after.avatar.url if after.avatar is not None else after.default_avatar.url
            self.log.debug(after.guild.id, f"{self._module}.{_method}", f"User {after.id} updated in guild {after.guild.id}")
            self.db.track_user(
                guildId=after.guild.id,
                userId=after.id,
                username=after.name,
                discriminator=after.discriminator,
                avatar=avatar,
                displayname=after.display_name,
                created=after.created_at,
                bot=after.bot,
                system=after.system,
                status=MemberStatus.from_discord(after.status),
            )
        except Exception as e:
            self.log.error(after.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        _method = inspect.stack()[0][3]
        try:
            if message is None or message.guild is None:
                return
            member = message.author
            avatar: typing.Union[str,None] = member.avatar.url if member.avatar is not None else member.default_avatar.url
            if isinstance(member, discord.User):
                member = await self.discord_helper.get_or_fetch_member(message.guild.id, member.id)

            if not member:
                return

            self.db.track_user(
                guildId=message.guild.id,
                userId=member.id,
                username=member.name,
                discriminator=member.discriminator,
                avatar=avatar,
                displayname=member.display_name,
                created=member.created_at,
                bot=member.bot,
                system=member.system,
                status=MemberStatus.from_discord(member.status),
            )
        except Exception as e:
            self.log.error(message.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())


    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

async def setup(bot):
    await bot.add_cog(UserLookup(bot))
