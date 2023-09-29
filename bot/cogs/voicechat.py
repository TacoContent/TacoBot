import inspect
import os
import traceback

from bot.cogs.lib import discordhelper, logger, settings
from bot.cogs.lib.enums import loglevel, tacotypes
from discord.ext import commands



class VoiceChatCog(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "voicechat"

        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after) -> None:
        _method = inspect.stack()[0][3]
        if not member.guild:
            return

        if member.bot or member.system:
            return

        guild_id = member.guild.id

        try:
            if before.channel is not None and after.channel is None:
                self.log.debug(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"User {member.name} left voice channel"
                )
                return

            if before.channel is None and after.channel is not None:
                cog_settings = self.get_cog_settings(guild_id)
                # this channel is not one we care about
                if str(after.channel.id) not in cog_settings.get("channels", []):
                    return

                reason_msg = self.settings.get_string(guild_id, "voicechat_create_channel_reason")

                await self.discord_helper.taco_give_user(
                    guildId=guild_id,
                    fromUser=self.bot.user,
                    toUser=member,
                    reason=reason_msg,
                    give_type=tacotypes.TacoTypes.CREATE_VOICE_CHANNEL,
                    taco_amount=0,
                )
                return
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


async def setup(bot):
    await bot.add_cog(VoiceChatCog(bot))
