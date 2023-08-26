import inspect
import os
import traceback

import discord
from bot.cogs.lib import discordhelper, logger, loglevel, mongo, settings, tacotypes
from bot.cogs.lib.system_actions import SystemActions
from discord.ext import commands


class JoinLeaveTracker(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        _method = inspect.stack()[0][3]
        # remove all tacos from the user
        guild_id = member.guild.id
        try:
            if not member or member.bot or member.system:
                return

            _method = inspect.stack()[0][3]
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{member} left the server")
            self.db.remove_all_tacos(guild_id, member.id)
            self.db.track_tacos_log(
                guildId=guild_id,
                toUserId=member.id,
                fromUserId=self.bot.user.id,
                count=0,
                reason="leaving the server",
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(tacotypes.TacoTypes.LEAVE_SERVER),
            )
            self.db.track_user_join_leave(guildId=guild_id, userId=member.id, join=False)
            self.db.track_system_action(
                guild_id=guild_id, action=SystemActions.LEAVE_SERVER, data={"user_id": str(member.id)}
            )
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        _method = inspect.stack()[0][3]
        guild_id = member.guild.id
        try:
            if not member or member.bot or member.system:
                return

            await self.discord_helper.taco_give_user(
                guild_id,
                self.bot.user,
                member,
                self.settings.get_string(guild_id, "taco_reason_join"),
                tacotypes.TacoTypes.JOIN_SERVER,
            )

            self.db.track_user_join_leave(guildId=guild_id, userId=member.id, join=True)
            self.db.track_system_action(
                guild_id=guild_id, action=SystemActions.JOIN_SERVER, data={"user_id": str(member.id)}
            )
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())


async def setup(bot) -> None:
    await bot.add_cog(JoinLeaveTracker(bot))
