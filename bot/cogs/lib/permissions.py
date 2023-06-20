import enum
import typing
import discord
from . import settings
from . import mongo
from . import utils
from . import discordhelper

class Permissions:
    def __init__(self, bot) -> None:
        self.settings = settings.Settings()
        self.db = mongo.MongoDatabase()
        self.discord_helper = discordhelper.DiscordHelper(bot)

    def has_permission(self, user: typing.Optional[discord.Member], permissions: typing.Optional[discord.Permissions] = None):
        if user is None:
            return False
        if permissions is None:
            return True
        return user.guild_permissions >= permissions

    def has_role(self, user: discord.Member, role: discord.Role):
        return role in user.roles

    async def is_admin(self, user: typing.Union[discord.Member, int], guildId: typing.Optional[int] = None ):
        if isinstance(user, int):
            if guildId is None:
                raise ValueError("guildId must be specified if user is an int")
            member = await self.discord_helper.get_or_fetch_member(guildId, user)
        else:
            member = user

        return self.has_permission(member, discord.Permissions(administrator=True))
