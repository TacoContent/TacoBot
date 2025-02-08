import inspect
import os

from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.tacobot import TacoBot


class FreeGamesCog(TacobotCog):
    # group = app_commands.Group(name="webhook", description="Webhook Handler")

    def __init__(self, bot: TacoBot):
        super().__init__(bot, "free_games")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.http_server = None

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")


async def setup(bot):
    await bot.add_cog(FreeGamesCog(bot))
