import typing

from bot.lib import logger
from bot.lib.enums import loglevel
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from discord.ext import commands


class TacobotCog(commands.Cog):
    def __init__(self, bot: TacoBot, settingsSection: str, settings: typing.Optional[Settings] = None) -> None:
        super().__init__()
        self.bot = bot

        self.SETTINGS_SECTION = settingsSection
        self.settings = settings or Settings()

        log_level = loglevel.LogLevel.DEBUG  # Default fallback
        try:
            log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        except KeyError:
            # Invalid log level string, keep default DEBUG
            pass

        self.log = logger.Log(minimumLogLevel=log_level)

    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            # check for global settings
            cog_settings = self.settings.get_settings(0, section)
        # if we still dont have settings, raise an error
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId} or globally.")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section="tacos")
