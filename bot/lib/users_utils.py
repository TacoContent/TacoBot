import inspect
import os
import traceback
import typing

from bot.lib import logger, settings
from bot.lib.enums import loglevel
from bot.lib.mongodb.twitch import TwitchDatabase


class UsersUtils:
    def __init__(self):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = settings.Settings()

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

        self.twitch_db = TwitchDatabase()

    def twitch_user_to_discord_user(self, twitch_user: str) -> typing.Optional[int]:
        _method = inspect.stack()[0][3]
        try:
            twitch_user_id = self.twitch_db.get_user_id_from_twitch_name(twitch_user)
            if twitch_user_id:
                return twitch_user_id
            return None
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def clean_twitch_channel_name(self, channel: typing.Optional[str]) -> str:
        if channel is None:
            return ""

        return channel.lower().strip().replace("#", "").replace("@", "")
