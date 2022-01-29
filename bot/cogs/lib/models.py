class StreamTeamMember:
    def __init__(self, guildId: int, teamName: int, userId: int, discordUsername: str, twitchUsername: str):
        self.guild_id = int(guildId)
        self.team_name = str(teamName)
        self.user_id = int(userId)
        self.discord_username = str(discordUsername)
        self.twitch_username = str(twitchUsername)
