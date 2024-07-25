import inspect
import os
import traceback
import typing

from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel
from bot.lib.enums.member_status import MemberStatus
from bot.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands


class UserLookup(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "user_lookup"

        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
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
                avatar: typing.Union[str, None] = (
                    member.avatar.url if member.avatar is not None else member.default_avatar.url
                )
                self.tracking_db.track_user(
                    guildId=guild.id,
                    userId=member.id,
                    username=member.name,
                    discriminator=member.discriminator,
                    avatar=avatar,
                    displayname=member.display_name,
                    created=member.created_at,
                    bot=member.bot,
                    system=member.system,
                    status=MemberStatus.from_discord(member.status),
                )

        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    # on events, get the user id and username and store it in the database
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        _method = inspect.stack()[0][3]
        try:
            if member is None or member.guild is None:
                return
            avatar: typing.Union[str, None] = (
                member.avatar.url if member.avatar is not None else member.default_avatar.url
            )
            self.log.debug(
                member.guild.id,
                f"{self._module}.{self._class}.{_method}",
                f"User {member.id} joined guild {member.guild.id}",
            )
            self.tracking_db.track_user(
                guildId=member.guild.id,
                userId=member.id,
                username=member.name,
                discriminator=member.discriminator,
                avatar=avatar,
                displayname=member.display_name,
                created=member.created_at,
                bot=member.bot,
                system=member.system,
                status=MemberStatus.from_discord(member.status),
            )
        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after) -> None:
        _method = inspect.stack()[0][3]
        try:
            if after is None or after.guild is None:
                return
            avatar: typing.Union[str, None] = after.avatar.url if after.avatar is not None else after.default_avatar.url
            self.log.debug(
                after.guild.id,
                f"{self._module}.{self._class}.{_method}",
                f"User {after.id} updated in guild {after.guild.id}",
            )
            self.tracking_db.track_user(
                guildId=after.guild.id,
                userId=after.id,
                username=after.name,
                discriminator=after.discriminator,
                avatar=avatar,
                displayname=after.display_name,
                created=after.created_at,
                bot=after.bot,
                system=after.system,
                status=MemberStatus.from_discord(after.status),
            )
        except Exception as e:
            self.log.error(after.guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section=self.SETTINGS_SECTION)

    def get_settings(self, guildId: int, section: str) -> dict:
        if not section or section == "":
            raise Exception("No section provided")
        cog_settings = self.settings.get_settings(guildId, section)
        if not cog_settings:
            raise Exception(f"No '{section}' settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        return self.get_settings(guildId=guildId, section="tacos")


async def setup(bot):
    await bot.add_cog(UserLookup(bot))
