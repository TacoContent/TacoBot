import os
from warnings import warn

from bot.lib.http.handlers.BaseHttpHandler import BaseHttpHandler
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
class GuildApiHandler(BaseHttpHandler):
    """Deprecated: Responsibilities split into specialized handlers.

    New handlers:
      - GuildLookupApiHandler (lookup, list)
      - GuildChannelsApiHandler (channels, categories)
      - GuildEmojisApiHandler (emojis)
      - GuildRolesApiHandler (roles, mentionables)

    This stub remains for imports that haven’t yet been updated. It performs no routing.
    """
    def __init__(self, bot: TacoBot):  # pragma: no cover
        super().__init__(bot)
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.settings = Settings()
        self.tracking_db = TrackingDatabase()
        warn(
            "GuildApiHandler is deprecated; use GuildLookupApiHandler, GuildChannelsApiHandler, GuildEmojisApiHandler, or GuildRolesApiHandler.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Intentionally no route methods; all moved to new handler classes.
