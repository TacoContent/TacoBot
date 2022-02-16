import sys
import os
import traceback
import glob
import typing
import json

class SuggestionModal():
    def __init__(self, guildId: int, userId: int, channelId: int, messageId: int, suggestionId: str,
        suggestion: str, state: int, created: int, modified: int = None,
        deleted: int = None, reason: str = None ):

        self.guild_id = guildId
        self.user_id = userId
        self.channel_id = channelId
        self.suggestion_id = suggestionId
        self.suggestion = suggestion
        self.state = state
        self.created = created
        self.modified = modified
        self.deleted = deleted
        self.reason = reason
