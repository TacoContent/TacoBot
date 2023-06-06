
from traceback import print_exc
import typing

class Database():

    def __init__(self):
        pass
    def open(self):
        pass
    def close(self):
        pass

    def insert_log(self, guildId: int, level: str, method: str, message: str, stack: str = None):
        pass
    def clear_log(self, guildId: int):
        pass

    # add StreamTeamMember to database
    def add_stream_team_request(self, guildId: int, userName: str, userId: int):
        pass
    def remove_stream_team_request(self, guildId: int, userId: int):
        pass

    def get_stream_team_requests(self, guildId: int):
        pass

    def set_user_twitch_info(self, userId: int, twitchId: str, twitchName: str):
        pass
    def get_user_twitch_info(self, userId: int):
        pass

    def add_tacos(self, guildId: int, userId: int, count: int):
        pass
    def remove_tacos(self, guildId: int, userId: int, count: int):
        pass
    def get_tacos_count(self, guildId: int, userId: int):
        pass
    def get_total_gifted_tacos(self, guildId: int, userId: int, timespan_seconds: int = 86400):
        pass
    def add_taco_gift(self, guildId: int, userId: int, count: int):
        pass
    def add_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass
    def get_taco_reaction(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass


    def add_settings(self, guildId: int, name:str, settings: dict):
        pass
    def get_settings(self, guildId: int, name:str):
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

    def track_wait_invoke(self, guildId: int, channelId: int, messageId: int):
        pass
    def untrack_wait_invoke(self, guildId: int, channelId: int, messageId: int):
        pass
    def get_wait_invokes(self, guildId: int, channelId: int):
        pass

    def track_invite_code(self, guildId: int, inviteCode: str, inviteInfo: dict):
        pass
    def get_invite_code(self, guildId: int, inviteCode: str):
        pass

    def track_live(self, guildId: int, userId: int, platform: str, channelId: int = None, messageId: int = None, url: str = None):
        pass
    def get_tracked_live(self, guildId: int, userId: int, platform: str):
        pass
    def untrack_live(self, guildId: int, userId: int, platform: str):
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

    def track_first_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass

    def track_message(self, guildId: int, userId: int, channelId: int, messageId: int):
        pass

    def is_first_message_today(self, guildId: int, userId: int):
        pass

    def track_user(self, guildId: int, userId: int, username: str, discriminator: str, avatar: str, displayname: str):
        pass

    def UPDATE_SCHEMA(self):
        pass
