import typing

import discord
from bot.lib import discordhelper, settings
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.mongodb.permissions import PermissionsDatabase


class Permissions:
    def __init__(self, bot) -> None:
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.permissions_db = PermissionsDatabase()

    def has_taco_permission(
        self,
        guild_id: int,
        user: typing.Union[discord.Member, discord.User, int],
        permission: typing.Union[TacoPermissions, str],
    ) -> bool:
        guild_id = guild_id
        if isinstance(user, int):
            user_id = user
        else:
            user_id = user.id

        if self.permissions_db is None:
            return False
        if isinstance(permission, str):
            permission = TacoPermissions.from_str(permission)
        return self.permissions_db.has_user_permission(guild_id, user_id, permission)

    async def has_permission(
        self,
        user: typing.Optional[typing.Union[discord.Member, int]] = None,
        permissions: typing.Optional[discord.Permissions] = None,
        guildId: typing.Optional[int] = None,
    ) -> bool:
        if user is None:
            return False
        if isinstance(user, int):
            if guildId is None:
                raise ValueError("guildId must be specified if user is an int")
            member = await self.discord_helper.get_or_fetch_member(guildId, user)
        elif isinstance(user, discord.Member):
            member = user
        else:
            member = None

        if member is None:
            return False

        if permissions is None:
            return True
        return member.guild_permissions >= permissions

    async def has_role(
        self,
        user: typing.Union[discord.Member, int],
        role: typing.Optional[typing.Union[discord.Role, int]] = None,
        guildId: typing.Optional[int] = None,
    ) -> bool:
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

    async def is_admin(self, user: typing.Union[discord.Member, int], guildId: typing.Optional[int] = None) -> bool:
        if isinstance(user, int):
            if guildId is None:
                raise ValueError("guildId must be specified if user is an int")
            member = await self.discord_helper.get_or_fetch_member(guildId, user)
        elif isinstance(user, discord.Member):
            member = user
        else:
            raise ValueError("user must be an int or a discord.Member")

        return await self.has_permission(member, discord.Permissions(administrator=True))
