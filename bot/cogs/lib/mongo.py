import datetime
import discord
import inspect
import os
import traceback
import typing
import uuid

from pymongo import MongoClient
from bson.objectid import ObjectId
from bot.cogs.lib.minecraft_op import MinecraftOpLevel
from . import database, loglevel, models, settings, utils
from .system_actions import SystemActions
from .member_status import MemberStatus


class MongoDatabase(database.Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.settings = settings.Settings()
        self.client = None
        self.connection = None
        pass

    def open(self) -> None:
        if not self.settings.db_url:
            raise ValueError("MONGODB_URL is not set")

        self.client = MongoClient(self.settings.db_url)
        self.connection = self.client.tacobot

    def close(self) -> None:
        try:
            if self.client:
                self.client.close()
            self.client = None
            self.connection = None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def insert_log(
        self, guildId: int, level: loglevel.LogLevel, method: str, message: str, stack: typing.Optional[str] = None
    ) -> None:
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
            print(ex)
            traceback.print_exc()

    def clear_log(self, guildId: int) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.logs.delete_many({"guild_id": guildId})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def add_twitchbot_to_channel(self, guildId: int, twitch_channel: str) -> bool:
        try:
            if self.connection is None or self.client is None:
                self.open()
            twitch_channel = utils.clean_channel_name(twitch_channel)

            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {"guild_id": str(guildId), "channel": twitch_channel, "timestamp": timestamp}
            self.connection.twitch_channels.update_one(
                {"guild_id": str(guildId), "channel": twitch_channel}, {"$set": payload}, upsert=True
            )
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def add_stream_team_request(self, guildId: int, userId: int, twitchName: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "twitch_name": twitchName if twitchName else "",
                "timestamp": timestamp,
            }
            # if not in table, insert
            if not self.connection.stream_team_requests.find_one(payload):
                self.connection.stream_team_requests.insert_one(payload)
            else:
                print(f"[DEBUG] [{self._module}.{_method}] [guild:0] User {userName}, already in table")
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def remove_stream_team_request(self, guildId: int, userId: int) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.stream_team_requests.delete_many({"guild_id": str(guildId), "user_id": str(userId)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    # twitchId: typing.Optional[str] = None,
    def set_user_twitch_info(self, userId: int, twitchName: typing.Optional[str] = None) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {"user_id": str(userId), "twitch_name": twitchName}
            # insert or update user twitch info
            self.connection.twitch_user.update_one({"user_id": str(userId)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_twitch_info(self, userId: int) -> typing.Optional[dict]:
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.twitch_user.find_one({"user_id": str(userId)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    # Tacos
    def remove_all_tacos(self, guildId: int, userId: int) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            print(f"[DEBUG] [{self._module}.{_method}] [guild:0] Removing tacos for user {userId}")
            self.connection.tacos.delete_many({"guild_id": str(guildId), "user_id": str(userId)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def add_tacos(self, guildId: int, userId: int, count: int) -> typing.Union[int, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            user_tacos = self.get_tacos_count(guildId, userId)
            if user_tacos is None:
                print(f"[DEBUG] [{self._module}.{_method}] [guild:0] User {userId} not in table")
                user_tacos = 0
            else:
                user_tacos = user_tacos or 0
                print(f"[DEBUG] [{self._module}.{_method}] [guild:0] User {userId} has {user_tacos} tacos")

            user_tacos += count
            print(f"[DEBUG] [{self._module}.{_method}] [guild:0] User {userId} now has {user_tacos} tacos")
            self.connection.tacos.update_one(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": {"count": user_tacos}}, upsert=True
            )
            return user_tacos
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def remove_tacos(self, guildId: int, userId: int, count: int):
        _method = inspect.stack()[0][3]
        try:
            if count < 0:
                print(f"[DEBUG] [{self._module}.{_method}] [guild:0] Count is less than 0")
                return 0
            if self.connection is None or self.client is None:
                self.open()

            user_tacos = self.get_tacos_count(guildId, userId)
            if user_tacos is None:
                print(f"[DEBUG] [{self._module}.{_method}] [guild:0] User {userId} not in table")
                user_tacos = 0
            else:
                user_tacos = user_tacos or 0
                print(f"[DEBUG] [{self._module}.{_method}] [guild:0] User {userId} has {user_tacos} tacos")

            user_tacos -= count
            if user_tacos < 0:
                user_tacos = 0

            print(f"[DEBUG] [{self._module}.{_method}] [guild:0] User {userId} now has {user_tacos} tacos")
            self.connection.tacos.update_one(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": {"count": user_tacos}}, upsert=True
            )
            return user_tacos
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tacos_count(self, guildId: int, userId: int) -> typing.Union[int, None]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            data = self.connection.tacos.find_one({"guild_id": str(guildId), "user_id": str(userId)})
            if data is None:
                print(f"[DEBUG] [{self._module}.{_method}] [guild:{guildId}] User {userId} not in table")
                return None
            return data['count']
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_total_gifted_tacos(self, guildId: int, userId: int, timespan_seconds: int = 86400) -> int:
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
            print(ex)
            traceback.print_exc()

            return 0

    def add_taco_gift(self, guildId: int, userId: int, count: int) -> bool:
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "user_id": str(userId), "count": count, "timestamp": timestamp}
            # total_gifts = self.get_total_gifted_tacos(guildId, userId, 86400)

            # add the gift
            self.connection.taco_gifts.insert_one(payload)
            return True

        except Exception as ex:
            print(ex)
            traceback.print_exc()
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
            print(f"[DEBUG] [{self._module}.{_method}] [guild:0] Adding taco reaction for user {userId}")
            self.connection.tacos_reactions.update_one(
                {"guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp},
                {"$set": payload},
                upsert=True,
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int) -> typing.Union[dict, None]:
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
            print(ex)
            traceback.print_exc()

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
            print(f"[DEBUG] [{self._module}.{_method}] [guild:0] Adding suggestion create message for guild {guildId}")
            self.connection.suggestion_create_messages.update_one(
                {"guild_id": str(guildId), "channel_id": str(channelId), "message_id": messageId},
                {"$set": payload},
                upsert=True,
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def remove_suggestion_create_message(self, guildId: int, channelId: int, messageId: int) -> None:
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
            print(ex)
            traceback.print_exc()

    def add_settings(self, guildId: int, name: str, settings: dict) -> None:
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
            print(ex)
            traceback.print_exc()

    # add or update a setting value in the settings collection, under the settings property
    def set_setting(self, guildId: int, name: str, key: str, value: typing.Any) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
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
            print(ex)
            traceback.print_exc()

    def get_settings(self, guildId: int, name: str) -> typing.Union[dict, None]:
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
            print(ex)
            traceback.print_exc()

    def get_suggestion(self, guildId: int, messageId: int) -> typing.Union[dict, None]:
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
            print(ex)
            traceback.print_exc()

    def get_suggestion_by_id(self, guildId: int, suggestionId: str) -> typing.Union[dict, None]:
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
            print(ex)
            traceback.print_exc()

    def set_state_suggestion_by_id(self, guildId: int, suggestionId: str, state: str, userId: int, reason: str) -> None:
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
            print(ex)
            traceback.print_exc()

    def set_state_suggestion(self, guildId: int, messageId: int, state: str, userId: int, reason: str) -> None:
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
            print(ex)
            traceback.print_exc()

    def has_user_voted_on_suggestion(self, suggestionId: str, userId: int) -> bool:
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
            print(ex)
            traceback.print_exc()
            return False

    def unvote_suggestion_by_id(self, guildId: int, suggestionId: str, userId: int) -> None:
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
            print(ex)
            traceback.print_exc()

    def unvote_suggestion(self, guildId: int, messageId: int, userId: int) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "message_id": str(messageId)}, {"$push": {"votes": payload}}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_suggestion_votes_by_id(self, suggestionId: str) -> typing.Union[dict, None]:
        try:
            if self.connection is None or self.client is None:
                self.open()
            suggestion = self.connection.suggestions.find_one({"id": str(suggestionId)})
            if suggestion is None:
                return None
            return suggestion['votes']
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def vote_suggestion(self, guildId: int, messageId: int, userId: int, vote: int) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            vote = vote if vote in [1, -1] else 0
            payload = {"user_id": userId, "vote": vote, "timestamp": timestamp}
            # insert the suggestion into the database
            self.connection.suggestions.update_one(
                {"guild_id": str(guildId), "message_id": str(messageId)},{"$push": {"votes": payload}},upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def vote_suggestion_by_id(self, suggestionId: str, userId: int, vote: int) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            vote = vote if vote in [1, -1] else 0
            payload = {"user_id": str(userId), "vote": vote, "timestamp": timestamp}
            # insert the suggestion into the database
            self.connection.suggestions.update_one({"id": suggestionId}, {"$push": {"votes": payload}}, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def add_suggestion(self, guildId: int, messageId: int, suggestion: dict) -> None:
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
            print(ex)
            traceback.print_exc()

    def delete_suggestion_by_id(self, guildId: int, suggestionId: str, userId: int, reason: str) -> None:
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
            print(ex)
            traceback.print_exc()

    def track_invite_code(self, guildId: int, inviteCode: str, inviteInfo: dict, userInvite: dict) -> None:
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
            print(ex)
            traceback.print_exc()

    def get_invite_code(self, guildId: int, inviteCode: str) -> typing.Any:
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.invite_codes.find_one({"guild_id": str(guildId), "code": inviteCode})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_live_activity(self, guildId: int, userId: int, live: bool, platform: str, url: str) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "status": "ONLINE" if live else "OFFLINE",
                "platform": platform.upper().strip(),
                "url": url,
                "timestamp": timestamp,
            }
            self.connection.live_activity.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_live(
        self,
        guildId: int,
        userId: int,
        platform: typing.Union[str, None],
        channelId: typing.Union[int, None] = None,
        messageId: typing.Union[int, None] = None,
        url: typing.Union[str, None] = None,
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()

            if platform is None:
                raise ValueError("platform cannot be None")
            if userId is None:
                raise ValueError("userId cannot be None")
            if guildId is None:
                raise ValueError("guildId cannot be None")

            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "platform": platform.upper().strip(),
                "url": url,
                "channel_id": str(channelId) if channelId is not None else None,
                "message_id": str(messageId) if messageId is not None else None,
                "timestamp": timestamp,
            }
            self.connection.live_tracked.update_one(
                {"guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip()},
                {"$set": payload},
                upsert=True,
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tracked_live(self, guildId: int, userId: int, platform: str):
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(
                self.connection.live_tracked.find(
                    {"guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip()}
                )
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tracked_live_by_url(self, guildId: int, url: str):
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.live_tracked.find({"guild_id": str(guildId), "url": url})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_tracked_live_by_user(self, guildId: int, userId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.live_tracked.find({"guild_id": str(guildId), "user_id": str(userId)}))
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def untrack_live(self, guildId: int, userId: int, platform: str):
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.live_tracked.delete_many(
                {"guild_id": str(guildId), "user_id": str(userId), "platform": platform.upper().strip()}
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def add_user_birthday(self, guildId: int, userId: int, month: int, day: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "month": month,
                "day": day,
                "timestamp": timestamp,
            }
            self.connection.birthdays.update_one(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_birthday(self, guildId: int, userId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.birthdays.find_one({"guild_id": str(guildId), "user_id": str(userId)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_birthdays(self, guildId: int, month: int, day: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.birthdays.find({"guild_id": str(guildId), "month": month, "day": day}))
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_birthday_check(self, guildId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"guild_id": str(guildId), "timestamp": timestamp}
            self.connection.birthday_checks.update_one({"guild_id": str(guildId)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def birthday_was_checked_today(self, guildId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            checks = list(self.connection.birthday_checks.find({"guild_id": str(guildId)}))
            if len(checks) > 0:
                # central_tz= pytz.timezone(self.settings.timezone)
                date = datetime.datetime.utcnow().date()
                start = datetime.datetime.combine(date, datetime.time.min)
                end = datetime.datetime.combine(date, datetime.time.max)
                start_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.min))
                end_ts = utils.to_timestamp(datetime.datetime.combine(date, datetime.time.max))
                timestamp = checks[0]["timestamp"]

                # ts_date = utils.from_timestamp(timestamp)
                # cst_dt = ts_date.replace(tzinfo=central_tz)
                # cst_ts = utils.to_timestamp(cst_dt, tz=central_tz)
                # cst_start = start.replace(tzinfo=central_tz)
                # cst_end = end.replace(tzinfo=central_tz)
                # cst_start_ts = utils.to_timestamp(cst_start, tz=central_tz)
                # cst_end_ts = utils.to_timestamp(cst_end, tz=central_tz)

                if timestamp >= start_ts and timestamp <= end_ts:
                    return True

                # if cst_ts >= cst_start_ts and cst_ts <= cst_end_ts:
                #     return True
            return False
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def save_tqotd(self, guildId: int, question: str, author: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "question": question,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
            }
            self.connection.tqotd.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_tqotd_answer(self, guildId: int, userId: int, message_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())
            result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            if result:
                self.connection.tqotd.update_one(
                    {"guild_id": str(guildId), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(userId), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    self.connection.tqotd.update_one(
                        {"guild_id": str(guildId), "timestamp": timestamp},
                        {
                            "$push": {
                                "answered": {"user_id": str(userId), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No TQOTD found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def tqotd_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the TQOTD?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.tqotd.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No TQOTD found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def _get_twitch_name(self, userId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.twitch_names.find_one({"user_id": str(userId)})
            if result:
                return result["twitch_name"]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def set_twitch_discord_link_code(self, userId: int, code: str):
        try:
            if self.connection is None or self.client is None:
                self.open()
            twitch_name = self._get_twitch_name(userId)
            if not twitch_name:
                payload = {"user_id": str(userId), "link_code": code.strip()}
                self.connection.twitch_user.update_one({"user_id": str(userId)}, {"$set": payload}, upsert=True)
                return True
            else:
                raise ValueError(f"Twitch user {twitch_name} already linked")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def link_twitch_to_discord_from_code(self, userId: int, code: str):
        try:
            if self.connection is None or self.client is None:
                self.open()
            twitch_name = self._get_twitch_name(userId)
            if not twitch_name:
                payload = {"user_id": str(userId)}
                result = self.connection.twitch_user.update_one(
                    {"link_code": code.strip()}, {"$set": payload}, upsert=True
                )
                if result.modified_count == 1:
                    return True
                else:
                    raise ValueError(f"Unable to find an entry for a user with link code: {code}")
            else:
                raise ValueError(f"Twitch user {twitch_name} already linked")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def get_minecraft_user(self, guildId: int, userId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.minecraft_users.find_one({"user_id": str(userId), "guild_id": str(guildId)})
            if result:
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def whitelist_minecraft_user(self, guildId: int, userId: int, username: str, uuid: str, whitelist: bool = True):
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {
                "user_id": str(userId),
                "guild_id": str(guildId),
                "username": username,
                "uuid": uuid,
                "whitelist": whitelist,
            }
            self.connection.minecraft_users.update_one(
                {"user_id": str(userId), "guild_id": str(guildId)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def op_minecraft_user(
        self,
        userId: int,
        username: str,
        uuid: str,
        op: bool = True,
        level: MinecraftOpLevel = MinecraftOpLevel.LEVEL1,
        bypassPlayerCount: bool = False,
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            payload = {
                "user_id": str(userId),
                "username": username,
                "uuid": uuid,
                "op": {"enabled": op, "level": int(level), "bypassesPlayerLimit": bypassPlayerCount},
            }
            self.connection.minecraft_users.update_one({"user_id": str(userId)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def find_open_game_key_offer(self, guild_id: int, channel_id: int):
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
            print(ex)
            traceback.print_exc()

    def open_game_key_offer(
        self,
        game_key_id: str,
        guild_id: int,
        message_id: int,
        channel_id: int,
        expires: typing.Optional[datetime.datetime] = None,
    ):
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
            print(ex)
            traceback.print_exc()

    def close_game_key_offer_by_message(self, guild_id: int, message_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_key_offers.delete_one({"guild_id": str(guild_id), "message_id": str(message_id)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def close_game_key_offer(self, guild_id: int, game_key_id: str):
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_key_offers.delete_one({"guild_id": str(guild_id), "game_key_id": game_key_id})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def claim_game_key_offer(self, game_key_id: str, user_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.utcnow())
            payload = {"redeemed_by": str(user_id), "redeemed_timestamp": timestamp}
            self.connection.game_keys.update_one({"_id": ObjectId(game_key_id)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def get_game_key_data(self, game_key_id: str):
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.game_keys.find_one({"_id": ObjectId(game_key_id)})
            if result:
                return result
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_random_game_key_data(self, guild_id: int):
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
            print(ex)
            traceback.print_exc()

    def track_wdyctw_answer(self, guild_id: int, user_id: int, message_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.wdyctw.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.wdyctw.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.wdyctw.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.wdyctw.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {
                            "$push": {
                                "answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No WDYCTW found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def save_wdyctw(
        self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.wdyctw.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def wdyctw_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the WDYCTW?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.wdyctw.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.wdyctw.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No WDYCTW found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def track_techthurs_answer(self, guild_id: int, user_id: int, message_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.techthurs.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.techthurs.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.techthurs.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.techthurs.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {
                            "$push": {
                                "answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No techthurs found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def save_techthurs(
        self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.techthurs.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def techthurs_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the techthurs?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.techthurs.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.techthurs.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(f"No techthurs found for guild {guildId} for {datetime.datetime.utcnow().date()}")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def track_mentalmondays_answer(self, guild_id: int, user_id: int, message_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()

            messageId = str(message_id)
            if message_id is None or messageId == "" or messageId == "0" or messageId == "None":
                messageId = None

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.mentalmondays.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.mentalmondays.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.mentalmondays.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.mentalmondays.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {
                            "$push": {
                                "answered": {"user_id": str(user_id), "message_id": messageId, "timestamp": ts_track}
                            }
                        },
                        upsert=True,
                    )
                else:
                    raise Exception(f"No mentalmondays found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def save_mentalmondays(
        self, guildId: int, message: str, image: str, author: int, channel_id: int = None, message_id: int = None
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.mentalmondays.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def mentalmondays_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the mentalmondays?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.mentalmondays.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.mentalmondays.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId) and answer["message_id"] == str(messageId):
                            return True
                    return False
                else:
                    raise Exception(
                        f"No mentalmondays found for guild {guildId} for {datetime.datetime.utcnow().date()}"
                    )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def save_taco_tuesday(
        self,
        guildId: int,
        message: str,
        image: str,
        author: int,
        channel_id: typing.Optional[int] = None,
        message_id: typing.Optional[int] = None,
        tweet: typing.Optional[str] = None,
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "message": message,
                "image": image,
                "author": str(author),
                "answered": [],
                "tweet": tweet,
                "timestamp": timestamp,
                "channel_id": str(channel_id),
                "message_id": str(message_id),
            }
            self.connection.taco_tuesday.update_one(
                {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_taco_tuesday(self, guild_id: int, user_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()

            now_date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(now_date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            ts_track = utils.to_timestamp(datetime.datetime.utcnow())

            result = self.connection.taco_tuesday.find_one({"guild_id": str(guild_id), "timestamp": timestamp})

            if result:
                self.connection.taco_tuesday.update_one(
                    {"guild_id": str(guild_id), "timestamp": timestamp},
                    {"$push": {"answered": {"user_id": str(user_id), "timestamp": ts_track}}},
                    upsert=True,
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                # timestamp = utils.to_timestamp(ts_date)
                result = self.connection.taco_tuesday.find_one(
                    {
                        "guild_id": str(guild_id),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        }
                    }
                )
                if result:
                    self.connection.taco_tuesday.update_one(
                        {"guild_id": str(guild_id), "timestamp": result['timestamp']},
                        {"$push": {"answered": {"user_id": str(user_id), "timestamp": ts_track}}},
                        upsert=True,
                    )
                else:
                    raise Exception(f"No taco tuesday found for guild {guild_id} for the last 7 days")
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def taco_tuesday_user_tracked(self, guildId: int, userId: int, messageId: int):
        # was this message, for this user, already used to answer the WDYCTW?
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.taco_tuesday.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                for answer in result["answered"]:
                    if answer["user_id"] == str(userId):
                        return True
                return False
            else:
                date = date - datetime.timedelta(days=1)
                ts_date = datetime.datetime.combine(date, datetime.time.min)
                timestamp = utils.to_timestamp(ts_date)
                result = self.connection.taco_tuesday.find_one({"guild_id": str(guildId), "timestamp": timestamp})
                if result:
                    for answer in result["answered"]:
                        if answer["user_id"] == str(userId):
                            return True
                    return False
                else:
                    raise Exception(
                        f"No Taco Tuesday found for guild {guildId} for {datetime.datetime.utcnow().date()}"
                    )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def taco_tuesday_set_user(self, guildId: int, userId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            # find the most recent taco tuesday
            result = self.connection.taco_tuesday.find_one({"guild_id": str(guildId), "timestamp": timestamp})
            if result:
                self.connection.taco_tuesday.update_one(
                    {"guild_id": str(guildId), "timestamp": timestamp}, {"$set": {"user_id": str(userId)}}, upsert=True
                )
            else:
                now_date = datetime.datetime.utcnow().date()
                back_date = now_date - datetime.timedelta(days=7)
                ts_now_date = datetime.datetime.combine(now_date, datetime.time.max)
                ts_back_date = datetime.datetime.combine(back_date, datetime.time.min)
                result = self.connection.taco_tuesday.find_one(
                    {
                        "guild_id": str(guildId),
                        "timestamp": {
                            "$gte": utils.to_timestamp(ts_back_date),
                            "$lte": utils.to_timestamp(ts_now_date),
                        },
                    }
                )
                if result:
                    self.connection.taco_tuesday.update_one(
                        {"guild_id": str(guildId), "timestamp": result['timestamp']},
                        {"$set": {"user_id": str(userId)}},
                        upsert=True,
                    )
                else:
                    raise Exception(
                        f"No Taco Tuesday found for guild {guildId} for {datetime.datetime.utcnow().date()}"
                    )
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def taco_tuesday_get_by_message(self, guildId: int, channelId: int, messageId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.taco_tuesday.find_one(
                {"guild_id": str(guildId), "channel_id": str(channelId), "message_id": str(messageId)}
            )
            return result
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def taco_tuesday_update_message(
        self, guildId: int, channelId: int, messageId: int, newChannelId: int, newMessageId: int
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            result = self.connection.taco_tuesday.update_one(
                {"guild_id": str(guildId), "channel_id": str(channelId), "message_id": str(messageId)},
                {"$set": {"channel_id": str(newChannelId), "message_id": str(newMessageId)}},
            )
            return result
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            raise ex

    def track_first_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "user_id": str(userId),
                "timestamp": timestamp,
            }

            # if self.is_first_message_today(guildId=guildId, userId=userId):
            self.connection.first_message.update_one(
                {"guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp},
                {"$set": payload},
                upsert=True,
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {"guild_id": str(guildId), "user_id": str(userId)}

            result = self.connection.messages.find_one({"guild_id": str(guildId), "user_id": str(userId)})
            if result:
                self.connection.messages.update_one(
                    {"guild_id": str(guildId), "user_id": str(userId)},
                    {
                        "$push": {
                            "messages": {
                                "channel_id": str(channelId),
                                "message_id": str(messageId),
                                "timestamp": timestamp,
                            }
                        }
                    },
                    upsert=True,
                )
            else:
                self.connection.messages.insert_one(
                    {
                        **payload,
                        "messages": [
                            {"channel_id": str(channelId), "message_id": str(messageId), "timestamp": timestamp}
                        ],
                    }
                )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def is_first_message_today(self, guildId: int, userId: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            result = self.connection.first_message.find_one(
                {"guild_id": str(guildId), "user_id": str(userId), "timestamp": timestamp}
            )
            if result:
                return False
            return True
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_user(
        self,
        guildId: int,
        userId: int,
        username: str,
        discriminator: str,
        avatar: typing.Optional[str],
        displayname: str,
        created: typing.Optional[datetime.datetime] = None,
        bot: bool = False,
        system: bool = False,
        status: typing.Optional[typing.Union[str, MemberStatus]] = None,
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            created_timestamp = utils.to_timestamp(created) if created else None
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "username": username,
                "discriminator": discriminator,
                "avatar": avatar,
                "displayname": displayname,
                "created": created_timestamp,
                "bot": bot,
                "system": system,
                "status": str(status) if status else None,
                "timestamp": timestamp,
            }

            self.connection.users.update_one(
                {"guild_id": str(guildId), "user_id": str(userId)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_photo_post(
        self, guildId: int, userId: int, channelId: int, messageId: int, message: str, image: str, channelName: str
    ):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "channel_id": str(channelId),
                "channel_name": channelName,
                "message_id": str(messageId),
                "message": message,
                "image": image,
                "timestamp": timestamp,
            }

            self.connection.photo_posts.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_user_join_leave(self, guildId: int, userId: int, join: bool):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guildId),
                "user_id": str(userId),
                "action": "JOIN" if join else "LEAVE",
                "timestamp": timestamp,
            }

            self.connection.user_join_leave.insert_one(payload)

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_tacos_log(self, guildId: int, fromUserId: int, toUserId: int, count: int, type: str, reason: str):
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
            print(ex)
            traceback.print_exc()

    def track_guild(self, guild: discord.Guild) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(guild.id),
                "name": guild.name,
                "owner_id": str(guild.owner_id),
                "created_at": utils.to_timestamp(guild.created_at),
                "vanity_url": guild.vanity_url or None,
                "vanity_url_code": guild.vanity_url_code or None,
                "icon": guild.icon.url if guild.icon else None,
                "timestamp": timestamp,
            }

            self.connection.guilds.update_one({"guild_id": str(guild.id)}, {"$set": payload}, upsert=True)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_trivia_question(self, triviaQuestion: models.TriviaQuestion):
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)
            payload = {
                "guild_id": str(triviaQuestion.guild_id),
                "channel_id": str(triviaQuestion.channel_id),
                "message_id": str(triviaQuestion.message_id),
                "question_id": triviaQuestion.question_id,
                "starter_id": str(triviaQuestion.starter_id),
                "question": triviaQuestion.question,
                "correct_answer": triviaQuestion.correct_answer,
                "incorrect_answers": triviaQuestion.incorrect_answers,
                "category": triviaQuestion.category,
                "difficulty": triviaQuestion.difficulty,
                "reward": triviaQuestion.reward,
                "punishment": triviaQuestion.punishment,
                "correct_users": [str(u) for u in triviaQuestion.correct_users],
                "incorrect_users": [str(u) for u in triviaQuestion.incorrect_users],
                "timestamp": timestamp,
            }

            self.connection.trivia_questions.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def migrate_game_keys(self):
        guild_id = "935294040386183228"
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.game_keys.update_many({"guild_id": {"$exists": False}}, {"$set": {"guild_id": guild_id}})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def migrate_minecraft_whitelist(self):
        guild_id = "935294040386183228"
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.minecraft_users.update_many(
                {"guild_id": {"$exists": False}}, {"$set": {"guild_id": guild_id}}
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def add_user_to_join_whitelist(self, guild_id: int, user_id: int, added_by: int) -> None:
        """Add a user to the join whitelist for a guild."""
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "added_by": str(added_by),
                "timestamp": timestamp,
            }
            self.connection.join_whitelist.update_one(
                {"guild_id": str(guild_id), "user_id": str(user_id)}, {"$set": payload}, upsert=True
            )
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_join_whitelist(self, guild_id: int) -> list:
        """Get the join whitelist for a guild."""
        try:
            return list(self.connection.join_whitelist.find({"guild_id": str(guild_id)}))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return []

    def remove_user_from_join_whitelist(self, guild_id: int, user_id: int) -> None:
        """Remove a user from the join whitelist for a guild."""
        try:
            if self.connection is None or self.client is None:
                self.open()
            self.connection.join_whitelist.delete_one({"guild_id": str(guild_id), "user_id": str(user_id)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def track_system_action(
        self, guild_id: int, action: typing.Union[SystemActions, str], data: typing.Optional[dict] = None
    ) -> None:
        """Track a system action."""
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild_id),
                "action": str(action.name if isinstance(action, SystemActions) else action),
                "timestamp": timestamp,
                "data": data,
            }
            self.connection.system_actions.insert_one(payload)
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_guild_ids(self) -> list:
        """Get all guild IDs."""
        try:
            if self.connection is None or self.client is None:
                self.open()
            return list(self.connection.guilds.distinct("guild_id"))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return []

    def get_user_introductions(self, guild_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.introductions.find({"guild_id": str(guild_id)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return []

    def get_user_introduction(self, guild_id: int, user_id: int):
        try:
            if self.connection is None or self.client is None:
                self.open()
            return self.connection.introductions.find_one({"guild_id": str(guild_id), "user_id": str(user_id)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            return None

    def track_user_introduction(
        self, guild_id: int, user_id: int, message_id: int, channel_id: int, approved: bool
    ) -> None:
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "message_id": str(message_id),
                "channel_id": str(channel_id),
                "approved": approved,
                "timestamp": timestamp,
            }
            self.connection.introductions.update_one(
                {"guild_id": str(guild_id), "user_id": str(user_id)}, {"$set": payload}, upsert=True
            )

        except Exception as ex:
            print(ex)
            traceback.print_exc()
