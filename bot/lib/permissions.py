import typing

import discord
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.helpers import EntityHelper
from bot.lib.mongodb.permissions import PermissionsDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot


class Permissions:
    def __init__(
        self,
        bot: TacoBot,
        settings: typing.Optional[Settings] = None,
        permissions_db: typing.Optional[PermissionsDatabase] = None,
        entity_helper: typing.Optional[EntityHelper] = None,
    ) -> None:
        self.settings = settings or Settings()
        self.permissions_db = permissions_db or PermissionsDatabase()
        self.entity_helper = entity_helper or EntityHelper(bot)

    def has_taco_permission(
        self,
        guild_id: int,
        user: typing.Union[discord.Member, discord.User, int],
        permission: typing.Union[TacoPermissions, str, typing.List[typing.Union[TacoPermissions, str]]],
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
        if isinstance(permission, list):
            # if its a string, we need to convert it to an enum
            permissions: typing.List[TacoPermissions] = [
                TacoPermissions.from_str(perm) if isinstance(perm, str) else perm for perm in permission
            ]
            return any(self.permissions_db.has_user_permission(guild_id, user_id, perm) for perm in permissions)
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
            member = await self.entity_helper.get_or_fetch_member(guildId, user)
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
            member = await self.entity_helper.get_or_fetch_member(guildId, user)
        elif isinstance(user, discord.Member):
            member = user
        else:
            raise ValueError("user must be an int or a discord.Member")
        if member is None:
            return False
        role_id = None
        if isinstance(role, int):
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
            member = await self.entity_helper.get_or_fetch_member(guildId, user)
        elif isinstance(user, discord.Member):
            member = user
        else:
            raise ValueError("user must be an int or a discord.Member")

        return await self.has_permission(member, discord.Permissions(administrator=True))
