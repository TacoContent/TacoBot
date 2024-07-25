import inspect
import os
import traceback

from bot.lib import discordhelper, logger, settings
from bot.lib.enums import loglevel, tacotypes
from bot.lib.mongodb.tracking import TrackingDatabase
from discord.ext import commands


class MessageTracker(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.SETTINGS_SECTION = "message_track"
        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        guild_id = 0
        _method = inspect.stack()[0][3]
        try:
            # if in a DM, ignore
            if message.guild is None:
                return
            # if the message is from a bot, ignore
            if message.author.bot:
                return
            guild_id = message.guild.id

            # if message is a bot command, ignore
            # loop all command prefixes
            for prefix in await self.bot.command_prefix(message):
                if message.content.startswith(prefix):
                    return

            if self.tracking_db.is_first_message_today(guild_id, message.author.id):
                await self.give_user_first_message_tacos(guild_id, message.author.id, message.channel.id, message.id)

            # track the message in the database
            self.tracking_db.track_message(guild_id, message.author.id, message.channel.id, message.id)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    async def give_user_first_message_tacos(self, guild_id, user_id, channel_id, message_id):
        _method = inspect.stack()[0][3]
        try:
            # create context
            # self, bot=None, author=None, guild=None, channel=None, message=None, invoked_subcommand=None, **kwargs
            # get guild from id
            guild = self.bot.get_guild(guild_id)
            # fetch member from id
            member = guild.get_member(user_id)
            # get channel
            channel = None
            message = None

            # get bot
            bot = self.bot
            ctx = self.discord_helper.create_context(
                bot=bot, guild=guild, author=member, channel=channel, message=message
            )

            # track that the user answered the question.
            self.tracking_db.track_first_message(guild_id, member.id, channel_id, message_id)

            tacos_settings = self.get_tacos_settings(guild_id)
            amount = tacos_settings.get("first_message_count", 5)

            reason_msg = self.settings.get_string(guild_id, "first_message_reason")

            await self.discord_helper.taco_give_user(
                guild_id, self.bot.user, member, reason_msg, tacotypes.TacoTypes.FIRST_MESSAGE, taco_amount=amount
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

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
    await bot.add_cog(MessageTracker(bot))
