import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import math
import datetime

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
from .lib import tacotypes


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        if self.settings.db_provider == dbprovider.DatabaseProvider.MONGODB:
            self.db = mongo.MongoDatabase()
        else:
            self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.invites = {}

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, "invite_tracker.__init__", "Initialized")

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            guild_id = guild.id
            self.invites[guild_id] = await guild.invites()

            for invite in self.invites[guild_id]:
                self.log.debug(guild_id, "invite_tracker.on_ready", f"adding invite: {invite.code}")
                invite_payload = self.get_payload_for_invite(invite)
                self.db.track_invite_code(guild_id, invite.code, invite_payload, None)

        self.log.debug(0, "invite_tracker.on_ready", "InviteTracker ready")

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        guild_id = invite.guild.id
        self.invites[invite.guild.id] = await invite.guild.invites()

        for invite in self.invites[guild_id]:
            self.log.debug(guild_id, "invite_tracker.on_ready", f"adding invite: {invite.code}")
            invite_payload = self.get_payload_for_invite(invite)
            self.db.track_invite_code(guild_id, invite.code, invite_payload, None)


    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        self.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = member.guild.id
        _method = inspect.stack()[0][3]
        try:

            invites_before_join = self.invites[member.guild.id]
            invites_after_join = await member.guild.invites()
            for invite in invites_before_join:
                if invite.uses < self.find_invite_by_code(invites_after_join, invite.code).uses:
                    self.log.debug(0, "invite_tracker.on_member_join", "Invite used: " + invite.code)
                    self.invites[member.guild.id] = invites_after_join

                    inviter = invite.inviter
                    if inviter is not None and not inviter.bot:
                        timestamp = utils.to_timestamp(datetime.datetime.utcnow())

                        # track the invite. add the invite to the database if it doesn't exist. add the new user to the invite
                        invite_payload = self.get_payload_for_invite(invite)

                        invite_use_payload = {
                            "user_id": member.id,
                            "timestamp": timestamp
                        }

                        self.db.track_invite_code(guild_id, invite.code, invite_payload, invite_use_payload)
                        self.discord_helper.taco_give_user(guild_id, self.bot.user, inviter, f"inviting {member.name} to the server", tacotypes.TacoTypes.INVITE )
                        # # get taco settings
                        # taco_settings = self.settings.get_settings(self.db, guild_id, "tacos")
                        # if not taco_settings:
                        #     # raise exception if there are no tacos settings
                        #     self.log.error(guild_id, "tacos.on_message", f"No tacos settings found for guild {guild_id}")
                        #     return
                        # invite_count = taco_settings["invite_count"]

                        # taco_count = self.db.add_tacos(guild_id, inviter.id, invite_count)
                        # self.log.debug(guild_id, _method, f"🌮 added taco to user {inviter.name} successfully")
                        # await self.discord_helper.tacos_log(guild_id, inviter, self.bot.user, invite_count, taco_count, f"inviting {member.name} to the discord")

                    return
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())

    def get_payload_for_invite(self, invite):
        return {
            "id": invite.id,
            "code": invite.code,
            "inviter_id": invite.inviter.id,
            "uses": invite.uses,
            "max_uses": invite.max_uses,
            "max_age": invite.max_age,
            "temporary": invite.temporary,
            "created_at": invite.created_at,
            "revoked": invite.revoked,
            "channel_id": invite.channel.id,
            "url": invite.url
        }

    def find_invite_by_code(self, inviteList, code):
        for invite in inviteList:
            if invite.code == code:
                return invite
        return None
def setup(bot):
    bot.add_cog(InviteTracker(bot))
