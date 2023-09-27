import datetime
import typing

from bot.cogs.lib import loglevel, models
from bot.cogs.lib.member_status import MemberStatus
from bot.cogs.lib.system_actions import SystemActions


class Database:
    def __init__(self):
        pass

    def open(self):
        pass

    def close(self):
        pass

    def get_stream_team_requests(self, guildId: int):
        pass

    def add_settings(self, guildId: int, name: str, settings: dict):
        pass

    def get_settings(self, guildId: int, name: str):
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
