
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
    def add_stream_team_member(self, guildId: int, teamName: str, userId: int, discordUsername: str, twitchUsername: str):
        pass
    def get_stream_team_members(self, guildId: int, teamName: str):
        pass
    def remove_stream_team_member(self, guildId: int, teamName: str, userId: int):
        pass

    # GuildTeamsSettings
    def add_guild_team_settings(self, guildId: int, teamRole: typing.Union[str,int], teamName: str):
        pass
    def update_guild_team_settings(self, guildId: int, teamRole: typing.Union[str,int], teamName: str):
        pass
    def remove_guild_team_settings(self, guildId: int, teamRole: typing.Union[str,int]):
        pass
    def get_guild_team_settings_by_team_name(self, guildId: int, teamName: str):
        pass
    def get_guild_team_settings_by_team_role(self, guildId: int, teamRole: typing.Union[str, int]):
        pass

    def add_tacos(self, guildId: int, userId: int, count: int):
        pass
    def get_tacos_count(self, guildId: int, userId: int):
        pass
    def UPDATE_SCHEMA(self):
        pass
