import inspect
import os
import typing

import discord
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums.system_actions import SystemActions
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.tacobot import TacoBot
from discord.ext import commands


class ModEventsCog(TacobotCog):
    def __init__(self, bot: TacoBot):
        super().__init__(bot, "mod_events")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: typing.Union[discord.User, discord.Member]):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"User {user.name} was banned from {guild.name}")
        self.tracking_db.track_system_action(
            guild_id=guild.id, action=SystemActions.USER_BAN, data={"user_id": user.id}
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"User {user.name} was unbanned from {guild.name}")
        self.tracking_db.track_system_action(
            guild_id=guild.id, action=SystemActions.USER_UNBAN, data={"user_id": user.id}
        )

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        _method = inspect.stack()[0][3]
        self.log.debug(
            0,
            f"{self._module}.{self._class}.{_method}",
            f"Automod action {execution.action.type} was executed on {execution.member.name if execution.member else execution.user_id} in {execution.guild.name}",
        )
        self.tracking_db.track_system_action(
            guild_id=execution.guild.id,
            action=SystemActions.AUTOMOD_ACTION,
            data={
                "user_id": execution.user_id,
                "action": execution.action.to_dict(),
                "guild_id": execution.guild.id,
                "content": execution.content,
                "message_id": execution.message_id,
                "channel_id": execution.channel_id,
                "rule": {"id": execution.rule_id, "type": execution.rule_trigger_type},
                "matched": {"keyword": execution.matched_keyword, "content": execution.matched_content},
            },
        )


async def setup(bot):
    await bot.add_cog(ModEventsCog(bot))
