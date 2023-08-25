# this is for restricted channels that only allow specific commands in chat.
import asyncio
import discord
import inspect
import traceback
import os
import re
import typing

from discord.ext import commands
from .lib import settings, discordhelper, logger, loglevel, mongo
from .lib.messaging import Messaging


class Restricted(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.SETTINGS_SECTION = "restricted"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            # if in a DM, ignore
            if message.guild is None:
                return
            # if the message is from a bot, ignore
            if message.author.bot:
                return

            guild_id = message.guild.id

            # {
            #   channels: [
            #   {
            #       id: "",
            #       allowed: ["", ""],
            #       denied: ["", ""],
            #       deny_message: "",
            #   ]
            # }

            # get the suggestion settings from settings
            cog_settings = self.get_cog_settings(guild_id)

            # get the suggestion channel ids from settings
            restricted_channels: typing.List[dict] = [
                c for c in cog_settings.get("channels", []) if str(c['id']) == str(message.channel.id)
            ]
            restricted_channel: typing.Union[dict, None] = None
            if restricted_channels:
                restricted_channel = restricted_channels[0]
            # if channel.id is not in restricted_channel_ids[] return
            if not restricted_channel:
                return

            silent = restricted_channel.get('silent', True)
            # get allowed commands from settings
            allowed = restricted_channel.get("allowed", [])
            # get denied commands from settings
            denied = restricted_channel.get("denied", [])
            # get the deny message from settings
            deny_message = self.settings.get_string(guild_id, "restricted_deny_message")
            if "deny_message" in restricted_channel:
                deny_message = restricted_channel.get("deny_message")

            # if message matches the allowed[] regular expressions then continue
            if not any(re.search(r, message.content) for r in allowed) or any(
                re.search(r, message.content) for r in denied
            ):
                # wait
                await asyncio.sleep(0.5)
                await message.delete()

                if not silent:
                    await self.messaging.send_embed(
                        channel=message.channel,
                        title=self.settings.get_string(guild_id, "restricted"),
                        message=self.settings.get_string(
                            guild_id, "restricted_deny_message", user=message.author.mention, reason=deny_message
                        ),
                        delete_after=20,
                        color=0xFF0000,
                    )
        except discord.NotFound as nf:
            self.log.info(guild_id, f"{self._module}.{self._class}.{_method}", f"Message not found: {nf}")
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    def get_cog_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            raise Exception(f"No cog settings found for guild {guildId}")
        return cog_settings

    def get_tacos_settings(self, guildId: int = 0) -> dict:
        cog_settings = self.settings.get_settings(self.db, guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings


async def setup(bot):
    await bot.add_cog(Restricted(bot))
