import inspect
import os
import traceback
import typing

import discord
from bot.cogs.lib import discordhelper, logger, settings, utils
from bot.cogs.lib.enums import loglevel
from bot.cogs.lib.enums.system_actions import SystemActions
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from bot.cogs.lib.mongodb.twitch import TwitchDatabase
from discord.ext import commands


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
        self.twitch_db = TwitchDatabase()
        self.tracking_db = TrackingDatabase()
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
            streamteam_settings = self.settings.get_settings(guild_id, self.SETTINGS_SECTION)
            if not streamteam_settings:
                # raise exception if there are no streamteam settings
                self.log.error(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No streamteam settings found for guild {guild_id}",
                )
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
                self.twitch_db.remove_stream_team_request(guild_id, user.id)
                twitch_user = self.twitch_db.get_user_twitch_info(user.id)
                twitch_name = "UNKNOWN"
                if twitch_user:
                    twitch_name = twitch_user['twitch_name']

                if log_channel:
                    await self.messaging.send_embed(
                        channel=log_channel,
                        title=self.settings.get_string(guild_id, "streamteam_removal_tile"),
                        message=self.settings.get_string(
                            guild_id,
                            "streamteam_removal_message",
                            user=f"{utils.get_user_display_name(user)}",
                            team_name=team_name,
                            twitch_name=twitch_name,
                        ),
                        color=0xFF0000,
                    )

                self.tracking_db.track_command_usage(
                    guildId=guild_id,
                    channelId=payload.channel_id if payload.channel_id else None,
                    userId=payload.user_id,
                    command="streamteam",
                    subcommand="remove",
                    args=[
                        {"type": "reaction"},
                        {
                            "payload": {
                                "message_id": str(payload.message_id),
                                "channel_id": str(payload.channel_id),
                                "guild_id": str(payload.guild_id),
                                "user_id": str(payload.user_id),
                                "emoji": payload.emoji.name,
                                "event_type": payload.event_type,
                                # "burst": payload.burst,
                            }
                        },
                    ],
                )

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
                unknown = self.settings.get_string(guild_id, "unknown")
                # send a message to the user and ask them their twitch name if it is not yet set
                twitch_name = unknown
                twitch_info = self.twitch_db.get_user_twitch_info(user.id)
                if twitch_info:
                    twitch_name = twitch_info['twitch_name']
                    if twitch_name is None or twitch_name == "":
                        twitch_name = unknown
                # add user to the stream team requests
                self.twitch_db.add_stream_team_request(guildId=guild_id, userId=user.id, twitchName=twitch_name)

                if log_channel:
                    twitch_name = unknown if twitch_name is None else twitch_name
                    await self.messaging.send_embed(
                        channel=log_channel,
                        title=self.settings.get_string(guild_id, "streamteam_join_title"),
                        message=self.settings.get_string(
                            guild_id, "streamteam_join_message", user=user, team_name=team_name, twitch_name=twitch_name
                        ),
                        color=0x00FF00,
                    )

                self.tracking_db.track_command_usage(
                    guildId=guild_id,
                    channelId=payload.channel_id if payload.channel_id else None,
                    userId=payload.user_id,
                    command="streamteam",
                    subcommand="add",
                    args=[
                        {"type": "reaction"},
                        {
                            "payload": {
                                "message_id": str(payload.message_id),
                                "channel_id": str(payload.channel_id),
                                "guild_id": str(payload.guild_id),
                                "user_id": str(payload.user_id),
                                "emoji": payload.emoji.name,
                                "event_type": payload.event_type,
                                # "burst": payload.burst,
                            }
                        },
                    ],
                )
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
    async def invite(self, ctx, twitchName: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            if twitchName is None:
                twitchInfo = self.twitch_db.get_user_twitch_info(ctx.author.id)
                if twitchInfo is not None:
                    twitchName = twitchInfo['twitch_name']
            if twitchName is None:
                try:
                    await self.messaging.send_embed(
                        channel=ctx.author,
                        title=self.settings.get_string(guild_id, "error"),
                        message=self.settings.get_string(guild_id, "streamteam_invite_no_twitch_name_message"),
                        color=0xFF0000,
                    )
                    return
                except discord.Forbidden:
                    # if we cant send to user, then we send to channel
                    await self.messaging.send_embed(
                        channel=ctx.channel,
                        title=self.settings.get_string(guild_id, "error"),
                        message=self.settings.get_string(guild_id, "streamteam_invite_no_twitch_name_message"),
                        footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                        color=0xFF0000,
                        delete_after=30,
                    )
                    return

            await self._invite_user(ctx, ctx.author, twitchName)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="streamteam",
                subcommand="invite",
                args=[{"type": "command"}, {"twitchName": twitchName}],
            )

        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @team.command(aliases=["invite-user"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def invite_user(self, ctx, user: discord.User, twitchName: str) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            guild_id = ctx.guild.id if ctx.guild else 0
            await self._invite_user(ctx, user, twitchName)
            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="streamteam",
                subcommand="invite",
                args=[{"type": "command"}, {"twitchName": twitchName}, {"user_id": str(user.id)}],
            )
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _invite_user(self, ctx, user: discord.User, twitchName: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            # get the streamteam settings from settings
            streamteam_settings = self.settings.get_settings(guild_id, self.SETTINGS_SECTION)
            if not streamteam_settings:
                # raise exception if there are no streamteam settings
                self.log.error(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"No streamteam settings found for guild {guild_id}",
                )
                await self.discord_helper.notify_bot_not_initialized(ctx, "streamteam")
                return
            unknown = self.settings.get_string(guild_id, "unknown")
            twitch_name = twitchName.lower().strip()

            log_channel_id = streamteam_settings["log_channel"]
            log_channel = None
            if log_channel_id:
                log_channel = await self.discord_helper.get_or_fetch_channel(log_channel_id)
            team_name = streamteam_settings["name"]

            self.twitch_db.set_user_twitch_info(user.id, twitchName)
            self.tracking_db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.LINK_TWITCH_TO_DISCORD,
                data={"user_id": str(user.id), "twitch_name": twitch_name.lower()},
            )
            self.twitch_db.add_stream_team_request(guildId=ctx.guild.id, twitchName=twitchName, userId=user.id)

            await self.messaging.send_embed(
                channel=ctx.channel,
                title=self.settings.get_string(guild_id, "success"),
                message=self.settings.get_string(
                    guild_id,
                    "streamteam_invite_success_message",
                    user=f"{utils.get_user_display_name(user)}",
                    team_name=team_name,
                    twitch_name=twitchName,
                ),
                footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                color=0x00FF00,
                delete_after=30,
            )

            if log_channel:
                twitch_name = unknown if twitch_name is None else twitch_name
                await self.messaging.send_embed(
                    channel=log_channel,
                    title=self.settings.get_string(guild_id, "streamteam_join_title"),
                    message=self.settings.get_string(
                        guild_id,
                        "streamteam_join_message",
                        user=f"{utils.get_user_display_name(user)}",
                        team_name=team_name,
                        twitch_name=twitchName,
                    ),
                    color=0x00FF00,
                )

        except Exception as ex:
            self.log.error(ctx.guild.id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

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
    await bot.add_cog(StreamTeam(bot))
