import inspect
import os
import traceback

from bot.lib.enums.loglevel import LogLevel
from bot.lib.mongodb.database import Database


class ShiftCodesDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def add_shift_code(self, payload: dict, track: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            code = payload.get("code", None)
            if not code:
                self.log(0, LogLevel.WARNING, f"{self._module}.{self._class}.{_method}", "No code found in payload")
                return
            code = str(code).strip().upper().replace(" ", "")

            # prepare the payload to be added to the tracked_in array
            track_payload = {
                "guild_id": str(track.get("guildId")),
                "channel_id": str(track.get("channelId")),
                "message_id": str(track.get("messageId")),
            }

            self.connection.shift_codes.update_one(  # type: ignore
                {"code": code},
                {
                    "$setOnInsert": payload,
                    "$addToSet": {"tracked_in": track_payload},
                },
                upsert=True,
            )
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return

    def is_code_tracked(self, guild_id: int, code: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            code = str(code).strip().upper().replace(" ", "")

            # find one document where code matches, and "tracked_in" array contains guild_id
            result = self.connection.shift_codes.find_one(  # type: ignore
                {"code": code, "tracked_in": {"$elemMatch": {"guild_id": str(guild_id)}}}
            )
            return result is not None
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return False

    def get_all_untracked_codes(self, guild_id: int, limit: int) -> list[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            results = self.connection.shift_codes.find(  # type: ignore
                {"tracked_in": {"$not": {"$elemMatch": {"guild_id": str(guild_id)}}}},
                limit=limit,
            )
            return list(results)
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return []
