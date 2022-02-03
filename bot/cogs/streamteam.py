import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing

from discord.ext.commands.cooldowns import BucketType
from discord_slash import ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select, create_select_option,  wait_for_component
from discord_slash.model import ButtonStyle
from discord.ext.commands import has_permissions, CheckFailure

from .lib import settings
from .lib import discordhelper
from .lib import logger
from .lib import loglevel
from .lib import utils
from .lib import settings
from .lib import mongo
from .lib import dbprovider

import inspect

class StreamTeam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(self.settings)
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "streamteam.__init__", f"DB Provider {self.settings.db_provider.name}")
        self.log.debug(0, "streamteam.__init__", f"Logger initialized with level {log_level.name}")

    def get_stream_team_roles(self, guild):
        return [discord.utils.get(guild.roles, name="STREAMER")]

    def get_stream_team_name(self, guild, team_role_id: int):
        return "Taco"

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        self.log.debug(0, "streamteam.on_guild_role_update", f"{before} -> {after}")
        if before is None:
            return
        if after is None:
            # role was deleted
            # remove from mongodb
            return
        stream_team_roles = self.get_stream_team_roles(before.guild)
        if stream_team_roles is None:
            self.log.debug(0, "streamteam.on_guild_role_update", f"stream_team_role is None")
            return
        if before in stream_team_roles:
            if before.id == after.id:

                pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        try:
            _method = inspect.stack()[1][3]
            guild_id = after.guild.id
            if after.roles == before.roles:
                self.log.debug(guild_id, "streamteam.on_member_update", f"{_method}", f"roles are the same")
                return
            # get streamteam role
            streamteam_roles = self.get_stream_team_roles(after.guild)
            for streamteam_role in streamteam_roles:
                STREAM_TEAM_NAME = self.get_stream_team_name(after.guild, streamteam_role.id)
                if not STREAM_TEAM_NAME:
                    self.log.debug(guild_id, "streamteam.on_member_update", f"Stream Team Name Not Found")
                    return

                # if streamteam role is not in after.roles or before.roles then return
                if streamteam_role not in after.roles and streamteam_role not in before.roles:
                    self.log.debug(guild_id, "streamteam.on_member_update", f"{_method}", f"{streamteam_role.name} not in roles")
                # if streamteam role is in after.roles and not in before.roles then add to db
                elif streamteam_role in after.roles and streamteam_role not in before.roles:
                    self.log.debug(guild_id, "streamteam.on_member_update", f"{_method}", f"{streamteam_role.name} added to roles")
                    self.db.add_stream_team_member(guild_id, STREAM_TEAM_NAME, after.id, f"{after.name}#{after.discriminator}", after.display_name.lower())
                    self.log.debug(guild_id, "streamteam.on_member_update", f"{after} added to STREAM TEAM: {STREAM_TEAM_NAME}")
                # if streamteam role is in before.roles and not in after.roles then remove from db
                elif streamteam_role in before.roles and streamteam_role not in after.roles:
                    self.db.remove_stream_team_member(guild_id, STREAM_TEAM_NAME, after.id)
                    self.log.debug(guild_id, "streamteam.on_member_update", f"{after} removed from STREAM TEAM")
        except discord.errors.NotFound as nf:
            self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
        except Exception as ex:
            self.log.error(guild_id, _method , str(ex), traceback.format_exc())
        finally:
            self.db.close()

    @commands.Cog.listener()
    async def on_ready(self):
        # for each guild, get the stream team members and add them to the database
        for guild in self.bot.guilds:
            streamteam_roles = self.get_stream_team_roles(guild)
            for role in streamteam_roles:
                STREAM_TEAM_NAME = self.get_stream_team_name(guild, role.id)
                if not STREAM_TEAM_NAME:
                    self.log.debug(guild.id, "streamteam.on_ready", f"Stream Team Name Not Found for role: {role.name}")
                    return
                for member in guild.members:
                    if role in member.roles:
                        self.db.add_stream_team_member(guild.id, STREAM_TEAM_NAME, member.id, f"{member.name}#{member.discriminator}", member.name.lower())
                        self.log.debug(guild.id, "streamteam.on_ready", f"{member} is in STREAM TEAM: {STREAM_TEAM_NAME}")

    @commands.Cog.listener()
    async def on_disconnect(self):
        pass

    @commands.Cog.listener()
    async def on_resumed(self):
        pass

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        self.log.error(0, "streamteam.on_error", f"{str(event)}", traceback.format_exc())

    @commands.group()
    async def team(self, ctx):
        pass

    @team.command()
    async def help(self, ctx):
        # todo: add help command
        await self.discord_helper.sendEmbed(ctx.channel, "Help", f"I don't know how to help with this yet.", delete_after=20)
        pass

    @team.command()
    async def list(self, ctx):
        try:
            # get stream team names and roles
            stream_team_roles = self.get_stream_team_roles(ctx.guild)
            # loop through roles and get the stream team names
            teams = []
            for role in stream_team_roles:
                team = self.get_stream_team_name(ctx.guild, role.id)
                # get members of the stream team
                stream_team_members = [m['discord_username'] for m in self.db.get_stream_team_members(ctx.guild.id, team)]
                # respond with a list of all the stream team members
                team_list = "\n".join(stream_team_members)
                await self.discord_helper.sendEmbed(ctx.channel, f"Stream Team: {team}", f"{team_list}", delete_after=30)
        except Exception as ex:
            self.log.error(ctx.guild.id, "streamteam.list", str(ex), traceback.format_exc())
        finally:
            await ctx.message.delete()

    @team.command(alias=["set-twitch-name"])
    async def set_twitch_name(self, ctx, memberOrName: typing.Union[str, discord.Member], twitch_name: str):
        try:
            _method = inspect.stack()[1][3]
            self.log.debug(ctx.guild.id, _method, f"{twitch_name}")
            # when memberOrName is a string then get the member
            if isinstance(memberOrName, str):
                member = await commands.MemberConverter().convert(ctx, memberOrName)
            else:
                member = memberOrName

            self.db.update_stream_team_member(ctx.guild.id, member.id, twitch_name)
            await ctx.send(f"Twitch Account set to {twitch_name}")
        except Exception as ex:
            self.log.error(ctx.guild_method, str(ex), traceback.format_exc())

def setup(bot):
    bot.add_cog(StreamTeam(bot))
