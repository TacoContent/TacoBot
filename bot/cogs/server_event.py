import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import datetime
import inspect

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import settings
from .lib import mongo
from .lib import tacotypes


class ServerEvent(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.db = mongo.MongoDatabase()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent) -> None:
        _method: str = inspect.stack()[0][3]
        if event is None or event.guild is None or event.creator is None:
            # if creator is none, no one to give tacos to
            return
        guild_id = event.guild.id
        try:
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=event.creator,
                reason=f"Scheduled an Event: {event.name}",
                give_type=tacotypes.TacoTypes.EVENT_CREATE,
                taco_amount=5,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return

    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent) -> None:
        _method: str = inspect.stack()[0][3]
        if event is None or event.guild is None or event.creator is None:
            # if creator is none, no one to give tacos to
            return
        guild_id = event.guild.id
        try:
            now = datetime.datetime.utcnow()
            if event.start_time < now:
                return

            if event.status == discord.EventStatus.completed or event.status == discord.EventStatus.ended:
                return

            # if event hasn't started, take back the tacos
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=event.creator,
                reason=f"Canceled an Event: {event.name}",
                give_type=tacotypes.TacoTypes.EVENT_CANCEL,
                taco_amount=-5,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent) -> None:
        _method: str = inspect.stack()[0][3]
        if before is None or before.guild is None or before.creator is None:
            # if creator is none, no one to give tacos to
            return
        guild_id = before.guild.id
        try:
            if after is None or after.creator is None:
                return

            if after.status == discord.EventStatus.cancelled:
                # if event hasn't started, take back the tacos
                await self.discord_helper.taco_give_user(
                    guildId=guild_id,
                    fromUser=self.bot.user,
                    toUser=after.creator,
                    reason=f"Canceled an Event: {after.name}",
                    give_type=tacotypes.TacoTypes.EVENT_CANCEL,
                    taco_amount=-5,
                )

            if after.status == discord.EventStatus.completed or after.status == discord.EventStatus.ended:
                # if event hasn't started, take back the tacos
                await self.discord_helper.taco_give_user(
                    guildId=guild_id,
                    fromUser=self.bot.user,
                    toUser=after.creator,
                    reason=f"Completed an Event: {after.name}",
                    give_type=tacotypes.TacoTypes.EVENT_COMPLETE,
                    taco_amount=5,
                )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return

    @commands.Cog.listener()
    async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User) -> None:
        _method: str = inspect.stack()[0][3]
        if event is None or event.guild is None or user is None:
            # if creator is none, no one to give tacos to
            return
        guild_id = event.guild.id
        try:
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=user,
                reason=f"Joining an Event: {event.name}",
                give_type=tacotypes.TacoTypes.EVENT_JOIN,
                taco_amount=5,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return

    @commands.Cog.listener()
    async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User) -> None:
        _method: str = inspect.stack()[0][3]
        if event is None or event.guild is None or user is None:
            # if creator is none, no one to give tacos to
            return
        guild_id = event.guild.id
        try:
            await self.discord_helper.taco_give_user(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=user,
                reason=f"Joining an Event: {event.name}",
                give_type=tacotypes.TacoTypes.EVENT_LEAVE,
                taco_amount=-5,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return


async def setup(bot):
    await bot.add_cog(ServerEvent(bot))
