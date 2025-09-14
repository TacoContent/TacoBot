import datetime
import inspect
import os
import traceback
import typing

import discord
import pytz
from bot.lib import utils
from bot.lib.enums import loglevel
from bot.lib.enums.member_status import MemberStatus
from bot.lib.enums.system_actions import SystemActions
from bot.lib.models.triviaquestion import TriviaQuestion
from bot.lib.mongodb.database import Database


class TrackingDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def track_command_usage(
        self,
        guildId: int,
        channelId: typing.Optional[int],
        userId: int,
        command: str,
        subcommand: typing.Optional[str] = None,
        args: typing.Optional[typing.List[dict]] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            date = datetime.datetime.utcnow().date()
            ts_date = datetime.datetime.combine(date, datetime.time.min)
            timestamp = utils.to_timestamp(ts_date)
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "user_id": str(userId),
                "command": command,
                "subcommand": subcommand,
                "arguments": args,
                "timestamp": timestamp,
            }
            self.connection.commands_usage.insert_one(payload)
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
            )

    def track_first_message(self, guildId: int, userId: int, channelId: int, messageId: int) -> None:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_message(self, guildId: int, userId: int, channelId: int, messageId: int) -> None:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def is_first_message_today(self, guildId: int, userId: int) -> bool:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

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
    ) -> None:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_photo_post(
        self, guildId: int, userId: int, channelId: int, messageId: int, message: str, image: str, channelName: str
    ) -> None:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_user_join_leave(self, guildId: int, userId: int, join: bool) -> None:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_guild(self, guild: discord.Guild) -> None:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guild.id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_trivia_question(self, triviaQuestion: TriviaQuestion) -> None:
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=triviaQuestion.guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_system_action(
        self, guild_id: int, action: typing.Union[SystemActions, str], data: typing.Optional[dict] = None
    ) -> None:
        """Track a system action."""
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_user_introduction(
        self, guild_id: int, user_id: int, message_id: int, channel_id: int, approved: bool
    ) -> None:
        """Track a user introduction."""
        _method = inspect.stack()[0][3]
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
            self.log(
                guildId=guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_free_game_key(self, guildId: int, channelId: int, messageId: int, gameId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.now(tz=pytz.timezone(self.settings.timezone)))
            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId),
                "game_id": str(gameId),
                "timestamp": timestamp,
            }
            self.connection.track_free_game_keys.update_one(  # type: ignore
                {
                    "guild_id": str(guildId),
                    "channel_id": str(channelId),
                    "message_id": str(messageId),
                    "game_id": str(gameId),
                },
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

    def track_shift_code(self, guildId: int, channelId: int, messageId: int, code: str):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()
            timestamp = utils.to_timestamp(datetime.datetime.now(tz=pytz.timezone(self.settings.timezone)))

            payload = {
                "guild_id": str(guildId),
                "channel_id": str(channelId),
                "message_id": str(messageId)
            }

            # {
            #   _id: ObjectId("..."),
            #   code: "SHIFT-CODE-1234",
            #   ...
            #   tracked_in: [
            #     {
            #       guild_id: "123456789012345678",
            #       channel_id: "123456789012345678",
            #       message_id: "123456789012345678",
            #     },
            #     ...
            #   ]
            # }

            code = str(code).strip().upper().replace(" ", "")

            # payload should exist in document as array element in the shift_codes collection
            self.connection.shift_codes.update_one(  # type: ignore
                {"code": code}, {"$addToSet": {"tracked_in": payload}}, upsert=True
            )

        except Exception as ex:
            self.log(
                guildId=guildId,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
