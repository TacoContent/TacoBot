import inspect
import os

from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.helpers import MessageHelper
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot


class FreeGamesCog(TacobotCog):
    # group = app_commands.Group(name="webhook", description="Webhook Handler")

    def __init__(self, bot: TacoBot, messaging: MessageHelper, tracking_db: TrackingDatabase, settings: Settings):
        super().__init__(bot, "free_games", settings=settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.http_server = None

        self.messaging = messaging
        self.tracking_db = tracking_db

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")


async def setup(bot):
    settings = Settings()
    messaging = MessageHelper(bot, settings)
    tracking_db = TrackingDatabase()
    await bot.add_cog(FreeGamesCog(bot=bot, messaging=messaging, tracking_db=tracking_db, settings=settings))
