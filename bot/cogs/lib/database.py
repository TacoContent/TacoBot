
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

    def UPDATE_SCHEMA(self):
        pass
