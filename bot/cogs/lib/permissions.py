import enum
import typing
import discord
from . import settings
from . import mongo
from . import utils

class Permissions:
    def __init__(self) -> None:
        self.settings = settings.Settings()
        self.db = mongo.MongoDatabase()

    def has_permission(self, user: typing.Optional[discord.Member], permissions: typing.Optional[discord.Permissions] = None):
        if user is None:
            return False
        if permissions is None:
            return True
        return user.guild_permissions >= permissions

    def has_role(self, user: discord.Member, role: discord.Role):
        return role in user.roles
