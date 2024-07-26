from discord.ext import commands

from bot.lib import logger, settings
from bot.lib.enums import loglevel
from bot.tacobot import TacoBot

class TacobotCog(commands.Cog):
    def __init__(self, bot: TacoBot, settingsSection: str) -> None:
        super().__init__()
        self.bot = bot

        self.SETTINGS_SECTION = settingsSection
        self.settings = settings.Settings()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)

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
