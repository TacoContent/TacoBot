import typing

from bot.cogs.lib import loglevel, mongo
from bot.cogs.lib.colors import Colors

class Log:
    def __init__(self, minimumLogLevel: loglevel.LogLevel = loglevel.LogLevel.DEBUG) -> None:
        self.db = mongo.MongoDatabase()
        self.minimum_log_level = minimumLogLevel
        pass

    def __write(
        self, guildId: int, level: loglevel.LogLevel, method: str, message: str, stack: typing.Optional[str] = None
    ) -> None:

        color = Colors.get_color(level)
        m_level = Colors.colorize(color, f"[{level.name}]", bold=True)
        m_method = Colors.colorize(Colors.HEADER, f"[{method}]", bold=False)
        m_message = f"{Colors.colorize(color, message)}"
        m_guild = Colors.colorize(Colors.OKGREEN, f"[{guildId}]", bold=False)
        str_out = f"{m_level} {m_method} {m_guild} {m_message}"
        print(str_out)
        if stack:
            print(Colors.colorize(color, stack))

        # print(f"[{level.name}] [{method}] [guild:{str(guildId)}] {message}")
        # if stack:
        #     print(stack)
        if level >= self.minimum_log_level:
            self.db.insert_log(guildId=guildId, level=level, method=method, message=message, stack=stack)

    def debug(self, guildId: int, method: str, message: str, stack: typing.Optional[str] = None) -> None:
        self.__write(guildId=guildId, level=loglevel.LogLevel.DEBUG, method=method, message=message, stack=stack)

    def info(self, guildId: int, method: str, message: str, stack: typing.Optional[str] = None) -> None:
        self.__write(guildId=guildId, level=loglevel.LogLevel.INFO, method=method, message=message, stack=stack)

    def warn(self, guildId: int, method: str, message: str, stack: typing.Optional[str] = None) -> None:
        self.__write(guildId=guildId, level=loglevel.LogLevel.WARNING, method=method, message=message, stack=stack)

    def error(self, guildId: int, method: str, message: str, stack: typing.Optional[str] = None) -> None:
        self.__write(guildId=guildId, level=loglevel.LogLevel.ERROR, method=method, message=message, stack=stack)

    def fatal(self, guildId: int, method: str, message: str, stack: typing.Optional[str] = None) -> None:
        self.__write(guildId=guildId, level=loglevel.LogLevel.FATAL, method=method, message=message, stack=stack)
