import inspect
import os
import traceback
import typing

from bot.lib.enums.loglevel import LogLevel
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.database import Database


class PullTabTicketsDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def save_ticket(self, payload: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            # save ticket payload (guard belongs in update_ticket)

            code = payload.get("code", None)
            if not code:
                self.log(0, LogLevel.WARNING, f"{self._module}.{self._class}.{_method}", "No code found in payload")
                return
            code = str(code)
            user_id = str(payload.get("user_id", ""))
            guild_id = str(payload.get("guild_id", ""))

            self.connection.pulltab_tickets.update_one(  # type: ignore
                {"code": code, "user_id": user_id, "guild_id": guild_id}, {"$setOnInsert": payload}, upsert=True
            )
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return

    def update_ticket(self, guild_id: int, user_id: int, code: str, updates: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            # guard: if updates is empty, don't call update_one
            if not updates:
                self.log(0, LogLevel.WARNING, f"{self._module}.{self._class}.{_method}", "No updates provided")
                return

            self.connection.pulltab_tickets.update_one(  # type: ignore
                {"code": code, "user_id": str(user_id), "guild_id": str(guild_id)}, {"$set": updates}
            )
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return

    def get_ticket(self, guild_id: int, user_id: int, code: str) -> typing.Optional[PullTabTicketEntry]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            code = str(code)

            result = self.connection.pulltab_tickets.find_one(  # type: ignore
                {"code": code, "user_id": str(user_id), "guild_id": str(guild_id)}
            )
            if result:
                # Use the model's `from_dict` helper to build a validated model
                # This ensures only supported fields are used and types are validated.
                return PullTabTicketEntry.from_dict(result)

            return None
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return None

    def is_ticket_redeemed(self, guild_id: int, user_id: int, code: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            code = str(code)
            # check if a ticket with the given code, user_id, and guild_id exists and has a non-null redeemed_at
            # if it is found, it means the ticket has been redeemed
            # if not found, it means the ticket has not been redeemed, but may or may not exist
            result = self.connection.pulltab_tickets.find_one(  # type: ignore
                {"code": code, "user_id": str(user_id), "guild_id": str(guild_id), "redeemed_at": {"$ne": None}}
            )
            return result is not None
        except Exception as e:
            self.log(0, LogLevel.ERROR, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())
            return False
