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

class NewAccountCheck(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.SETTINGS_SECTION = "account_age_check"
        self.MINIMUM_ACCOUNT_AGE = 30 # days
        self.ACCOUNT_WHITE_LIST = []
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{_method}", "Initialized")


    @commands.Cog.listener()
    async def on_ready(self) -> None:
        pass
        # self.MINIMUM_ACCOUNT_AGE = self.settings.get_setting(self.SETTINGS_SECTION, "minimum_account_age", 30)
    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs) -> None:
        _method = inspect.stack()[0][3]
        self.log.error(0, f"{self._module}.{_method}", f"{str(event)}", traceback.format_exc())


    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        guild_id = member.guild.id
        _method = inspect.stack()[0][3]
        try:
            # check if the member is in the white list
            if member.id in self.ACCOUNT_WHITE_LIST:
                return

            self.log.debug(guild_id, f"{self._module}.{_method}", f"Member {utils.get_user_display_name(member)} joined {member.guild.name}")
            # check if the member has an account that is newer than the threshold
            member_created = member.created_at.timestamp()
            now = datetime.datetime.now().timestamp()
            age = now - member_created
            age_days = math.floor(age / 86400)
            if age_days < self.MINIMUM_ACCOUNT_AGE:
                self.log.error(guild_id, f"{self._module}.{_method}", f"Member {utils.get_user_display_name(member)} (ID: {member.id}) account age is less than {self.MINIMUM_ACCOUNT_AGE} days.")
                # kick the member
                # await member.kick(reason=f"New Account: account age ({age_days} days) is less than required minimum of {self.MINIMUM_ACCOUNT_AGE} days.")
            else:
                self.log.warn(guild_id, f"{self._module}.{_method}", f"Member {utils.get_user_display_name(member)} (ID: {member.id}) account age is {age_days} days.")
            return
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", str(e), traceback.format_exc())

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
    await bot.add_cog(NewAccountCheck(bot))
