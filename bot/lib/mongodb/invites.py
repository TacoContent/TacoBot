import datetime
import inspect
import os
import traceback
import typing

from bot.lib import utils
from bot.lib.enums import loglevel
from bot.lib.mongodb.database import Database


class InvitesDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def track_invite_code(self, guildId: int, inviteCode: str, inviteInfo: dict, userInvite: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "code": inviteCode, "info": inviteInfo, "timestamp": timestamp}
            if userInvite is None:
                self.connection.invite_codes.update_one(
                    {"guild_id": str(guildId), "code": inviteCode}, {"$set": payload}, upsert=True
                )
            else:
                self.connection.invite_codes.update_one(
                    {"guild_id": str(guildId), "code": inviteCode},
                    {"$set": payload, "$push": {"invites": userInvite}},
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

    # unused?
    def get_invite_code(self, guildId: int, inviteCode: str) -> typing.Any:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.invite_codes.find_one({"guild_id": str(guildId), "code": inviteCode})
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
