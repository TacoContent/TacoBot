"""TacoHelper - Handles taco giving, logging, and taco-related operations.

This helper class is responsible for:
- Giving tacos to users
- Logging taco transactions to log channels
- Purging tacos from users
- Fetching taco settings for guilds
"""

import inspect
import os
import traceback
import typing

import discord
from bot.lib import logger, utils
from bot.lib.enums import loglevel, tacotypes
from bot.lib.helpers import MessageHelper
from bot.lib.mongodb.tacos import TacosDatabase
from bot.lib.settings import Settings


class TacoHelper:
    """Helper class for taco system operations."""

    def __init__(self, bot, entity_helper=None) -> None:
        """Initialize TacoHelper with bot instance.

        Args:
            bot: The Discord bot instance
            entity_helper: Optional EntityHelper instance for fetching entities
        """
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]

        self.bot = bot
        self.settings = Settings()
        self.tacos_db = TacosDatabase()
        self.message_helper = MessageHelper(bot=self.bot, settings=self.settings)

        # EntityHelper for fetching channels
        # Import here to avoid circular dependency
        if entity_helper is None:
            from bot.lib.helpers.entity_helper import EntityHelper

            self.entity_helper = EntityHelper(bot)
        else:
            self.entity_helper = entity_helper

        log_level = loglevel.LogLevel.DEBUG
        try:
            log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        finally:
            self.log = logger.Log(minimumLogLevel=log_level)

    def get_taco_count(self, guildId: int, userId: int) -> typing.Optional[int]:
        """Get the current taco count for a user in a guild.

        Args:
            guildId: The guild ID
            userId: The user ID

        Returns:
            Current taco count for the user
        """
        _method = inspect.stack()[0][3]
        try:
            taco_count = self.tacos_db.get_tacos_count(guildId, userId)
            return taco_count
        except Exception as e:
            self.log.error(guildId, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return None

    async def give_tacos(
        self,
        guildId: int,
        fromUser: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]],
        toUser: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]],
        reason: typing.Optional[str],
        give_type: tacotypes.TacoTypes = tacotypes.TacoTypes.CUSTOM,
        taco_amount: int = 1,
    ) -> int:
        """Give tacos to a user and log the transaction.

        Args:
            guildId: The guild ID where tacos are being given
            fromUser: The user giving tacos
            toUser: The user receiving tacos
            reason: Optional reason for giving tacos
            give_type: Type of taco transaction (CUSTOM, REACTION, etc.)
            taco_amount: Default taco amount (overridden by settings if type is configured)

        Returns:
            Total taco count for the receiving user after the transaction
        """
        _method = inspect.stack()[0][3]
        try:
            if toUser is None or fromUser is None:
                self.log.warn(guildId, f"{self._module}.{self._class}.{_method}", "toUser or fromUser is None")
                return 0
            # get taco settings
            taco_settings = self.get_taco_settings(guildId=guildId)
            taco_count = taco_amount
            taco_type_key = tacotypes.TacoTypes.get_string_from_taco_type(give_type)
            if taco_type_key not in taco_settings:
                self.log.debug(
                    guildId,
                    f"{self._module}.{self._class}.{_method}",
                    f"Key {taco_type_key} not found in taco settings. Using taco_amount ({taco_amount}) as taco count",
                )
                taco_count = taco_count
            else:
                taco_count = taco_settings.get(taco_type_key, taco_amount)

            reason_msg = reason if reason else self.settings.get_string(guildId, "no_reason")

            total_taco_count = self.tacos_db.add_tacos(guildId, toUser.id, taco_count)
            await self.log_taco_transaction(
                guild_id=guildId,
                toMember=toUser,
                fromMember=fromUser,
                count=taco_count,
                total_tacos=total_taco_count,
                reason=reason_msg,
                type=give_type,
            )

            self.tacos_db.track_tacos_log(
                guildId=guildId,
                toUserId=toUser.id,
                fromUserId=fromUser.id,
                count=taco_count,
                reason=reason_msg,
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(give_type),
            )
            return total_taco_count
        except Exception as e:
            self.log.error(guildId, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return 0

    async def log_taco_purge(
        self,
        guild_id: int,
        toMember: typing.Union[discord.User, discord.Member],
        fromMember: typing.Union[discord.User, discord.Member],
        reason: str,
    ):
        """Log a taco purge event (all tacos removed from a user).

        Args:
            guild_id: The guild ID where tacos were purged
            toMember: The user whose tacos were purged
            fromMember: The user who performed the purge
            reason: Reason for the purge
        """
        _method = inspect.stack()[0][3]
        try:
            taco_settings = self.get_taco_settings(guildId=guild_id)
            taco_log_channel_id = taco_settings["taco_log_channel_id"]
            log_channel = await self.entity_helper.get_or_fetch_channel(int(taco_log_channel_id))

            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{fromMember.name} purged all tacos from {toMember.name} for {reason}",
            )
            if log_channel:
                await log_channel.send(
                    self.settings.get_string(
                        guild_id, "tacos_purged_log", touser=toMember.name, fromuser=fromMember.name, reason=reason
                    )
                )
            self.tacos_db.track_tacos_log(
                guildId=guild_id,
                toUserId=toMember.id,
                fromUserId=fromMember.id,
                count=0,
                reason=reason,
                type=tacotypes.TacoTypes.get_db_type_from_taco_type(tacotypes.TacoTypes.PURGE),
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    async def log_taco_transaction(
        self,
        guild_id: int,
        toMember: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]],
        fromMember: typing.Optional[typing.Union[discord.User, discord.Member, discord.ClientUser]],
        count: int,
        total_tacos: int,
        reason: str,
        type: tacotypes.TacoTypes = tacotypes.TacoTypes.CUSTOM,
    ):
        """Log a taco transaction to the configured taco log channel.

        Args:
            guild_id: The guild ID where the transaction occurred
            toMember: The user who received/lost tacos
            fromMember: The user who initiated the transaction
            count: Number of tacos given/taken (negative for losses)
            total_tacos: Total taco count after the transaction
            reason: Reason for the transaction
            type: Type of taco transaction
        """
        _method = inspect.stack()[0][3]
        try:
            if toMember is None or fromMember is None:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", "toMember or fromMember is None")
                return
            taco_settings = self.get_taco_settings(guildId=guild_id)
            taco_log_channel_id = taco_settings["taco_log_channel_id"]
            log_channel = await self.entity_helper.get_or_fetch_channel(int(taco_log_channel_id))
            taco_word = self.settings.get_string(guild_id, "taco_plural")
            if count == 1:
                taco_word = self.settings.get_string(guild_id, "taco_singular")

            total_taco_word = self.settings.get_string(guild_id, "taco_plural")
            if total_tacos == 1:
                total_taco_word = self.settings.get_string(guild_id, "taco_singular")

            action = self.settings.get_string(guild_id, "tacos_log_action_received")
            if count < 0:
                action = self.settings.get_string(guild_id, "tacos_log_action_lost")

            positive_count = abs(count)

            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{utils.get_user_display_name(toMember)} {action} {positive_count} {taco_word} from {utils.get_user_display_name(fromMember)} for {reason}",
            )
            if log_channel:
                fields = [
                    {"name": "▶ TO USER", "value": toMember.name},
                    {"name": "◀ FROM USER", "value": fromMember.name},
                    {"name": f"🎬 {action.upper()}", "value": f"{positive_count} {taco_word}"},
                    {"name": "🌮 TOTAL TACOS", "value": f"{total_tacos} {total_taco_word}"},
                    {"name": "ℹ REASON", "value": reason},
                    {"name": "✨ TYPE", "value": type.name},
                ]

                await self.message_helper.send_embed(
                    channel=log_channel, title="", message="", fields=fields, author=fromMember
                )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    def get_taco_settings(self, guildId: int = 0) -> dict:
        """Get taco settings for a guild.

        Args:
            guildId: The guild ID to fetch settings for

        Returns:
            Dictionary of taco settings

        Raises:
            Exception: If no taco settings found for the guild
        """
        cog_settings = self.settings.get_settings(guildId, "tacos")
        if not cog_settings:
            raise Exception(f"No tacos settings found for guild {guildId}")
        return cog_settings
