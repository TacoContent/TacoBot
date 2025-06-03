import inspect
import os
import sys
import traceback
import typing

from bot.lib import utils
from bot.lib.colors import Colors
from bot.lib.enums import loglevel
from pymongo import MongoClient


class BaseDatabase:
    def __init__(self) -> None:
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.client = None
        self.connection = None
        self.database_name = "tacobot"
        self.db_url = utils.dict_get(
            os.environ, "MONGODB_URL", default_value=f"mongodb://localhost:27017/{self.database_name}"
        )

    def open(self) -> None:
        if not self.db_url:
            raise ValueError("MONGODB_URL is not set")

        self.client = MongoClient(self.db_url)
        self.connection = self.client[self.database_name]

    def close(self) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.client:
                self.client.close()
            self.client = None
            self.connection = None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to close connection: {ex}",
                stackTrace=traceback.format_exc(),
            )

    def log(
        self,
        guildId: typing.Optional[int],
        level: loglevel.LogLevel,
        method: str,
        message: str,
        stackTrace: typing.Optional[str] = None,
        outIO: typing.Optional[typing.IO] = None,
        colorOverride: typing.Optional[str] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        if guildId is None:
            guildId = 0
        if colorOverride is None:
            color = Colors.get_color(level)
        else:
            color = colorOverride

        m_level = Colors.colorize(color, f"[{level.name}]", bold=True)
        m_method = Colors.colorize(Colors.HEADER, f"[{method}]", bold=True)
        m_guild = Colors.colorize(Colors.OKGREEN, f"[{guildId}]", bold=True)
        m_message = f"{Colors.colorize(color, message)}"

        str_out = f"{m_level} {m_method} {m_guild} {m_message}"
        if outIO is None:
            stdoe = sys.stdout if level < loglevel.LogLevel.ERROR else sys.stderr
        else:
            stdoe = outIO

        print(str_out, file=stdoe)
        if stackTrace:
            print(Colors.colorize(color, stackTrace), file=stdoe)
        try:
            if level >= loglevel.LogLevel.INFO:
                self.insert_log(guildId=guildId, level=level, method=method, message=message, stack=stackTrace)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.PRINT,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Unable to log to database: {ex}",
                stackTrace=traceback.format_exc(),
                outIO=sys.stderr,
                colorOverride=Colors.FAIL,
            )
        finally:
            if self.connection is not None and self.client is not None:
                self.close()

    def insert_log(
        self, guildId: int, level: loglevel.LogLevel, method: str, message: str, stack: typing.Optional[str] = None
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "timestamp": utils.get_timestamp(),
                "level": level.name,
                "method": method,
                "message": message,
                "stack_trace": stack if stack else "",
            }
            self.connection.logs.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.PRINT,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to insert log: {ex}",
                stackTrace=traceback.format_exc(),
                outIO=sys.stderr,
                colorOverride=Colors.FAIL,
            )
        finally:
            if self.connection is not None and self.client is not None:
                self.close()
