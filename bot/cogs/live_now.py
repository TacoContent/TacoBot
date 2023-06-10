import json
from random import random
import discord
from discord.ext import commands
import asyncio
import traceback
import sys
import os
import glob
import typing
import math
import re
import uuid
import requests

from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands import has_permissions, CheckFailure
import inspect

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider
from .lib import tacotypes

class LiveNow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)

        self.SETTINGS_SECTION = "live_now"

        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "live_now.__init__", "Initialized")

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
            if not cog_settings:
                self.log.warn(guild_id, "live_now.on_member_update", f"No live_now settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                return

            # get the tacos settings
            taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
            if not taco_settings:
                self.log.error(guild_id, "live_now.on_member_update", f"No tacos settings found for guild {guild_id}")
                return

            before_streaming_activities = []
            after_streaming_activities = []

            before_streaming_activities_temp = [ a for a in before.activities if a.type == discord.ActivityType.streaming ]
            after_streaming_activities_temp = [ a for a in after.activities if a.type == discord.ActivityType.streaming ]

            if len(before_streaming_activities_temp) == 0:
                if before.activity and before.activity.type == discord.ActivityType.streaming:
                    before_streaming_activities = [ before.activity ]
            if len(after_streaming_activities_temp) == 0:
                if after.activity and after.activity.type == discord.ActivityType.streaming:
                    after_streaming_activities = [ after.activity ]

            for bsa in before_streaming_activities_temp:
                # if item is not in the list, add it
                if len([a for a in before_streaming_activities if a.url == bsa.url]) == 0:
                    before_streaming_activities.append(bsa)

            for asa in after_streaming_activities_temp:
                if len([a for a in after_streaming_activities if a.url == asa.url]) == 0:
                    after_streaming_activities.append(asa)

            # remove items that exist in both lists
            # for bsa in before_streaming_activities:
            #     for asa in after_streaming_activities:
            #         if asa.url == bsa.url and asa.platform == bsa.platform:
            #             # dont remove the after items so we always check for the "went live" event
            #             # after_streaming_activities.remove(asa)
            #             before_streaming_activities.remove(bsa)

            # check if the user is in any of the "add" roles, but has no streaming activity
            # remove them from those roles
            if len(before_streaming_activities) == 0 and len(after_streaming_activities) == 0:
                watch_groups = cog_settings.get("watch", [])
                for wg in watch_groups:
                    watch_roles = wg.get("roles", [])
                    add_roles = wg.get("remove_roles", [])
                    remove_roles = wg.get("add_roles", [])
                    await self.add_remove_roles(user=after, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)

                await self.clean_up_live(guild_id, after.id)
                return

            # any item left in after_streaming_activities is a new streaming activity
            # any item left in before_streaming_activities is a streaming activity that has ended

            # WENT LIVE
            for asa in after_streaming_activities:
                tracked = self.db.get_tracked_live(guild_id, after.id, asa.platform)
                is_tracked = tracked != None and tracked.count() > 0

                await self.add_live_roles(after, cog_settings)

                # if it is already tracked, then we don't need to do anything
                if is_tracked:
                    self.log.debug(guild_id, "live_now.on_member_update", f"{after.display_name} is already tracked for {asa.platform}")
                    continue

                # check if asa is in before_streaming_activities
                # found_asa = len([b for b in before_streaming_activities if b.url == asa.url and b.platform == asa.platform]) > 0
                # # this activity exists in both lists, so it is not a new live
                # if found_asa :
                #     # self.log.debug(guild_id, "live_now.on_member_update", f"{after.display_name} is already tracked for {asa.platform}")
                #     continue

                self.log.info(guild_id, "live_now.on_member_update", f"{after.display_name} started streaming on {asa.platform}")

                # if we get here, then we need to track the user live activity
                self.db.track_live(
                    guildId=guild_id,
                    userId=after.id,
                    platform=asa.platform,
                    url=asa.url
                )
                self.db.track_live_activity(
                    guildId=guild_id,
                    userId=after.id,
                    live=True,
                    platform=asa.platform,
                    url=asa.url
                )

                twitch_name: typing.Union[str, None] = None
                if asa.platform.lower() == "twitch":
                    twitch_name = self.handle_twitch_live(after, after_streaming_activities)
                elif asa.platform.lower() == "youtube":
                    self.handle_youtube_live(after, after_streaming_activities)
                else:
                    self.handle_other_live(after, after_streaming_activities)

                logging_channel_id = cog_settings.get("logging_channel", None)
                if logging_channel_id:
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
                    taco_amount=taco_amount )


            # ENDED STREAM
            for bsa in before_streaming_activities:

                # check if bsa is in after_streaming_activities
                found_bsa = len([a for a in after_streaming_activities if a.url == bsa.url and a.platform == bsa.platform]) > 0
                if found_bsa:
                    # this activity exists in both lists, so it is still live
                    continue

                await self.remove_live_roles(before, cog_settings)

                tracked = self.db.get_tracked_live(guild_id, before.id, bsa.platform)
                is_tracked = tracked != None and tracked.count() > 0
                # if it is not tracked, then we don't need to do anything
                if not is_tracked:
                    self.log.debug(guild_id, "live_now.on_member_update", f"{after.display_name} is not tracked for {bsa.platform}")
                    continue

                # if we get here, then we need to untrack the user live activity
                self.log.info(guild_id, "live_now.on_member_update", f"{before.display_name} stopped streaming on {bsa.platform}")
                # track the END activity
                self.db.track_live_activity(guild_id, before.id, False, bsa.platform, url=bsa.url)

                logging_channel_id = cog_settings.get("logging_channel", None)
                logging_channel = self.bot.get_channel(int(logging_channel_id))
                if logging_channel:
                    for tracked_item in tracked:
                        message_id = tracked_item.get("message_id", None)
                        if message_id:
                            try:
                                message = await logging_channel.fetch_message(int(message_id))
                                if message:
                                    await message.delete()
                            except discord.errors.NotFound:
                                self.log.warn(guild_id, "live_now.on_member_update", f"Message {message_id} not found in channel {logging_channel}")

                # remove all tracked items for this live platform (should only be one)
                self.db.untrack_live(guild_id, before.id, bsa.platform)

        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())
            return

    async def remove_live_roles(self, user: discord.Member, cog_settings: dict):
        watch_groups = cog_settings.get("watch", [])
        for wg in watch_groups:
            watch_roles = wg.get("roles", [])
            # do opposite here, to put back to original roles
            # we add the "remove_roles" and remove the "add_roles"
            add_roles = wg.get("remove_roles", [])
            remove_roles = wg.get("add_roles", [])
            await self.add_remove_roles(user=user, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)

    async def add_live_roles(self, user: discord.Member, cog_settings: dict):
        # get the watch groups
        watch_groups = cog_settings.get("watch", [])
        for wg in watch_groups:
            watch_roles = wg.get("roles", [])
            add_roles = wg.get("add_roles", [])
            remove_roles = wg.get("remove_roles", [])
            # add / remove roles defined in the watch groups
            await self.add_remove_roles(user=user, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)

    def handle_other_live(self, user: discord.Member, activities: typing.List[discord.Streaming]) -> typing.Union[str, None]:
        guild_id = user.guild.id
        if len(activities) > 1:
            self.log.warn(guild_id, "live_now.handle_other_live", f"{user.display_name} has more than one streaming activity")
        activity = activities[0]
        self.log.info(guild_id, "live_now.handle_other_live", f"{user.display_name} started streaming on an {activity.platform} platform")
        return None

    def handle_youtube_live(self, user: discord.Member, activities: typing.List[discord.Streaming]) -> typing.Union[str, None]:
        guild_id = user.guild.id
        if len(activities) > 1:
            self.log.warn(guild_id, "live_now.handle_other_live", f"{user.display_name} has more than one streaming activity")

        self.log.info(guild_id, "live_now.handle_youtube_live", f"{user.display_name} started streaming on youtube")
        return None

    def handle_twitch_live(self, user: discord.Member, activities: typing.List[discord.Streaming]) -> typing.Union[str, None]:
        guild_id = user.guild.id

        twitch_name: str = None
        twitch_info = self.db.get_user_twitch_info(user.id)
        if len(activities) > 1:
            self.log.warn(guild_id, "live_now.handle_other_live", f"{user.display_name} has more than one streaming activity")
        # Only add the twitch name if we don't have it already
        # and only if we can get the twitch name from the url or activity
        # or if we have a different twitch name in the database
        for activity in activities:
            if activity.twitch_name:
                twitch_name = activity.twitch_name.lower()
                break
            elif activity.url and "twitch.tv/" in activity.url.lower():
                twitch_name = activity.url.lower().split("twitch.tv/")[1]
                break
            if twitch_name:
                # track the users twitch name
                self.db.set_user_twitch_info(user.id, "", twitch_name.lower())
        if twitch_info:
            twitch_info_name = twitch_info.get("twitch_name", None)
        else:
            twitch_info_name = None
        if twitch_name and twitch_name != "" and twitch_name != twitch_info_name:
            self.log.info(guild_id, "live_now.on_member_update", f"{user.display_name} has a different twitch name: {twitch_name}")
            self.db.set_user_twitch_info(user.id, "", twitch_name)
        elif not twitch_name and twitch_info_name:
            twitch_name = twitch_info_name
        if not twitch_name:
            self.log.error(guild_id, "live_now.on_member_update", f"{user.display_name} has no twitch name")

        return twitch_name

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No live_now settings found for guild {guildId}")
        return cog_settings

    async def log_live_post(self, channel_id: int, activity: discord.Streaming, user: discord.Member, twitch_name: typing.Union[str, None]) -> None:
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
                fields.append({ "name": self.settings.get_string(guild_id, "game"), "value": activity.game, "inline": False },)
            if activity.platform:
                platform_emoji = self.find_platform_emoji(user.guild, activity.platform)
                emoji = ""
                if platform_emoji:
                    emoji = f"<:{platform_emoji.name}:{platform_emoji.id}> "

                fields.append({ "name": self.settings.get_string(guild_id, "platform"), "value": f"{emoji}{activity.platform}", "inline": True },)

            profile_icon = profile_icon if profile_icon else user.avatar.url

            if activity.assets:
                image_url = activity.assets.get("large_image", None)
                if image_url:
                    if "twitch:" in image_url and not profile_icon and not twitch_name:
                        twitch_name = image_url.replace("twitch:", "")
                        profile_icon = self.get_user_profile_image(twitch_name)

                    # self.log.debug(guild_id, "live_now.log_live_post", f"Found large image {image_url}")

            message = await self.discord_helper.sendEmbed(logging_channel,
                f"🔴 {user.display_name}", description,
                fields, thumbnail=profile_icon,
                author=user, color=0x6a0dad)

            # this should update the existing entry with the channel and message id
            self.db.track_live(guild_id, user.id, activity.platform, logging_channel.id, message.id, url=activity.url)

    async def add_remove_roles(self, user: discord.Member, check_list: list, add_list: list, remove_list: list) -> None:
        if user is None or user.guild is None:
            self.log.warn(0, "live_now.add_remove_roles", "User or guild is None")
            return

        guild_id = user.guild.id
        if user.roles:
            # check if the user has any of the watch roles
            user_is_in_watch_role =  any([ str(r.id) for r in user.roles if str(r.id) in check_list ])
            # for watch_role_id in [ str(r.id) for r in user.roles if str(r.id) in check_list ]:

            if user_is_in_watch_role:
                # remove the roles from the user
                if remove_list:
                    role_list = []
                    for role_id in remove_list:
                        role = user.guild.get_role(int(role_id))
                        if role and role in user.roles:
                            role_list.append(role)
                            self.log.info(guild_id, "live_now.add_remove_roles", f"Removed role {role.name} from user {user.display_name}")
                        # else:
                        #     self.log.error(guild_id, "live_now.add_remove_roles", f"Role {role_id} not found")

                    if role_list and len(role_list) > 0:
                        try:
                            await user.remove_roles(*role_list)
                        except Exception as e:
                            self.log.warn(guild_id, "live_now.add_remove_roles", str(e), traceback.format_exc())
                # else:
                #     self.log.info(guild_id, "live_now.add_remove_roles", f"No roles to remove from user {user.display_name}")

                # add the existing roles back to the user
                if add_list:
                    role_list = []
                    for role_id in add_list:
                        role = user.guild.get_role(int(role_id))
                        if role and role not in user.roles:
                            role_list.append(role)
                            self.log.info(guild_id, "live_now.add_remove_roles", f"Added role {role.name} to user {user.display_name}")
                        # else:
                        #     self.log.error(guild_id, "live_now.add_remove_roles", f"Role {role_id} not found")

                    if role_list and len(role_list) > 0:
                        try:
                            await user.add_roles(*role_list)
                        except Exception as e:
                            self.log.warn(guild_id, "live_now.add_remove_roles", str(e), traceback.format_exc())

                # else:
                #     self.log.info(guild_id, "live_now.add_remove_roles", f"No roles to add to user {user.display_name}")
            # else:
            #     self.log.debug(guild_id, "live_now.add_remove_roles", f"User {user.display_name} is not in any of the watch roles")

    async def clean_up_live(self, guild_id: int, user_id: int) -> None:
        if guild_id is None or user_id is None:
            return

        all_tracked_for_user = self.db.get_tracked_live_by_user(guildId=guild_id, userId=user_id)
        if all_tracked_for_user is None or all_tracked_for_user.count() == 0:
            return

        cog_settings = self.get_cog_settings(guild_id)

        logging_channel_id = cog_settings.get("logging_channel", None)
        logging_channel = self.bot.get_channel(int(logging_channel_id))
        for tracked in all_tracked_for_user:
            if logging_channel:
                message_id = tracked.get("message_id", None)
                if message_id:
                    try:
                        message = await logging_channel.fetch_message(int(message_id))
                        if message:
                            await message.delete()
                    except discord.errors.NotFound:
                        self.log.debug(guild_id, "live_now.on_member_update", f"Message {message_id} not found in channel {logging_channel}")

            # remove all tracked items for this live platform (should only be one)
            self.db.untrack_live(guild_id, tracked.get('user_id'), tracked.get('platform'))

    def find_platform_emoji(self, guild: discord.Guild, platform: str) -> typing.Union[discord.Emoji, None]:
        if guild is None:
            return None

        platform_emoji = discord.utils.find(lambda m: m.name.lower() == platform.lower(), guild.emojis)
        return platform_emoji

    def get_user_profile_image(self, twitch_user: str) -> typing.Union[str, None]:
        if twitch_user:
            result = requests.get(f"http://decapi.me/twitch/avatar/{twitch_user}")
            if result.status_code == 200:
                self.log.debug(0, "live_now.get_user_profile_image", f"Got profile image for {twitch_user}: {result.text}")
                return result.text
            else:
                self.log.debug(0, "live_now.get_user_profile_image", f"Failed to get profile image for {twitch_user}")
                self.log.info(0, "live_now.get_user_profile_image", f"{result.text}")
        return None

async def setup(bot):
    await bot.add_cog(LiveNow(bot))
