
from traceback import print_exc

class Database():

    def __init__(self):
        print("[database.__init__] INITIALIZE DATABASE")
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

    def UPDATE_SCHEMA(self):
        pass
