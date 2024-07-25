import inspect
import os
import traceback

import discord
from bot.lib import logger, settings
from bot.lib.enums import loglevel
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.SETTINGS_SECTION = "tacobot"
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_ready(self):
        _method = inspect.stack()[0][3]
        self.log.debug(
            0, f"{self._module}.{self._class}.{_method}", f"Logged in as {self.bot.user.name}:{self.bot.user.id}"
        )

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        pass

    @commands.Cog.listener()
    async def on_disconnect(self):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Bot Disconnected")

    @commands.Cog.listener()
    async def on_resumed(self):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Bot Session Resumed")

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        _method = inspect.stack()[0][3]
        self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(event)}", traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section="tacos")


async def setup(bot):
    await bot.add_cog(Events(bot))
