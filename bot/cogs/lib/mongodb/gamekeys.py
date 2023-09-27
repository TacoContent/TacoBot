import datetime
import inspect
import traceback
import os
import typing

from bot.cogs.lib import loglevel, utils
from bot.cogs.lib.mongodb.database import Database


class GameKeysDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def find_open_game_key_offer(self, guild_id: int, channel_id: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.game_key_offers.find_one(
                {"guild_id": str(guild_id), "channel_id": str(channel_id)}
            )
            if result:
                return result
            return None
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def open_game_key_offer(
        self,
        game_key_id: str,
        guild_id: int,
        message_id: int,
        channel_id: int,
        expires: typing.Optional[datetime.datetime] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            if expires:
                expires_ts = utils.to_timestamp(expires)
            else:
                # 1 day
                expires_ts = timestamp + 86400

            payload = {
                "guild_id": str(guild_id),
                "game_key_id": str(game_key_id),
                "message_id": str(message_id),
                "channel_id": str(channel_id),
                "timestamp": timestamp,
                "expires": expires_ts,
            }
            self.connection.game_key_offers.update_one(
                {"guild_id": str(guild_id), "game_key_id": game_key_id}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def close_game_key_offer_by_message(self, guild_id: int, message_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_key_offers.delete_one({"guild_id": str(guild_id), "message_id": str(message_id)})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def close_game_key_offer(self, guild_id: int, game_key_id: str) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_key_offers.delete_one({"guild_id": str(guild_id), "game_key_id": game_key_id})
        except Exception as ex:
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def claim_game_key_offer(self, game_key_id: str, user_id: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"redeemed_by": str(user_id), "redeemed_timestamp": timestamp}
            self.connection.game_keys.update_one({"_id": ObjectId(game_key_id)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.FATAL,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            raise ex

    def get_game_key_data(self, game_key_id: str) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.game_keys.find_one({"_id": ObjectId(game_key_id)})
            if result:
                return result
            return None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_random_game_key_data(self, guild_id: int) -> typing.Optional[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.game_keys.aggregate(
                [{"$match": {"redeemed_by": None, "guild_id": str(guild_id)}}, {"$sample": {"size": 1}}]
            )
            records = list(result)
            if records and len(records) > 0:
                record = records[0]
                return {
                    "id": record["_id"],
                    "title": record["title"],
                    "platform": record["type"],
                    "info_url": record["info_link"] or "",
                    "offered_by": record["user_owner"],
                }
            return None
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
