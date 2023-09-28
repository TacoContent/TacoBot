import inspect
import os
import traceback

from bot.cogs.lib import logger, settings
from pymongo import MongoClient

from bot.cogs.lib.enums import loglevel


class MigrationBase:
    def __init__(self) -> None:
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        self.log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        self.log = logger.Log(minimumLogLevel=self.log_level)

    def open(self) -> None:
        if not self.settings.db_url:
            raise ValueError("MONGODB_URL is not set")
        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client.tacobot

    def close(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.client:
                self.client.close()
        except Exception as ex:
            self.log.error(
                guildId=0,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to close connection: {ex}",
                stack=traceback.format_exc(),
            )
    def run(self) -> None:
        pass

    def needs_run(self) -> bool:
        _method = inspect.stack()[0][3]
        if self.connection is None:
            self.open()

        try:
            run = self.connection.migration_runs.find_one({"module": self._module})
            if run is None:
                return True
            else:
                return not run["completed"]
        except Exception as ex:
            self.log.error(
                guildId=0,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to determine if migration needs running: {ex}",
                stack=traceback.format_exc(),
            )
            return False

    def track_run(self, success: bool) -> None:
        _method = inspect.stack()[0][3]
        if self.connection is None:
            self.open()

        try:
            self.connection.migration_runs.update_one(
                {"module": self._module}, {"$set": {"completed": success}}, upsert=True
            )
        except Exception as ex:
            self.log.error(
                guildId=0,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to track migration run: {ex}",
                stack=traceback.format_exc(),
            )
