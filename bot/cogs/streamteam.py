import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import inspect
import collections

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib.system_actions import SystemActions
from .lib.messaging import Messaging


class StreamTeam(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.SETTINGS_SECTION = "streamteam"
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id or 0
        try:
            if guild_id is None or guild_id == 0:
                return
            if payload.event_type != 'REACTION_REMOVE':
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if not user or user.bot or user.system:
                return

            # get the streamteam settings from settings
            streamteam_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not streamteam_settings:
                # raise exception if there are no streamteam settings
                self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"No streamteam settings found for guild {guild_id}")
                await self.discord_helper.notify_bot_not_initialized(message, "streamteam")
                return

            # get the reaction emoji
            emoji = streamteam_settings["emoji"]
            team_name = streamteam_settings["name"]
            # get the message ids to check
            watch_message_ids = streamteam_settings["message_ids"]
            # get the log channel id
            log_channel_id = streamteam_settings["log_channel"]
            log_channel = None
            if log_channel_id:
                log_channel = await self.discord_helper.get_or_fetch_channel(log_channel_id)

            # check if the message that is reacted to is in the list of message ids and the emoji is one that is configured.
            if str(message.id) in watch_message_ids and str(payload.emoji) in emoji:
                # add user to the stream team requests
                self.db.remove_stream_team_request(guild_id, user.id)
                twitch_user = self.db.get_user_twitch_info(user.id)
                twitch_name = "UNKNOWN"
                if twitch_user:
                    twitch_name = twitch_user['twitch_name']

                if log_channel:
                    await self.messaging.send_embed(
                        channel=log_channel,
                        title=self.settings.get_string(guild_id, "streamteam_removal_tile"),
                        message=self.settings.get_string(guild_id, "streamteam_removal_message",
                            user=f"{utils.get_user_display_name(user)}",
                            team_name=team_name,
                            twitch_name=twitch_name),
                        color=0xff0000)

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_reaction_add(self, payload) -> None:
        _method = inspect.stack()[0][3]
        guild_id = payload.guild_id or 0
        try:
            # ignore if not in a guild
            if guild_id is None or guild_id == 0:
                return
            if payload.event_type != 'REACTION_ADD':
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_helper.get_or_fetch_user(payload.user_id)
            if user is None or user.system or user.bot:
                return

            # get the streamteam settings from settings
            cog_settings = self.get_cog_settings(guild_id)

            # get the reaction emoji
            emoji = cog_settings.get("emoji", [])
            team_name = cog_settings.get("name", "")

            if len(emoji) == 0 or team_name == "":
                return

            # get the message ids to check
            watch_message_ids = cog_settings.get("message_ids", [])
            # get the log channel id
            log_channel_id = cog_settings.get("log_channel", None)
            log_channel = None
            if log_channel_id:
                log_channel = await self.discord_helper.get_or_fetch_channel(log_channel_id)

            # check if the message that is reacted to is in the list of message ids and the emoji is one that is configured.
            if str(message.id) in watch_message_ids and str(payload.emoji) in emoji:
                # add user to the stream team requests
                self.db.add_stream_team_request(guild_id, utils.get_user_display_name(user), user.id)
                unknown = self.settings.get_string(guild_id, "unknown")
                # send a message to the user and ask them their twitch name if it is not yet set
                twitch_name = unknown
                # twitch_user = self.db.get_user_twitch_info(user.id)
                # if not twitch_user:
                #     try:
                #         ctx_dict = {"bot": self.bot, "author": user, "guild": None, "channel": None}
                #         ctx = collections.namedtuple("Context", ctx_dict.keys())(*ctx_dict.values())
                #         twitch_name = await self.discord_helper.ask_text(ctx, user,
                #             self.settings.get_string(guild_id, "twitch_name_title"),
                #             self.settings.get_string(guild_id, "twitch_name_question", team_name=team_name),
                #             timeout=60)
                #         if twitch_name:
                #             twitch_name = utils.get_last_section_in_url(twitch_name.lower().strip())

                #             self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{utils.get_user_display_name(user)} requested to set twitch name {twitch_user}")
                #             self.db.set_user_twitch_info(user.id, twitch_name)
                # self.db.track_system_action(
                #     guild_id=guild_id,
                #     action=SystemActions.LINK_TWITCH_TO_DISCORD,
                #     data={"user_id": str(user.id), "twitch_name": twitch_name.lower()},
                # )
                #             await self.messaging.send_embed(user,
                #                 self.settings.get_string(guild_id, "success"),
                #                 self.settings.get_string(guild_id, "streamteam_set_twitch_name_message", twitch_name=twitch_name),
                #                 color=0x00ff00)
                #     except discord.Forbidden as e:
                #         # cant send them a message. Put it in the channel...
                #         await self.messaging.send_embed(channel,
                #             self.settings.get_string(guild_id, "error"),
                #             self.settings.get_string(guild_id, "twitch_name_dm_error", user=user.mention),
                #             footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                #             color=0xff0000, delete_after=30)

                # else:
                #     twitch_name = twitch_user['twitch_name']

                if log_channel:
                    twitch_name = unknown if twitch_name is None else twitch_name
                    await self.messaging.send_embed(
                        channel=log_channel,
                        title=self.settings.get_string(guild_id, "streamteam_join_title"),
                        message=self.settings.get_string(guild_id, "streamteam_join_message",
                            user=user, team_name=team_name, twitch_name=twitch_name),
                        color=0x00ff00)
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())


    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs) -> None:
        _method = inspect.stack()[0][3]
        self.log.error(0, f"{self._module}.{self._class}.{_method}", f"{str(event)}", traceback.format_exc())

    @commands.group()
    @commands.guild_only()
    async def team(self, ctx):
        pass

    @team.command()
    @commands.guild_only()
    async def invite(self, ctx, twitchName: str = None) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:

            if twitchName is None:
                twitchName = self.db.get_user_twitch_info(ctx.author.id)['twitch_name']
            if twitchName is None:
                try:
                    await self.messaging.send_embed(
                        channel=ctx.author,
                        title=self.settings.get_string(guild_id, "error"),
                        message=self.settings.get_string(guild_id, "streamteam_invite_no_twitch_name_message"),
                        color=0xff0000,)
                    return
                except discord.Forbidden:
                    # if we cant send to user, then we send to channel
                    await self.messaging.send_embed(
                        channel=ctx.channel,
                        title=self.settings.get_string(guild_id, "error"),
                        message=self.settings.get_string(guild_id, "streamteam_invite_no_twitch_name_message"),
                        footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                        color=0xff0000,
                        delete_after=30,)
                    return

            await self._invite_user(ctx, ctx.author, twitchName)

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @team.command(aliases=["invite-user"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def invite_user(self, ctx, user: discord.User, twitchName: str) -> None:
        await self._invite_user(ctx, user, twitchName)

    async def _invite_user(self, ctx, user: discord.User, twitchName: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            # get the streamteam settings from settings
            streamteam_settings = self.settings.get_settings(self.db, guild_id, self.SETTINGS_SECTION)
            if not streamteam_settings:
                # raise exception if there are no streamteam settings
                self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"No streamteam settings found for guild {guild_id}")
                await self.discord_helper.notify_bot_not_initialized(ctx, "streamteam")
                return
            unknown = self.settings.get_string(guild_id, "unknown")
            twitch_name = twitchName.lower().strip()

            log_channel_id = streamteam_settings["log_channel"]
            log_channel = None
            if log_channel_id:
                log_channel = await self.discord_helper.get_or_fetch_channel(log_channel_id)
            team_name = streamteam_settings["name"]

            self.db.set_user_twitch_info(user.id, twitchName)
            self.db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.LINK_TWITCH_TO_DISCORD,
                data={"user_id": str(user.id), "twitch_name": twitch_name.lower()},
            )
            self.db.add_stream_team_request(guildId=ctx.guild.id, twitchName=twitchName, userId=user.id)

            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "success"),
                message=self.settings.get_string(guild_id, "streamteam_invite_success_message", user=f"{utils.get_user_display_name(user)}", team_name=team_name, twitch_name=twitchName),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                color=0x00ff00,
                delete_after=30,)

            if log_channel:
                twitch_name = unknown if twitch_name is None else twitch_name
                await self.messaging.send_embed(
                    channel=log_channel,
                    title=self.settings.get_string(guild_id, "streamteam_join_title"),
                    message=self.settings.get_string(guild_id, "streamteam_join_message", user=f"{utils.get_user_display_name(user)}", team_name=team_name, twitch_name=twitchName),
                    color=0x00ff00,)

        except Exception as ex:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

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
    await bot.add_cog(StreamTeam(bot))
