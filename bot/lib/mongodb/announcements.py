"""MongoDB persistence layer for announcement tracking.

This module provides the `AnnouncementsDatabase` class which encapsulates the
storage concerns for announcement messages captured by the `AnnouncementsCog`.

Responsibilities:
-----------------
* Normalize and upsert announcement entries keyed by (guild, channel, message)
* Record tracking timestamp distinct from message lifecycle timestamps
* Support idempotent re-processing (subsequent calls update existing record)

Design Choices:
---------------
* Upserts ensure edits or delayed event delivery do not create duplicates.
* IDs are stored as strings for consistency with other collections (if any)
    that treat large numeric IDs uniformly and to avoid potential integer size
    issues in environments with differing numeric capabilities.
"""

import datetime
import inspect
import os
import traceback

import pytz
from bot.lib import utils
from bot.lib.enums import loglevel
from bot.lib.models.AnnouncementEntry import AnnouncementEntry
from bot.lib.mongodb.database import Database


class AnnouncementsDatabase(Database):
    """Database accessor for announcement entries.

    Extends the base `Database` abstraction to provide a focused method for
    tracking (creating or updating) announcements. Other query / retrieval
    methods can be added as required by higher level features.
    """

    def __init__(self) -> None:
        super().__init__()
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        pass

    def track_announcement(self, entry: "AnnouncementEntry") -> None:
        """Insert or update an announcement record.

        Parameters
        ----------
        entry : AnnouncementEntry
            The announcement entry containing message metadata & content snapshot.

        Behavior
        --------
        * Ensures a database connection is open.
        * Derives a `tracked_at` timestamp separate from message creation/edit times.
        * Performs an upsert keyed on (guild_id, channel_id, message_id)
            to avoid duplicate records and to reflect message edits/deletions.
        """
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None or self.client is None:
                self.open()

            timestamp = utils.to_timestamp(datetime.datetime.now(pytz.UTC))

            payload = {
                "author_id": entry.author_id,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "deleted_at": entry.deleted_at,
                "message": entry.message.to_dict() if entry.message else None,
                "tracked_at": timestamp,
            }

            self.connection.announcements.update_one(  # type: ignore
                {
                    "guild_id": str(entry.guild_id),
                    "channel_id": str(entry.channel_id),
                    "message_id": str(entry.message_id),
                },
                {"$set": payload},
                upsert=True,
            )
        except Exception as ex:
            self.log(
                guildId=entry.guild_id,
                level=loglevel.LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
