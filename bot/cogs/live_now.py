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
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
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
            # if the user is now streaming
            if before.activity is None and after.activity is not None:
                if after.activity.type == discord.ActivityType.streaming:
                    ## TODO: check if the user is on twitch or youtube
                    twitch_name = None

                    if after.activity.twitch_name:
                        # make sure the user's twitch info is tracked in the database
                        self.db.add_twitch_user(after.id, "", after.activity.twitch_name)
                        twitch_name = after.activity.twitch_name

                    cog_settings = self.get_cog_settings(guild_id)
                    if cog_settings.get("enabled", False):
                        # get the watch groups
                        watch_groups = cog_settings.get("watch", [])
                        logging_channel_id = cog_settings.get("logging_channel", None)
                        for wg in watch_groups:
                            watch_roles = wg.get("roles", [])
                            add_roles = wg.get("add_roles", [])
                            remove_roles = wg.get("remove_roles", [])
                            await self.add_remove_roles(user=after, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)

                        # get the logging channel
                        logging_channel = None
                        if logging_channel_id:
                            logging_channel = self.bot.get_channel(int(logging_channel_id))
                        if logging_channel:
                            # if we are logging this to a channel...

                            if not twitch_name:
                                # get twitch streamer name from database
                                twitch_info = self.db.get_user_twitch_info(after.id)
                                if twitch_info:
                                    twitch_name = twitch_info.get("twitch_name", None)

                            if twitch_name:
                                profile_icon = self.get_user_profile_image(twitch_name)
                                description = f"{after.activity.name}\n\n<https://twitch.tv/{twitch_name}>"
                                # embed = discord.Embed(title=f"🔴 {after.display_name}", description=description, color=0x6a0dad)
                                fields = [
                                    { "name": "Game", "value": after.activity.game, "inline": False },
                                ]
                                profile_icon = profile_icon if profile_icon else after.avatar_url
                                # embed.set_thumbnail(url=profile_icon)
                                # embed.set_author(name=f"{after.name}#{after.discriminator}", icon_url=after.avatar_url)
                                message = await self.discord_helper.sendEmbed(logging_channel,
                                    f"🔴 {after.display_name}", description,
                                    fields, thumbnail=profile_icon,
                                    author=after, color=0x6a0dad)

                                # message = await logging_channel.send(embed=embed, fields=fields)
                                self.db.track_live_post(guild_id, logging_channel.id, message.id, after.id)
                        # await self.handle_streaming(after, cog_settings)
            # should this check the before? or just check the after to make sure there are no stragglers left behind.
            elif before.activity and before.activity.type == discord.ActivityType.streaming and after.activity == None:
                cog_settings = self.get_cog_settings(guild_id)
                if cog_settings.get("enabled", False):
                    # get the watch groups
                        watch_groups = cog_settings.get("watch", [])
                        for wg in watch_groups:
                            watch_roles = wg.get("roles", [])
                            # do opposite here, to put back to original roles
                            add_roles = wg.get("remove_roles", [])
                            remove_roles = wg.get("add_roles", [])
                            await self.add_remove_roles(user=after, check_list=watch_roles, add_list=add_roles, remove_list=remove_roles)

                            track_list = self.db.get_tracked_live_post(guild_id, after.id)
                            logging_channel_id = cog_settings.get("logging_channel", None)
                            logging_channel = self.bot.get_channel(int(logging_channel_id))
                            for track in track_list:
                                if logging_channel:
                                    message_id = track.get("message_id", None)
                                    if message_id:
                                        message = await logging_channel.fetch_message(int(message_id))
                                        await message.delete()
                                        self.db.untrack_live_post(guild_id, message.id)
        except Exception as e:
            self.log.error(guild_id, "live_now.on_member_update", str(e), traceback.format_exc())

    @commands.command(aliases=["live", "streaming"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def live_now(self, ctx, user: discord.Member = None):
        try:
            await ctx.message.delete()
            guild_id = ctx.guild.id
            cog_settings = self.get_cog_settings(guild_id)
            logging_channel_id = cog_settings.get("logging_channel", None)
            logging_channel = None
            if logging_channel_id:
                logging_channel = self.bot.get_channel(int(logging_channel_id))
            if not logging_channel:
                self.log.debug(guild_id, "live_now.live_now", "No logging channel set")
                return
            twitch_info = self.db.get_user_twitch_info(user.id)
            twitch_name = None
            if twitch_info:
                twitch_name = twitch_info.get("twitch_name", None)

            if not twitch_name:
                self.log.debug(guild_id, "live_now.live_now", "No twitch name set")
                return

            profile_icon = self.get_user_profile_image(twitch_name)
            twitch_title = await self.discord_helper.ask_text(ctx, ctx.channel, "Stream Title", "What is the title of the stream?", timeout=60)
            if not twitch_title:
                self.log.debug(guild_id, "live_now.live_now", "No stream title given")
                return
            game_name = await self.discord_helper.ask_text(ctx, ctx.channel, "Game Title", "What is the title of the game?", timeout=60)
            if not game_name:
                self.log.debug(guild_id, "live_now.live_now", "No game title given")
                return
            description = f"{twitch_title}\n\n<https://twitch.tv/{twitch_name}>"
            # embed = discord.Embed(title=f"🔴 {user.display_name}", description=description, color=0x6a0dad)
            fields = [
                { "name": "Game", "value": game_name, "inline": False },
            ]
            profile_icon = profile_icon if profile_icon else user.avatar_url
            self.log.debug(guild_id, "live_now.live_now", f"profile_icon: {profile_icon}")

            message = await self.discord_helper.sendEmbed(logging_channel, f"🔴 {user.display_name}", description, fields, thumbnail=profile_icon, author=user, color=0x6a0dad)

            # embed.set_thumbnail(url=profile_icon)
            # embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar_url)
            # # embed.set_image(url=profile_icon)
            # for f in fields:
            #     embed.add_field(name=f["name"], value=f["value"], inline=f["inline"])
            # message = await logging_channel.send(embed=embed)
            # self.db.track_live_post(guild_id, logging_channel.id, message.id, user.id)
        except Exception as e:
            self.log.error(guild_id, "live_now.live_now", str(e), traceback.format_exc())
            return

    def get_cog_settings(self, guildId: int = 0):
        cog_settings = self.settings.get_settings(self.db, guildId, self.SETTINGS_SECTION)
        if not cog_settings:
            # raise exception if there are no leave_survey settings
            # self.log.error(guildId, "live_now.get_cog_settings", f"No live_now settings found for guild {guildId}")
            raise Exception(f"No live_now settings found for guild {guildId}")
        return cog_settings
    async def add_remove_roles(self, user: discord.Member, check_list: list, add_list: list, remove_list: list):
        if user is None or user.guild is None:
            return

        guild_id = user.guild.id
        # check if the user has any of the watch roles
        if user.roles:
            for role in [ r.id for r in user.roles if str(r.id) in check_list ]:
                # remove the roles from the user
                if add_list:
                    role_list = []
                    for role_id in add_list:
                        role = user.guild.get_role(int(role_id))
                        if role:
                            role_list.append(role)
                            self.log.info(guild_id, "live_now.add_remove_roles", f"Added role {role.name} to user {user.display_name}")
                    if role_list and len(role_list) > 0:
                        await user.remove_roles(*role_list)
                # add the existing roles back to the user
                if remove_list:
                    role_list = []
                    for role_id in remove_list:
                        role = user.guild.get_role(int(role_id))
                        if role:
                            role_list.append(role)
                            self.log.info(guild_id, "live_now.add_remove_roles", f"Removed role {role.name} from user {user.display_name}")
                    if role_list and len(role_list) > 0:
                        await user.add_roles(*role_list)

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
def setup(bot):
    bot.add_cog(LiveNow(bot))
