import datetime
import inspect
import os
import traceback

from bot.cogs.lib import utils
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.mongodb.database import Database


class WhitelistDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def add_user_to_join_whitelist(self, guild_id: int, user_id: int, added_by: int) -> None:
        """Add a user to the join whitelist for a guild."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "added_by": str(added_by),
                "timestamp": timestamp,
            }
            self.connection.join_whitelist.update_one(
                {"guild_id": str(guild_id), "user_id": str(user_id)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_user_join_whitelist(self, guild_id: int) -> list:
        """Get the join whitelist for a guild."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.join_whitelist.find({"guild_id": str(guild_id)}))
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def remove_user_from_join_whitelist(self, guild_id: int, user_id: int) -> None:
        """Remove a user from the join whitelist for a guild."""
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.join_whitelist.delete_one({"guild_id": str(guild_id), "user_id": str(user_id)})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
