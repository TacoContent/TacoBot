import asyncio
import inspect
import os
import traceback
import typing

import discord
import requests
from bot.lib import discordhelper, logger, settings, utils
from bot.lib.enums import loglevel, tacotypes
from bot.lib.enums.system_actions import SystemActions
from bot.lib.messaging import Messaging
from bot.lib.mongodb.live import LiveDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.twitch import TwitchDatabase
from discord.ext import commands


class LiveNow(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.SETTINGS_SECTION = "live_now"
        self.live_db = LiveDatabase()
        self.twitch_db = TwitchDatabase()
        self.tracking_db = TrackingDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        _method = inspect.stack()[0][3]
        guild_id = 0
        if before.guild:
            guild_id = before.guild.id
        elif after.guild:
            guild_id = after.guild.id

        try:
            cog_settings = self.get_cog_settings(guild_id)

            if not cog_settings.get("enabled", False):
                return

            # get the tacos settings
            taco_settings = self.get_tacos_settings(guild_id)

            before_streaming_activities = []
            after_streaming_activities = []

            before_streaming_activities_temp = [
                a for a in before.activities if a.type == discord.ActivityType.streaming
            ]
            after_streaming_activities_temp = [a for a in after.activities if a.type == discord.ActivityType.streaming]

            if len(before_streaming_activities_temp) == 0:
                if before.activity and before.activity.type == discord.ActivityType.streaming:
                    before_streaming_activities = [before.activity]
            if len(after_streaming_activities_temp) == 0:
                if after.activity and after.activity.type == discord.ActivityType.streaming:
                    after_streaming_activities = [after.activity]

            for bsa in before_streaming_activities_temp:
                # if item is not in the list, add it
                if len([b for b in before_streaming_activities if b.platform.lower() == bsa.platform.lower()]) == 0:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Adding {bsa.platform} to before_streaming_activities for {before.display_name}",
                    )
                    before_streaming_activities.append(bsa)

            for asa in after_streaming_activities_temp:
                if len([a for a in after_streaming_activities if a.platform.lower() == asa.platform.lower()]) == 0:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Adding {asa.platform} to after_streaming_activities for {after.display_name}",
                    )
                    after_streaming_activities.append(asa)

            # WENT LIVE
            for asa in after_streaming_activities:
                await asyncio.sleep(1)

                tracked = self.live_db.get_tracked_live(guild_id, after.id, asa.platform)
                is_tracked = tracked != None and len(tracked) > 0
                # if it is already tracked, then we don't need to do anything
                if is_tracked:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"{after.display_name} is already tracked for {asa.platform}",
                    )
                    await self.add_live_roles(after, cog_settings)
                    continue

                self.log.info(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"{after.display_name} started streaming on {asa.platform}",
                )

                # if we get here, then we need to track the user live activity
                self.live_db.track_live(guildId=guild_id, userId=after.id, platform=asa.platform, url=asa.url)
                self.live_db.track_live_activity(
                    guildId=guild_id, userId=after.id, live=True, platform=asa.platform, url=asa.url
                )

                await self.add_live_roles(after, cog_settings)

                twitch_name: typing.Union[str, None] = None
                if asa.platform.lower() == "twitch":
                    twitch_name = self.handle_twitch_live(after, after_streaming_activities)
                elif asa.platform.lower() == "youtube":
                    self.handle_youtube_live(after, after_streaming_activities)
                else:
                    self.handle_other_live(after, after_streaming_activities)

                logging_channel_id = cog_settings.get("logging_channel", None)
                if logging_channel_id:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Logging live post {after.display_name} ({asa.platform}) to channel {logging_channel_id}",
                    )
                    # this is double posting. need to figure out why
                    await self.log_live_post(int(logging_channel_id), asa, after, twitch_name)

                # give the user tacos for going live
                # technically this doesnt need to be sent to the db, but it is for consistency
                taco_amount = taco_settings.get("stream_count", 5)
                reason_msg = self.settings.get_string(guild_id, "taco_reason_stream")
                await self.discord_helper.taco_give_user(
                    guildId=guild_id,
                    fromUser=self.bot.user,
                    toUser=before,
                    reason=reason_msg,
                    give_type=tacotypes.TacoTypes.STREAM,
                    taco_amount=taco_amount,
                )

            # ENDED STREAM
            # HMMMM. This is not triggering. Need to figure out why
            # for bsa in before_streaming_activities:
            #     # sleep for a bit to make sure the live role is removed before we clean up the db
            #     await asyncio.sleep(1)

            #     # check if bsa is in after_streaming_activities
            #     found_bsa = len([a for a in after_streaming_activities if a.url == bsa.url and a.platform == bsa.platform]) > 0
            #     if found_bsa:
            #         self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{after.display_name} is still live on {bsa.platform}")
            #         # this activity exists in both lists, so it is still live
            #         continue

            #     tracked = self.live_db.get_tracked_live(guildId=guild_id, userId=before.id, platform=bsa.platform)
            #     is_tracked = tracked != None and len(tracked) > 0
            #     # if it is not tracked, then we don't need to do anything
            #     if not is_tracked or not tracked:
            #         self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{after.display_name} is not tracked for {bsa.platform}")
            #         await self.remove_live_roles(before, cog_settings)
            #         continue

            #     # if we get here, then we need to untrack the user live activity
            #     self.log.info(guild_id, f"{self._module}.{self._class}.{_method}", f"{before.display_name} stopped streaming on {bsa.platform}")
            #     # track the END activity
            #     self.live_db.track_live_activity(guild_id, before.id, False, bsa.platform, url=bsa.url)

            #     logging_channel_id = cog_settings.get("logging_channel", None)
            #     if logging_channel_id:
            #         logging_channel = await self.discord_helper.get_or_fetch_channel(int(logging_channel_id))
            #         if logging_channel:
            #             for tracked_item in tracked:
            #                 message_id = tracked_item.get("message_id", None)
            #                 if message_id:
            #                     try:
            #                         message = await logging_channel.fetch_message(int(message_id))
            #                         if message:
            #                             self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Deleting LIVE 🔴 message ({message_id}) from channel {logging_channel}")
            #                             await message.delete()
            #                     except discord.errors.NotFound:
            #                         self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", f"Message {message_id} not found in channel {logging_channel}")

            #     # remove all tracked items for this live platform (should only be one)
            #     self.live_db.untrack_live(guild_id, before.id, bsa.platform)

            #     await self.remove_live_roles(before, cog_settings)

            if len(before_streaming_activities) == 0 and len(after_streaming_activities) == 0:
                try:
                    await self.remove_live_roles(after, cog_settings)
                    await self.clean_up_live(guild_id, after.id)
                except Exception as e:
                    self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return

    async def remove_live_roles(self, user: discord.Member, cog_settings: dict):
        watch_groups = cog_settings.get("watch", [])
        for wg in watch_groups:
            watch_roles = wg.get("roles", [])
            # do opposite here, to put back to original roles
            # we add the "remove_roles" and remove the "add_roles"
            add_roles = wg.get("remove_roles", [])
            remove_roles = wg.get("add_roles", [])
            await self.discord_helper.add_remove_roles(
                user=user, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles
            )

    async def add_live_roles(self, user: discord.Member, cog_settings: dict):
        # get the watch groups
        watch_groups = cog_settings.get("watch", [])
        for wg in watch_groups:
            watch_roles = wg.get("roles", [])
            add_roles = wg.get("add_roles", [])
            remove_roles = wg.get("remove_roles", [])
            # add / remove roles defined in the watch groups
            await self.discord_helper.add_remove_roles(
                user=user, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles
            )

    def handle_other_live(
        self, user: discord.Member, activities: typing.List[discord.Streaming]
    ) -> typing.Union[str, None]:
        _method = inspect.stack()[0][3]
        guild_id = user.guild.id
        # get non-youtube activities and non-twitch activities
        other_activities = [
            a
            for a in activities
            if a.platform is not None and a.platform.lower() != "youtube" and a.platform.lower() != "twitch"
        ]

        if len(other_activities) > 1:
            self.log.warn(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{user.display_name} has more than one streaming activity",
            )

        for a in other_activities:
            self.log.info(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{user.display_name} started streaming on an {a.platform} platform",
            )
        return None

    def handle_youtube_live(
        self, user: discord.Member, activities: typing.List[discord.Streaming]
    ) -> typing.Union[str, None]:
        _method = inspect.stack()[0][3]
        guild_id = user.guild.id
        # get only the youtube activity
        youtube_activities = [a for a in activities if a.platform is not None and a.platform.lower() == "youtube"]
        if len(youtube_activities) > 1:
            self.log.warn(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{user.display_name} has more than one streaming activity",
            )

        if len(youtube_activities) == 0:
            self.log.warn(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{user.display_name} has no youtube streaming activity",
            )
            return None

        activity = youtube_activities[0]

        self.log.info(
            guild_id, f"{self._module}.{self._class}.{_method}", f"{user.display_name} started streaming on youtube"
        )
        return None

    def handle_twitch_live(
        self, user: discord.Member, activities: typing.List[discord.Streaming]
    ) -> typing.Union[str, None]:
        _method = inspect.stack()[0][3]
        guild_id = user.guild.id

        # get only the twitch activity
        twitch_activities = [a for a in activities if a.platform is not None and a.platform.lower() == "twitch"]

        twitch_name: typing.Optional[str] = None
        twitch_info = self.twitch_db.get_user_twitch_info(user.id)
        if len(twitch_activities) > 1:
            self.log.warn(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{user.display_name} has more than one streaming activity",
            )
        # Only add the twitch name if we don't have it already
        # and only if we can get the twitch name from the url or activity
        # or if we have a different twitch name in the database
        for activity in twitch_activities:
            if activity.twitch_name:
                twitch_name = activity.twitch_name.lower()
                break
            elif activity.url and "twitch.tv/" in activity.url.lower():
                twitch_name = activity.url.lower().split("twitch.tv/")[1]
                break
        if twitch_info:
            twitch_info_name = twitch_info.get("twitch_name", None)
        else:
            twitch_info_name = None
        if twitch_name and twitch_name != "" and twitch_name != twitch_info_name:
            self.log.info(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{user.display_name} has a different twitch name: {twitch_name}",
            )
            self.twitch_db.set_user_twitch_info(user.id, twitch_name)
            self.tracking_db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.LINK_TWITCH_TO_DISCORD,
                data={"user_id": str(user.id), "twitch_name": twitch_name.lower()},
            )

        elif not twitch_name and twitch_info_name:
            twitch_name = twitch_info_name
        if not twitch_name:
            self.log.error(
                guild_id, f"{self._module}.{self._class}.{_method}", f"{user.display_name} has no twitch name"
            )

        return twitch_name

    async def log_live_post(
        self, channel_id: int, activity: discord.Streaming, user: discord.Member, twitch_name: typing.Union[str, None]
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = user.guild.id
        # get the logging channel
        logging_channel = None
        if channel_id:
            logging_channel = self.bot.get_channel(channel_id)
        # if we are logging this to a channel...
        if logging_channel:
            profile_icon: typing.Union[str, None] = None

            if twitch_name:
                profile_icon = self.get_user_profile_image(twitch_name)

            description = f"{activity.name}\n\n<{activity.url}>"

            fields = []
            if activity.game:
                fields.append(
                    {"name": self.settings.get_string(guild_id, "game"), "value": activity.game, "inline": False}
                )
            if activity.platform:
                platform_emoji = self.find_platform_emoji(user.guild, activity.platform)
                emoji = ""
                if platform_emoji:
                    emoji = f"<:{platform_emoji.name}:{platform_emoji.id}> "

                fields.append(
                    {
                        "name": self.settings.get_string(guild_id, "platform"),
                        "value": f"{emoji}{activity.platform}",
                        "inline": True,
                    }
                )

            profile_icon: typing.Union[str, None] = (
                profile_icon if profile_icon else user.avatar.url if user.avatar else user.default_avatar.url
            )

            if activity.assets:
                image_url = activity.assets.get("large_image", None)
                if image_url:
                    if "twitch:" in image_url and not profile_icon and not twitch_name:
                        twitch_name = image_url.replace("twitch:", "")
                        profile_icon = self.get_user_profile_image(twitch_name)

            user_display_name = utils.get_user_display_name(user)
            message = await self.messaging.send_embed(
                logging_channel,
                f"🔴 {user_display_name}",
                description,
                fields,
                thumbnail=profile_icon,
                author=user,
                color=0x6A0DAD,
            )

            # this should update the existing entry with the channel and message id
            self.live_db.track_live(
                guild_id, user.id, activity.platform, logging_channel.id, message.id, url=activity.url
            )

    async def clean_up_live(self, guild_id: int, user_id: int) -> None:
        _method = inspect.stack()[0][3]
        if guild_id is None or user_id is None:
            return

        all_tracked_for_user = self.live_db.get_tracked_live_by_user(guildId=guild_id, userId=user_id)
        tracked_count = len(all_tracked_for_user)
        if all_tracked_for_user is None or tracked_count == 0:
            return

        user = await self.discord_helper.get_or_fetch_member(guildId=guild_id, userId=user_id)
        if user is None:
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Could not find user {user_id}")
            return

        self.log.debug(
            guild_id,
            f"{self._module}.{self._class}.{_method}",
            f"Cleaning up {tracked_count} tracked live items for user {user_id}",
        )
        cog_settings = self.get_cog_settings(guild_id)

        logging_channel_id = cog_settings.get("logging_channel", None)
        logging_channel = None
        if logging_channel_id:
            logging_channel = await self.discord_helper.get_or_fetch_channel(int(logging_channel_id))

        for tracked in all_tracked_for_user:
            platform = tracked.get("platform", "UNKNOWN")
            url = tracked.get("url", None)
            self.log.info(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"{utils.get_user_display_name(user)} stopped streaming on {platform}",
            )
            self.live_db.track_live_activity(guild_id, user.id, False, platform, url=url)

            if logging_channel:
                message_id = tracked.get("message_id", None)
                if message_id is not None and message_id != "None" and message_id != "":
                    try:
                        message = await logging_channel.fetch_message(int(message_id))
                        if message:
                            await message.delete()
                    except discord.errors.NotFound:
                        self.log.debug(
                            guild_id,
                            f"{self._module}.{self._class}.{_method}",
                            f"Message {message_id} not found in channel {logging_channel}",
                        )

            # remove all tracked items for this live platform (should only be one)
            self.live_db.untrack_live(guild_id, user.id, platform)
            await self.remove_live_roles(user, cog_settings)

    def find_platform_emoji(self, guild: discord.Guild, platform: str) -> typing.Union[discord.Emoji, None]:
        if guild is None:
            return None

        platform_emoji = discord.utils.find(lambda m: m.name.lower() == platform.lower(), guild.emojis)
        return platform_emoji

    def get_user_profile_image(self, twitch_user: typing.Union[str, None]) -> typing.Union[str, None]:
        _method = inspect.stack()[0][3]
        try:
            if twitch_user:
                result = requests.get(f"http://decapi.me/twitch/avatar/{twitch_user}")
                if result.status_code == 200:
                    return result.text
                else:
                    self.log.debug(
                        0, f"{self._module}.{self._class}.{_method}", f"Failed to get profile image for {twitch_user}"
                    )
                    self.log.info(0, f"{self._module}.{self._class}.{_method}", f"{result.text}")
            return None
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            return None

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
    await bot.add_cog(LiveNow(bot))
