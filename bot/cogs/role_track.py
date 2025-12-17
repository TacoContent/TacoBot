import inspect
import os
import traceback

import discord

from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from discord.ext import commands


class GuildRoleTrack(TacobotCog):
    def __init__(self, bot: TacoBot, tracking_db: TrackingDatabase, settings: Settings):
        super().__init__(bot, "guild_role_track", settings=settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.tracking_db = tracking_db

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild) -> None:
        _method = inspect.stack()[0][3]
        try:
            if guild is None:
                return

            self.tracking_db.track_roles(roles=guild.roles)

        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        _method = inspect.stack()[0][3]
        try:
            if role is None or role.guild is None:
                return

            self.tracking_db.track_roles(roles=[role])
        except Exception as e:
            self.log.error(role.guild.id if role and role.guild else 0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        _method = inspect.stack()[0][3]
        try:
            if before is None or after is None or before.guild is None:
                return

            self.tracking_db.track_role(role=after)
        except Exception as e:
            self.log.error(before.guild.id if before and before.guild else 0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        _method = inspect.stack()[0][3]
        try:
            if role is None or role.guild is None:
                return

            self.tracking_db.track_role_deletion(guildId=role.guild.id, roleId=role.id)
        except Exception as e:
            self.log.error(role.guild.id if role and role.guild else 0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        _method = inspect.stack()[0][3]
        try:
            if before is None or after is None or before.guild is None:
                return

            # Check for role changes
            before_roles = set(before.roles)
            after_roles = set(after.roles)

            added_roles = after_roles - before_roles
            removed_roles = before_roles - after_roles

            self.tracking_db.track_roles(roles=added_roles)
            self.tracking_db.track_roles(roles=removed_roles)
        except Exception as e:
            self.log.error(before.guild.id if before and before.guild else 0, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

async def setup(bot):
    settings = Settings()
    tracking_db = TrackingDatabase()
    await bot.add_cog(GuildRoleTrack(bot=bot, tracking_db=tracking_db, settings=settings))
