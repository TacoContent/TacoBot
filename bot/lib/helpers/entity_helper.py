import inspect
import os
import traceback
import typing

import discord
from bot.lib import logger, settings
from bot.lib.enums import loglevel


class EntityHelper:
    """Helper for fetching Discord entities (users, members, roles, channels).

    Edge cases handled:
    - Missing IDs/guilds: returns None
    - NotFound from Discord API: logs at warn level and returns None
    - Uses cache-first (get_*) then fetch_* network call as fallback
    """

    def __init__(self, bot) -> None:
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()] if self.settings.log_level else None
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

    async def get_or_fetch_user(self, userId: int) -> typing.Union[discord.User, None]:
        _method = inspect.stack()[0][3]
        try:
            if userId:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    def get_member_id(self, username: str) -> typing.Union[int, None]:
        _method = inspect.stack()[0][3]
        try:
            guilds = self.bot.guilds

            for guild in guilds:
                member = discord.utils.find(
                    lambda m: str(m) == username or m.name == username, guild.members
                )
                if member:
                    return member.id
            return None
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_member(self, guildId: int, userId: int) -> typing.Union[discord.Member, None]:
        _method = inspect.stack()[0][3]
        try:
            if not guildId:
                return None
            guild = self.bot.get_guild(guildId)
            if not guild:
                guild = await self.bot.fetch_guild(guildId)
            if not guild:
                return None

            if userId:
                user = guild.get_member(userId)
                if not user:
                    user = await guild.fetch_member(userId)
                return user
            return None
        except discord.errors.NotFound:
            return None
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    async def get_or_fetch_role(self, guild: discord.Guild, roleId: int) -> typing.Union[discord.Role, None]:
        _method = inspect.stack()[0][3]
        try:
            if not guild:
                return None
            if roleId:
                role = guild.get_role(roleId)
                if not role:
                    roles = [r for r in await guild.fetch_roles() if r.id == roleId]
                    role = roles[0] if roles else None
                return role
            return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", str(nf), traceback.format_exc())
            return None

    async def get_or_fetch_channel(
        self, channelId: int
    ) -> typing.Optional[typing.Union[discord.TextChannel, discord.DMChannel, discord.Thread]]:
        _method = inspect.stack()[0][3]
        try:
            if channelId:
                chan = self.bot.get_channel(channelId)
                if not chan:
                    chan = await self.bot.fetch_channel(channelId)
                return chan
            else:
                return None
        except discord.errors.NotFound as nf:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", str(nf), traceback.format_exc())
            return None
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Channel ID: '{channelId}'")
            try:
                self.log.error(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    f"Bot: '{self.bot.id}' - {getattr(self.bot, 'name', 'Unknown')}",
                )
            except Exception:
                pass
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            return None

    def get_by_name_or_id(self, iterable, nameOrId: typing.Union[int, str]):
        if isinstance(nameOrId, str):
            return discord.utils.get(iterable, name=str(nameOrId))
        elif isinstance(nameOrId, int):
            return discord.utils.get(iterable, id=int(nameOrId))
        else:
            return None
