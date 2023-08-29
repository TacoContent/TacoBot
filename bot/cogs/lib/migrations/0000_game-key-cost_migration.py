import inspect
import os
import traceback

from bot.cogs.lib.migration_base import MigrationBase  # pylint: disable=relative-beyond-top-level


class Migration(MigrationBase):
    def __init__(self) -> None:
        super().__init__()
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self._version = 0

    def run(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            # update all game keys that don't have a cost to 500
            result = self.connection.game_keys.update_many({"cost": {"$exists": False}}, {"$set": {"cost": 500}})

            self.log.info(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Updated {result.modified_count} game keys with no cost to cost of 500"
            )

            self.track_run(True)
        except Exception as ex:
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Failed to run migration: {ex}",
                stack=traceback.format_exc(),
            )

            self.track_run(False)
