import inspect
import os
import traceback

from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel
from bot.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands


class GuildTrack(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "guild_track"
        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_guild_available(self, guild) -> None:
        _method = inspect.stack()[0][3]
        try:
            if guild is None:
                return

            self.log.debug(guild.id, f"{self._module}.{self._class}.{_method}", f"Guild ({guild.id}) is available")
            self.tracking_db.track_guild(guild=guild)
        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_guild_update(self, before, after) -> None:
        _method = inspect.stack()[0][3]
        try:
            if after is None:
                return

            self.log.debug(before.id, f"{self._module}.{self._class}.{_method}", f"Guild ({before.id}) is updated")
            self.tracking_db.track_guild(guild=after)
        except Exception as e:
            self.log.error(before.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

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
    await bot.add_cog(GuildTrack(bot))
