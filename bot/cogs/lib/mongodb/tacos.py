import datetime
import inspect
import os
import traceback
import typing

from bot.cogs.lib import settings, utils
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.mongodb.database import Database


class TacosDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    # Tacos
    def remove_all_tacos(self, guildId: int, userId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Removing tacos for user {userId}",
            )
            self.connection.tacos.delete_many({"guild_id": str(guildId), "user_id": str(userId)})
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def add_tacos(self, guildId: int, userId: int, count: int) -> int:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            user_tacos = self.get_tacos_count(guildId, userId)
            if user_tacos is None:
                self.log(
                    guildId=guildId,
                    level=loglevel.LogLevel.DEBUG,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"User {userId} not in table",
                )
                user_tacos = 0
            else:
                user_tacos = user_tacos or 0
                self.log(
                    guildId=guildId,
                    level=loglevel.LogLevel.DEBUG,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"User {userId} has {user_tacos} tacos",
                )

            user_tacos += count
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"User {userId} has {user_tacos} tacos",
            )
            self.connection.tacos.update_one(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": {"count": user_tacos}}, upsert=True
            )
            return user_tacos
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return 0

    def remove_tacos(self, guildId: int, userId: int, count: int):
        _method = inspect.stack()[0][3]
        try:
            if count < 0:
                self.log(
                    guildId=guildId,
                    level=loglevel.LogLevel.DEBUG,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"Count is less than 0",
                )
                return 0
            if self.connection is None or self.client is None:
                self.open()

            user_tacos = self.get_tacos_count(guildId, userId)
            if user_tacos is None:
                self.log(
                    guildId=guildId,
                    level=loglevel.LogLevel.DEBUG,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"User {userId} not in table",
                )
                user_tacos = 0
            else:
                user_tacos = user_tacos or 0
                self.log(
                    guildId=guildId,
                    level=loglevel.LogLevel.DEBUG,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"User {userId} has {user_tacos} tacos",
                )

            user_tacos -= count
            if user_tacos < 0:
                user_tacos = 0

            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"User {userId} now has {user_tacos} tacos",
            )
            self.connection.tacos.update_one(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": {"count": user_tacos}}, upsert=True
            )
            return user_tacos
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_tacos_count(self, guildId: int, userId: int) -> typing.Union[int, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            data = self.connection.tacos.find_one({"guild_id": str(guildId), "user_id": str(userId)})
            if data is None:
                self.log(
                    guildId=guildId,
                    level=loglevel.LogLevel.DEBUG,
                    method=f"{self._module}.{self._class}.{_method}",
                    message=f"User {userId} not in table",
                )
                return None
            return data['count']
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_total_gifted_tacos(self, guildId: int, userId: int, timespan_seconds: int = 86400) -> int:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            data = self.connection.taco_gifts.find(
                {"guild_id": str(guildId), "user_id": str(userId), "timestamp": {"$gt": timestamp - timespan_seconds}}
            )
            if data is None:
                return 0
            # add up all the gifts from the count column
            total_gifts = 0
            for gift in data:
                total_gifts += gift['count']
            return total_gifts
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

            return 0

    def add_taco_gift(self, guildId: int, userId: int, count: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "user_id": str(userId), "count": count, "timestamp": timestamp}
            # add the gift
            self.connection.taco_gifts.insert_one(payload)
            return True

        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def add_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "timestamp": timestamp,
            }
            # log entry for the user
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Adding taco reaction for user {userId}",
            )
            self.connection.tacos_reactions.update_one(
                {"guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp},
                {"$set": payload},
                upsert=True,
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int) -> typing.Union[dict, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            reaction = self.connection.tacos_reactions.find_one(
                {
                    "guild_id": str(guildId),
                    "user_id": str(userId),
                    "channel_id": str(channelId),
                    "message_id": str(messageId),
                }
            )
            if reaction is None:
                return None
            return reaction
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_tacos_log(self, guildId: int, fromUserId: int, toUserId: int, count: int, type: str, reason: str) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "from_user_id": str(fromUserId),
                "to_user_id": str(toUserId),
                "count": count,
                "type": type,
                "reason": reason,
                "timestamp": timestamp,
            }

            self.connection.tacos_log.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
