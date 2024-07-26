import inspect
import os
import traceback

from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands


class GuildTrack(TacobotCog):
    def __init__(self, bot):
        super().__init__(bot, "guild_track")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.tracking_db = TrackingDatabase()

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


async def setup(bot):
    await bot.add_cog(GuildTrack(bot))
