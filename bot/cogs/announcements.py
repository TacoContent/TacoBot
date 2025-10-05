"""Announcements tracking cog.

This cog listens to Discord gateway events related to messages for a configured
set of guild text channels and persists a simplified representation of those
messages as "announcements" in the announcements database collection. The
primary purposes are:

* Historical tracking of important announcement channel content (including edits & soft deletes)
* Potential future analytics / display in external dashboards or APIs
* Decoupling of Discord message structures from persistence layer via model classes

Key Behaviors:
----------------
* Only operates for guilds where the cog has been enabled in settings
* Optionally imports existing historical messages (on guild availability) up to a
  configured limit when `import_existing` is true
* Tracks create, edit, delete, bulk delete events; for deletions a `deleted_at`
  timestamp is stored (soft delete) so historical content remains accessible

Settings (per guild / section: announcements):
----------------------------------------------
enabled: bool
    Enables or disables tracking for the guild.
channels: list[str]
    String IDs of channels to track.
import_existing: bool
    If true, on guild availability the cog will backfill messages.
import_limit: int (default ~100 if not set)
    Max number of messages to pull per channel during import.
last_import: int (epoch seconds)
    When the last import occurred (set by this cog).

Design Notes:
-------------
Message processing funnels through `_track_announcement` to ensure a single
validation & persistence path. The persistence layer (AnnouncementsDatabase)
handles the upsert behavior keyed on guild, channel & message IDs.
"""

import datetime
import inspect
import os
import traceback
import typing

import discord
import pytz
from bot import tacobot  # pylint: disable=no-name-in-module
from bot.lib import discordhelper, utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.messaging import Messaging
from bot.lib.models.AnnouncementEntry import AnnouncementEntry
from bot.lib.mongodb.announcements import AnnouncementsDatabase
from discord.ext import commands



class AnnouncementsCog(TacobotCog):
    """Cog responsible for tracking announcement messages.

    Listens to message lifecycle events and stores the relevant message
    metadata & content in the announcements database for configured channels.

    Attributes
    ----------
    discord_helper : discordhelper.DiscordHelper
        Utility helper for common Discord-related convenience operations.
    messaging : Messaging
        Internal messaging/notification abstraction (unused directly here but
        injected for future extension potential).
    announcements_db : AnnouncementsDatabase
        Database accessor handling announcement persistence (upsert writes).
    """

    def __init__(self, bot: tacobot.TacoBot) -> None:
        """Initialize the announcements cog.

        Parameters
        ----------
        bot : tacobot.TacoBot
            The running bot instance used for event dispatch and settings access.
        """
        super().__init__(bot, "announcements")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)

        self.announcements_db = AnnouncementsDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_guild_available(self, guild) -> None:
        """Handle guild availability to optionally backfill existing messages.

        When the guild becomes available and the cog settings specify both
        `enabled` and `import_existing`, each configured channel is scanned up
        to the configured `import_limit` (defaulting to 100) and messages are
        persisted through the shared tracking method.

        Parameters
        ----------
        guild : discord.Guild | None
            The guild that just became available (can be None in rare cases
            from upstream library edge conditions; safely ignored).
        """
        _method = inspect.stack()[0][3]
        try:
            if guild is None:
                return

            cog_settings = self.get_cog_settings(guild.id)
            if not cog_settings.get("enabled", False):
                return

            if not cog_settings.get("import_existing", False):
                return

            # get the channels we care about
            channels = cog_settings.get("channels", [])
            if not channels or len(channels) == 0:
                return

            for channel_id in channels:
                channel = guild.get_channel(int(channel_id))
                if not channel or not isinstance(channel, discord.TextChannel):
                    continue

                async for message in channel.history(limit=cog_settings.get("import_limit", 100)):
                    await self._track_announcement(message)

            # update the last_import time in the settings
            date = datetime.datetime.now(pytz.UTC)
            timestamp = utils.to_timestamp(date)
            self.settings.settings_db.set_setting(guild.id, self.SETTINGS_SECTION, 'last_import', timestamp)

        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Track a newly created guild message if it matches channel filters.

        Parameters
        ----------
        message : discord.Message
            The created message event payload.
        """
        await self._track_announcement(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """Track an edited message (using the post-edit state).

        Parameters
        ----------
        before : discord.Message
            Original message prior to edit.
        after : discord.Message
            Updated message after edit.
        """
        await self._track_announcement(after)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """Track a soft-deleted message by recording its deletion timestamp.

        Parameters
        ----------
        message : discord.Message
            The deleted message (if cached).
        """
        await self._track_announcement(message, deleted=True)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """Handle raw delete events when the original message cache is absent.

        Currently this method is a placeholder; if a message isn't cached the
        code path to reconstruct partial data for persistence could be added
        here in the future.

        Parameters
        ----------
        payload : discord.RawMessageDeleteEvent
            Raw deletion payload (may or may not contain cached message).
        """
        if payload.cached_message:
            # if this exists, then it SHOULD have been handled by on_message_delete
            return

        # otherwise, we have to track it ourselves
        # channel = self.bot.get_channel(payload.channel_id)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: typing.List[discord.Message]) -> None:
        """Track a bulk delete operation.

        Each deleted message is individually processed so that `deleted_at`
        timestamps are recorded consistently.

        Parameters
        ----------
        messages : list[discord.Message]
            Collection of deleted messages (only those still cached).
        """
        for message in messages:
            await self._track_announcement(message, deleted=True)

    async def _track_announcement(self, message: discord.Message, deleted: bool = False) -> None:
        """Core tracking logic for announcement messages.

        Validates that the message belongs to a guild with tracking enabled
        and that its channel is in the configured channel set. Constructs an
        `AnnouncementEntry` (with optional deletion timestamp) and delegates
        persistence to the announcements database layer.

        Parameters
        ----------
        message : discord.Message
            Discord message instance to evaluate / persist.
        deleted : bool, optional
            Whether the message has been deleted (soft delete). Defaults to False.
        """
        _method = inspect.stack()[0][3]
        try:
            if not message.guild:
                self.log.warn(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    "Message is not in a guild",
                )
                return

            cog_settings = self.get_cog_settings(message.guild.id)
            if not cog_settings.get("enabled", False):
                self.log.warn(
                    message.guild.id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Announcement tracking disabled for guild {message.guild.id}",
                )
                return

            # do we care about this channel?
            if str(message.channel.id) not in cog_settings.get("channels", []):
                self.log.warn(
                    message.guild.id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Ignoring announcement message {message.id} in channel {message.channel.id}",
                )
                return

            # track this announcement
            self.log.debug(
                message.guild.id,
                f"{self._module}.{self._class}.{_method}",
                f"Tracking announcement message {message.id} in channel {message.channel.id}",
            )

            deleted_at: typing.Optional[int] = (
                int(utils.to_timestamp(datetime.datetime.now(pytz.UTC))) if deleted else None
            )
            self.log.debug(
                message.guild.id,
                f"{self._module}.{self._class}.{_method}",
                f"Tracking announcement: message.id={message.id}",
            )
            self.announcements_db.track_announcement(AnnouncementEntry.from_message(message, deleted_at=deleted_at))

        except Exception as e:
            self.log.error(
                message.guild.id if message.guild else 0,
                f"{self._module}.{self._class}._track_announcement",
                f"Error tracking announcement: {e}",
                None,
            )


async def setup(bot):
    """Async setup entrypoint used by discord.py extension loader.

    Parameters
    ----------
    bot : tacobot.TacoBot
        The bot instance to which this cog will be added.
    """
    await bot.add_cog(AnnouncementsCog(bot))
