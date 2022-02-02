import sys
import os
import traceback
import glob
import typing
import json

class GuildTeamsSettings:
    def __init__(self, guildId: int, teamRoleId: int, teamName: str ):
        self.guild_id = guildId
        self.team_role = teamRoleId
        self.team_name = teamName.lower()
