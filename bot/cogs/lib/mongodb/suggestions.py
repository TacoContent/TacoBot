import datetime
import inspect
import traceback
import os
import typing

from bot.cogs.lib import loglevel, utils
from bot.cogs.lib.mongodb.database import Database


class SuggestionsDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    # unused?
    def add_suggestion_create_message(self, guildId: int, channelId: int, messageId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "timestamp": timestamp,
            }
            # log entry for the user
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.DEBUG,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Adding suggestion create message for guild {guildId}",
            )
            self.connection.suggestion_create_messages.update_one(
                {"guild_id": str(guildId), "channel_id": str(channelId), "message_id": messageId},
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

    # unused?
    def remove_suggestion_create_message(self, guildId: int, channelId: int, messageId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            self.connection.suggestion_create_messages.delete_one(
                {
                    "guild_id": str(guildId),
                    "channel_id": str(channelId),
                    "message_id": str(messageId),
                    "timestamp": timestamp,
                }
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_suggestion(self, guildId: int, messageId: int) -> typing.Union[dict, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({"guild_id": str(guildId), "message_id": str(messageId)})
            # explicitly return None if no suggestion is found
            if suggestion is None:
                return None
            # return the suggestion object
            return suggestion
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    # unused?
    def get_suggestion_by_id(self, guildId: int, suggestionId: str) -> typing.Union[dict, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({"guild_id": str(guildId), "id": str(suggestionId)})
            # explicitly return None if no suggestion is found
            if suggestion is None:
                return None
            # return the suggestion object
            return suggestion
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def set_state_suggestion_by_id(self, guildId: int, suggestionId: str, state: str, userId: int, reason: str) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "id": suggestionId, "state": state.upper().strip()}
            # insert the suggestion into the database
            action_payload = {
                "state": state.upper().strip(),
                "user_id": str(userId),
                "reason": reason,
                "timestamp": timestamp,
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "id": str(suggestionId)},
                {"$set": payload, "$push": {"actions": action_payload}},
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
    def set_state_suggestion(self, guildId: int, messageId: int, state: str, userId: int, reason: str) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "message_id": str(messageId), "state": state.upper().strip()}
            action_payload = {
                "state": state.upper().strip(),
                "user_id": str(userId),
                "reason": reason,
                "timestamp": timestamp,
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "message_id": str(messageId)},
                {"$set": payload, "$push": {"actions": action_payload}},
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

    def has_user_voted_on_suggestion(self, suggestionId: str, userId: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({"id": str(suggestionId)})
            if suggestion is None:
                return False
            if suggestion['votes'] is None:
                return False
            if str(userId) in [v['user_id'] for v in suggestion['votes']]:
                return True
            return False
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def unvote_suggestion_by_id(self, guildId: int, suggestionId: str, userId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "id": str(suggestionId)},
                {"$pull": {"votes": {"user_id": str(userId)}}},
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
    def unvote_suggestion(self, guildId: int, messageId: int, userId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "message_id": str(messageId)},
                {"$push": {"votes": {"user_id": str(userId)}}},
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

    def get_suggestion_votes_by_id(self, suggestionId: str) -> typing.Union[dict, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({"id": str(suggestionId)})
            if suggestion is None:
                return None
            return suggestion['votes']
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    # unused?
    def vote_suggestion(self, guildId: int, messageId: int, userId: int, vote: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            vote = vote if vote in [1, -1] else 0
            payload = {"user_id": userId, "vote": vote, "timestamp": timestamp}
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "message_id": str(messageId)}, {"$push": {"votes": payload}}, upsert=True
            )
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def vote_suggestion_by_id(self, suggestionId: str, userId: int, vote: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            vote = vote if vote in [1, -1] else 0
            payload = {"user_id": str(userId), "vote": vote, "timestamp": timestamp}
            # insert the suggestion into the database
            self.connection.suggestions.update_one({"id": suggestionId}, {"$push": {"votes": payload}}, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def add_suggestion(self, guildId: int, messageId: int, suggestion: dict) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            suggestion_data = utils.dict_get(suggestion, "suggestion", {})
            payload = {
                "id": utils.dict_get(suggestion, 'id', uuid.uuid4().hex),
                "guild_id": str(guildId),
                "author_id": str(utils.dict_get(suggestion, "author_id", None)),
                "message_id": str(messageId),
                "actions": [],
                "votes": [],
                "suggestion": suggestion_data,
                "state": utils.dict_get(suggestion, 'state', 'ACTIVE').upper().strip(),
                "timestamp": timestamp,
            }
            # insert the suggestion for the guild in to the database with key name and timestamp
            self.connection.suggestions.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def delete_suggestion_by_id(self, guildId: int, suggestionId: str, userId: int, reason: str) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            states = models.SuggestionStates()
            state = states.DELETED
            action_payload = {
                "state": state.upper().strip(),
                "user_id": str(userId),
                "reason": reason,
                "timestamp": timestamp,
            }
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "id": str(suggestionId)},
                {"$set": {"state": state}, "$push": {"actions": action_payload}},
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
