import inspect
import os
import traceback

from bot.lib import discordhelper
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.models.DiscordUser import DiscordUser
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.tacobot import TacoBot
from discord.ext import commands


class UserLookupCog(TacobotCog):
    def __init__(self, bot: TacoBot) -> None:
        super().__init__(bot, "user_lookup")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(bot)

        self.tracking_db = TrackingDatabase()
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_guild_available(self, guild) -> None:
        _method = inspect.stack()[0][3]
        try:
            if guild is None:
                return
            # pull this from the settings and see if we should do the import of all users

            enabled = False
            cog_settings = self.get_cog_settings(guild.id)
            if cog_settings is not None:
                enabled = cog_settings.get("full_import_enabled", False)

            if not enabled:
                return

            self.log.debug(
                guild.id, f"{self._module}.{self._class}.{_method}", f"Performing full user import for guild {guild.id}"
            )
            for member in guild.members:
                self.log.debug(
                    guild.id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Tracking user {member.name} in guild {guild.name}",
                )

                self.tracking_db.track_discord_user(user=DiscordUser.fromUser(member))
                # self.tracking_db.track_user(
                #     guildId=guild.id,
                #     userId=member.id,
                #     username=member.name,
                #     discriminator=member.discriminator,
                #     avatar=avatar,
                #     displayname=member.display_name,
                #     created=member.created_at,
                #     bot=member.bot,
                #     system=member.system,
                #     status=MemberStatus.from_discord(member.status),
                # )

        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    # on events, get the user id and username and store it in the database
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        _method = inspect.stack()[0][3]
        try:
            if member is None or member.guild is None:
                return
            self.log.debug(
                member.guild.id,
                f"{self._module}.{self._class}.{_method}",
                f"User {member.id} joined guild {member.guild.id}",
            )
            self.tracking_db.track_discord_user(user=DiscordUser.fromUser(member))
            # self.tracking_db.track_user(
            #     guildId=member.guild.id,
            #     userId=member.id,
            #     username=member.name,
            #     discriminator=member.discriminator,
            #     avatar=avatar,
            #     displayname=member.display_name,
            #     created=member.created_at,
            #     bot=member.bot,
            #     system=member.system,
            #     status=MemberStatus.from_discord(member.status),
            # )
        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after) -> None:
        _method = inspect.stack()[0][3]
        try:
            if after is None or after.guild is None:
                return

            self.log.debug(
                after.guild.id,
                f"{self._module}.{self._class}.{_method}",
                f"User {after.id} updated in guild {after.guild.id}",
            )
            self.tracking_db.track_discord_user(user=DiscordUser.fromUser(after))
            # self.tracking_db.track_user(
            #     guildId=after.guild.id,
            #     userId=after.id,
            #     username=after.name,
            #     discriminator=after.discriminator,
            #     avatar=avatar,
            #     displayname=after.display_name,
            #     created=after.created_at,
            #     bot=after.bot,
            #     system=after.system,
            #     status=MemberStatus.from_discord(after.status),
            # )
        except Exception as e:
            self.log.error(after.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())


async def setup(bot):
    await bot.add_cog(UserLookupCog(bot))
