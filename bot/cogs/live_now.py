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
            self.log.debug(guild_id, "live_now.on_member_update", f"Checking if live_now is enabled for guild {guild_id}")
            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(guild_id, "live_now.on_member_update", f"No live_now settings found for guild {guild_id}")
                return
            if not cog_settings.get("enabled", False):
                self.log.debug(guild_id, "live_now.on_member_update", f"live_now is disabled for guild {guild_id}")
                return

            before_streaming_activities = [ a for a in before.activities if a.type == discord.ActivityType.streaming ]
            after_streaming_activities = [ a for a in after.activities if a.type == discord.ActivityType.streaming ]

            # if the streaming activity isn't found in the collection, but it is in the singular activity, then use that.
            if len(before_streaming_activities) == 0:
                if before.activity and before.activity.type == discord.ActivityType.streaming:
                    before_streaming_activities = [ before.activity ]
            if len(after_streaming_activities) == 0:
                if after.activity and after.activity.type == discord.ActivityType.streaming:
                    after_streaming_activities = [ after.activity ]

            # before_has_streaming_activity = len(before_streaming_activities) > 0
            # after_has_streaming_activity = len(after_streaming_activities) > 0
            # has_after_diff_streaming_activity =  len(after_streaming_activities) > len(before_streaming_activities)
            # has_before_diff_streaming_activity = len(before_streaming_activities) > len(after_streaming_activities)

            # check if the user is in any of the "add" roles, but has no streaming activity
            # remove them from those roles
            if len(before_streaming_activities) == 0 and len(after_streaming_activities) == 0:
                self.log.debug(guild_id, "live_now.on_member_update", f"no streaming activity found for {before.display_name}, checking if they are in any of the add roles")
                watch_groups = cog_settings.get("watch", [])
                for wg in watch_groups:
                    watch_roles = wg.get("roles", [])
                    add_roles = wg.get("remove_roles", [])
                    remove_roles = wg.get("add_roles", [])
                    self.log.info(guild_id, "live_now.on_member_update", f"updating roles for {before.display_name}")
                    await self.add_remove_roles(user=after, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)
                return

            self.log.debug(guild_id, "live_now.on_member_update", f"got streaming activities for {before.display_name}")

            # loop after activities and see if they are in the before activities
            # if they are not, then we have a new streaming activity
            for asa in after_streaming_activities:
                found = False
                for bsa in before_streaming_activities:
                    if asa.url == bsa.url and asa.platform == bsa.platform:
                        found = True
                        break
                self.log.debug(guild_id, "live_now.on_member_update", f"found ({found}) streaming activity for {after.display_name} on {asa.platform}")
                # check if the user activity was already tracked
                tracked = self.db.get_tracked_live(guild_id, after.id, asa.platform)
                is_tracked = tracked != None and tracked.count() > 0
                self.log.debug(guild_id, "live_now.on_member_update", f"Is {after.display_name} already tracked? {is_tracked}")

                if not is_tracked:
                    self.log.info(guild_id, "live_now.on_member_update", f"Found new streaming activity for {after.display_name}.")
                    tracked = self.db.get_tracked_live(guild_id, after.id, asa.platform)
                    if tracked.count() == 0:
                        self.log.info(guild_id, "live_now.on_member_update", f"{before.display_name} started streaming on {asa.platform}")

                        # get the tacos settings
                        taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
                        if not taco_settings:
                            self.log.error(guild_id, "live_now.on_member_update", f"No tacos settings found for guild {guild_id}")
                            return

                        # give the user tacos for going live
                        taco_amount = taco_settings.get("stream_count", 5)
                        reason_msg = self.settings.get_string(guild_id, "taco_reason_stream")
                        await self.discord_helper.taco_give_user(guild_id, self.bot.user, before, reason_msg, tacotypes.TacoTypes.STREAM, taco_amount=taco_amount )

                        self.db.track_live_activity(guild_id, after.id, True, asa.platform, asa.url)
                        twitch_name = None
                        if asa.platform.lower() == "twitch":
                            twitch_name = self.handle_twitch_live(after, after_streaming_activities)
                        elif asa.platform.lower() == "youtube":
                            self.handle_youtube_live(after, after_streaming_activities)
                        else:
                            self.log.warn(guild_id, "live_now.on_member_update", f"{before.display_name} started streaming, but platform {asa.platform} is not supported")

                        # get the watch groups
                        watch_groups = cog_settings.get("watch", [])
                        for wg in watch_groups:
                            watch_roles = wg.get("roles", [])
                            add_roles = wg.get("add_roles", [])
                            remove_roles = wg.get("remove_roles", [])
                            await self.add_remove_roles(user=after, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)

                        logging_channel_id = cog_settings.get("logging_channel", None)
                        if logging_channel_id:
                            await self.log_live_post(int(logging_channel_id), asa, after, twitch_name)
                        else:
                            self.db.track_live(guild_id, after.id, asa.platform, url=asa.url)
                    else:
                        self.log.debug(guild_id, "live_now.on_member_update", f"{before.display_name} started streaming on {asa.platform} but was already tracked")

            # loop all the before activities and see if they are in the after activities
            # if they are not, then we need to remove them from the database
            for bsa in before_streaming_activities:
                found = False
                for asa in after_streaming_activities:
                    if bsa.url == asa.url and bsa.platform == asa.platform:
                        found = True
                        break

                self.log.debug(guild_id, "live_now.on_member_update", f"found ({found}) streaming activity for {after.display_name} on {asa.platform}")
                tracked = self.db.get_tracked_live(guild_id, after.id, bsa.platform)
                is_tracked = tracked != None and tracked.count() > 0
                self.log.debug(guild_id, "live_now.on_member_update", f"Is {after.display_name} tracked? {is_tracked}")
                if found:
                    self.log.info(guild_id, "live_now.on_member_update", f"{before.display_name} stopped streaming on {bsa.platform}")
                    if is_tracked and tracked:
                        self.log.info(guild_id, "live_now.on_member_update", f"{before.display_name} stopped streaming")
                        self.db.track_live_activity(guild_id, before.id, False, bsa.platform, url=bsa.url)

                        logging_channel_id = cog_settings.get("logging_channel", None)
                        logging_channel = self.bot.get_channel(int(logging_channel_id))
                        for track in tracked:
                            if logging_channel:
                                message_id = track.get("message_id", None)
                                if message_id:
                                    try:
                                        message = await logging_channel.fetch_message(int(message_id))
                                        if message:
                                            try:
                                                await message.delete()
                                            except discord.errors.NotFound:
                                                self.log.warn(guild_id, "live_now.on_member_update", f"Message {message_id} not found in channel {logging_channel}")
                                    except discord.errors.NotFound:
                                        self.log.warn(guild_id, "live_now.on_member_update", f"Message {message_id} not found in channel {logging_channel}")
                                    self.db.untrack_live(guild_id, after.id, bsa.platform)
                    watch_groups = cog_settings.get("watch", [])
                    for wg in watch_groups:
                        watch_roles = wg.get("roles", [])
                        # do opposite here, to put back to original roles
                        add_roles = wg.get("remove_roles", [])
                        remove_roles = wg.get("add_roles", [])
                        await self.add_remove_roles(user=before, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)

        except Exception as e:
            self.log.error(guild_id, "live_now.on_member_update", str(e), traceback.format_exc())

    def handle_youtube_live(self, user: discord.Member, activities: typing.List[discord.Streaming]):
        guild_id = user.guild.id
        if len(activities) > 1:
            self.log.error(guild_id, "live_now.on_member_update", f"{user.display_name} has more than one streaming activity")

        self.log.info(guild_id, "live_now.handle_youtube_live", f"{user.display_name} started streaming on youtube")

    def handle_twitch_live(self, user: discord.Member, activities: typing.List[discord.Streaming]):
        guild_id = user.guild.id

        twitch_name = None
        twitch_info = self.db.get_user_twitch_info(user.id)
        if len(activities) > 1:
            self.log.error(guild_id, "live_now.on_member_update", f"{user.display_name} has more than one streaming activity")
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

    async def log_live_post(self, channel_id: int, activity: discord.Streaming, user: discord.Member, twitch_name: str):
        guild_id = user.guild.id
        # get the logging channel
        logging_channel = None
        if channel_id:
            logging_channel = self.bot.get_channel(channel_id)
        if logging_channel:
            # if we are logging this to a channel...

            if twitch_name:
                profile_icon = self.get_user_profile_image(twitch_name)
            else:
                profile_icon = None

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

            profile_icon = profile_icon if profile_icon else user.avatar_url

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

            self.db.track_live(guild_id, user.id, activity.platform, logging_channel.id, message.id, url=activity.url)

    async def add_remove_roles(self, user: discord.Member, check_list: list, add_list: list, remove_list: list):
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


    def find_platform_emoji(self, guild: discord.Guild, platform: str):
        if guild is None:
            return None

        platform_emoji = discord.utils.find(lambda m: m.name.lower() == platform.lower(), guild.emojis)
        return platform_emoji

    def get_user_profile_image(self, twitch_user: str):
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
