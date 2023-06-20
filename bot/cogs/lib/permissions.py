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

    async def has_role(self, user: typing.Union[discord.Member, int], role: typing.Optional[typing.Union[discord.Role, int]] = None, guildId: typing.Optional[int] = None):
        if isinstance(user, int):
            if guildId is None:
                raise ValueError("guildId must be specified if user is an int")
            member = await self.discord_helper.get_or_fetch_member(guildId, user)
        elif isinstance(user, discord.Member):
            member = user
        else:
            raise ValueError("user must be an int or a discord.Member")
        if member is None:
            return False
        role_id = None
        if isinstance(role, int):
            if role is None:
                return False
            role_id = role
        elif isinstance(role, discord.Role):
            role_id = role.id
        else:
            raise ValueError("role must be an int or a discord.Role")

        return role_id in [r.id for r in member.roles if r.id == role_id]

    async def is_admin(self, user: typing.Union[discord.Member, int], guildId: typing.Optional[int] = None ):
        if isinstance(user, int):
            if guildId is None:
                raise ValueError("guildId must be specified if user is an int")
            member = await self.discord_helper.get_or_fetch_member(guildId, user)
        elif isinstance(user, discord.Member):
            member = user
        else:
            raise ValueError("user must be an int or a discord.Member")

        return self.has_permission(member, discord.Permissions(administrator=True))
