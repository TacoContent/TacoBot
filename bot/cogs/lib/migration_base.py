import os
import traceback

from bot.cogs.lib import settings  # pylint: disable=no-name-in-module
from pymongo import MongoClient


class MigrationBase:
    def __init__(self) -> None:
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.client = None
        self.connection = None

    def open(self) -> None:
        if not self.settings.db_url:
            raise ValueError("MONGODB_URL is not set")
        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client.tacobot

    def close(self) -> None:
        try:
            if self.client:
                self.client.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def run(self) -> None:
        pass

    def needs_run(self) -> bool:
        if self.connection is None:
            self.open()

        try:
            run = self.connection.migration_runs.find_one({"module": self._module})
            if run is None:
                return True
            else:
                return not run["completed"]
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection is not None:
                self.close()

    def track_run(self, success: bool) -> None:
        if self.connection is None:
            self.open()

        try:
            self.connection.migration_runs.update_one(
                {"module": self._module}, {"$set": {"completed": success}}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection is not None:
                self.close()
