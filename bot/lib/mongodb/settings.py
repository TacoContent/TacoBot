import datetime
import inspect
import os
import traceback
import typing

from bot.lib import utils
from bot.lib.enums import loglevel
from bot.lib.mongodb.basedatabase import BaseDatabase


class SettingsDatabase(BaseDatabase):
    def __init__(self) -> None:
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

    def add_settings(self, guildId: int, name: str, settings: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "name": name, "settings": settings, "timestamp": timestamp}
            # insert the settings for the guild in to the database with key name and timestamp
            self.connection.settings.update_one(
                {"guild_id": str(guildId), "name": name}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

    # add or update a setting value in the settings collection, under the settings property
    def set_setting(self, guildId: int, name: str, key: str, value: typing.Any) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            # get the settings object
            settings = self.get_settings(guildId, name)
            # if the settings object is None, create a new one
            if settings is None:
                settings = {}
            # set the key to the value
            settings[key] = value
            # update the settings object in the database
            self.add_settings(guildId, name, settings)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

    def get_settings(self, guildId: int, name: str) -> typing.Union[dict, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            settings = self.connection.settings.find_one({"guild_id": str(guildId), "name": name})
            # explicitly return None if no settings are found
            if settings is None:
                return None
            # return the settings object
            return settings['settings']
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
        finally:
            if self.connection is not None and self.client is not None:
                self.close()
