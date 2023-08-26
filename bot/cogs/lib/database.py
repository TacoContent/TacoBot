import datetime
import typing

from bot.cogs.lib import models, loglevel  # pylint: disable=no-name-in-module
from bot.cogs.lib.member_status import MemberStatus  # pylint: disable=relative-beyond-top-level
from bot.cogs.lib.system_actions import SystemActions  # pylint: disable=relative-beyond-top-level


class Database:
    def __init__(self):
        pass

    def open(self):
        pass

    def close(self):
        pass

    def insert_log(
        self, guildId: int, level: loglevel.LogLevel, method: str, message: str, stack: typing.Optional[str] = None
    ):
        pass

    def clear_log(self, guildId: int):
        pass

    # add StreamTeamMember to database
    def add_stream_team_request(
        self, guildId: int, userName: str, userId: int, twitchName: typing.Optional[str] = None
    ) -> None:
        pass

    def remove_stream_team_request(self, guildId: int, userId: int):
        pass

    def get_stream_team_requests(self, guildId: int):
        pass

    def set_user_twitch_info(self, userId: int, twitchName: typing.Optional[str] = None):
        pass

    def get_user_twitch_info(self, userId: int):
        pass

    def add_tacos(self, guildId: int, userId: int, count: int):
        pass

    def remove_tacos(self, guildId: int, userId: int, count: int):
        pass

    def get_tacos_count(self, guildId: int, userId: int) -> typing.Union[int, None]:
        pass

    def get_total_gifted_tacos(
        self, guildId: int, userId: int, timespan_seconds: int = 86400
    ) -> typing.Union[int, None]:
        pass

    def add_taco_gift(self, guildId: int, userId: int, count: int):
        pass

    def add_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass

    def get_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass

    def add_settings(self, guildId: int, name: str, settings: dict):
        pass

    def get_settings(self, guildId: int, name: str):
        pass

    def get_suggestion(self, guildId: int, messageId: int):
        pass

    def get_suggestion_by_id(self, guildId: int, suggestionId: str):
        pass

    def add_suggestion(self, guildId: int, messageId: int, suggestion: dict):
        pass

    def add_suggestion_create_message(self, guildId: int, channelId: int, messageId: int):
        pass

    def remove_suggestion_create_message(self, guildId: int, channelId: int, messageId: int):
        pass

    def track_invite_code(self, guildId: int, inviteCode: str, inviteInfo: dict):
        pass

    def get_invite_code(self, guildId: int, inviteCode: str):
        pass

    def track_live(
        self,
        guildId: int,
        userId: int,
        platform: str,
        channelId: typing.Optional[int] = None,
        messageId: typing.Optional[int] = None,
        url: typing.Optional[str] = None,
    ) -> None:
        pass

    def get_tracked_live(self, guildId: int, userId: int, platform: str):
        pass

    def untrack_live(self, guildId: int, userId: int, platform: str):
        pass

    def get_tracked_live_by_url(self, guildId: int, url: str):
        pass

    def get_tracked_live_by_user(self, guildId: int, userId: int):
        pass

    def birthday_was_checked_today(self, guildId: int):
        pass

    def track_birthday_check(self, guildId: int):
        pass

    def get_user_birthdays(self, guildId: int, month: int, day: int):
        pass

    def add_user_birthday(self, guildId: int, userId: int, month: int, day: int):
        pass

    def save_tqotd(self, guildId: int, quote: str, author: int):
        pass

    def save_wdyctw(self, guildId: int, message: str, image: str, author: int):
        pass

    def save_techthurs(self, guildId: int, message: str, image: str, author: int):
        pass

    def save_mentalmondays(self, guildId: int, message: str, image: str, author: int):
        pass

    def track_tqotd_answer(self, guildId: int, userId: int):
        pass

    def tqotd_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        pass

    def track_wdyctw_answer(self, guildId: int, userId: int):
        pass

    def wdyctw_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        pass

    def track_techthurs_answer(self, guildId: int, userId: int):
        pass

    def techthurs_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        pass

    def track_mentalmondays_answer(self, guildId: int, userId: int):
        pass

    def mentalmondays_user_message_tracked(self, guildId: int, userId: int, messageId: int):
        pass

    def save_taco_tuesday(self, guildId: int, message: str, image: str, author: int):
        pass

    def track_taco_tuesday(self, guildId: int, userId: int):
        pass

    def taco_tuesday_user_tracked(self, guildId: int, userId: int, messageId: int):
        pass

    def taco_tuesday_set_user(self, guildId: int, userId: int):
        pass

    def taco_tuesday_get_by_message(self, guildId: int, channelId: int, messageId: int):
        pass

    def taco_tuesday_update_message(
        self, guildId: int, channelId: int, messageId: int, newChannelId: int, newMessageId: int
    ) -> None:
        pass

    def track_first_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass

    def track_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass

    def is_first_message_today(self, guildId: int, userId: int):
        pass

    def track_user(
        self,
        guildId: int,
        userId: int,
        username: str,
        discriminator: str,
        avatar: str,
        displayname: str,
        created: typing.Optional[datetime.datetime] = None,
        bot: bool = False,
        system: bool = False,
        status: typing.Optional[typing.Union[str, MemberStatus]] = None,
    ) -> None:
        pass

    def track_food_post(
        self, guildId: int, userId: int, channelId: int, messageId: int, message: str, image: str
    ) -> None:
        pass

    def track_user_join_leave(self, guildId: int, userId: int, join: bool):
        pass

    def track_tacos_log(self, guildId: int, fromUserId: int, toUserId: int, count: int, type: str, reason: str) -> None:
        pass

    def track_trivia_question(self, triviaQuestion: models.TriviaQuestion) -> None:
        pass

    def get_random_game_key_data(self, guild_id: int):
        pass

    def get_game_key_data(self, game_key_id: str):
        pass

    def claim_game_key_offer(self, game_key_id: str, user_id: int):
        pass

    def close_game_key_offer(self, guild_id: int, game_key_id: str):
        pass

    def close_game_key_offer_by_message(self, guild_id: int, message_id: int):
        pass

    def open_game_key_offer(self, game_key_id: str, guild_id: int, message_id: int, channel_id: int):
        pass

    def find_open_game_key_offer(self, guild_id: int, channel_id: int):
        pass

    def add_user_to_join_whitelist(self, guild_id: int, user_id: int, added_by: int) -> None:
        pass

    def get_user_join_whitelist(self, guild_id: int) -> list:
        return []

    def remove_user_from_join_whitelist(self, guild_id: int, user_id: int) -> None:
        pass

    def track_system_action(
        self, guild_id: int, action: typing.Union[SystemActions, str], data: typing.Optional[dict] = None
    ) -> None:
        pass
