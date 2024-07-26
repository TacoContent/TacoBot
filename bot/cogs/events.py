import inspect
import os
import traceback

from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from discord.ext import commands


class Events(TacobotCog):
    def __init__(self, bot):
        super().__init__(bot, "tacobot")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

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


async def setup(bot):
    await bot.add_cog(Events(bot))
