import datetime
import inspect
import os
import traceback
import typing

from discord.ext import commands

from .lib import settings, discordhelper, logger, loglevel, mongo, utils, tacotypes
from .lib.system_actions import SystemActions


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.db = mongo.MongoDatabase()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG

        self.invites = {}

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        _method = inspect.stack()[0][3]
        for guild in self.bot.guilds:
            guild_id = guild.id
            self.invites[guild_id] = await guild.invites()

            for invite in self.invites[guild_id]:
                invite_payload = self.get_payload_for_invite(invite)
                self.db.track_invite_code(guild_id, invite.code, invite_payload, None)

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "InviteTracker ready")

    @commands.Cog.listener()
    async def on_invite_create(self, invite) -> None:
        _method = inspect.stack()[0][3]
        guild_id = invite.guild.id
        self.invites[invite.guild.id] = await invite.guild.invites()

        for invite in self.invites[guild_id]:
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"adding invite: {invite.code}")
            invite_payload = self.get_payload_for_invite(invite)
            self.db.track_invite_code(guild_id, invite.code, invite_payload, None)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite) -> None:
        self.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        guild_id = member.guild.id
        _method = inspect.stack()[0][3]
        try:
            invites_before_join = self.invites[member.guild.id]
            invites_after_join = await member.guild.invites()
            for invite in invites_before_join:
                found_code = self.find_invite_by_code(invites_after_join, invite.code)
                if found_code is not None and invite.uses < found_code.uses:
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Invite used: " + invite.code)
                    self.invites[member.guild.id] = invites_after_join

                    inviter = invite.inviter
                    if inviter is not None and not inviter.bot:
                        timestamp = utils.to_timestamp(datetime.datetime.utcnow())

                        # track the invite. add the invite to the database if it doesn't exist. add the new user to the invite
                        invite_payload = self.get_payload_for_invite(invite)

                        invite_use_payload = {"user_id": str(member.id), "timestamp": timestamp}

                        self.db.track_invite_code(guild_id, invite.code, invite_payload, invite_use_payload)
                        await self.discord_helper.taco_give_user(
                            guild_id,
                            self.bot.user,
                            inviter,
                            self.settings.get_string(guild_id, "taco_reason_invite", user=member.name),
                            tacotypes.TacoTypes.USER_INVITE,
                        )
                        self.db.track_system_action(
                            guild_id=guild_id,
                            action=SystemActions.USER_INVITE,
                            data={
                                "inviter_id": str(inviter.id),
                                "inviter_name": inviter.name,
                                "invited_id": str(member.id),
                                "invited_name": member.name,
                                "invite_code": invite.code,
                            },
                        )
                    return
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    def get_payload_for_invite(self, invite) -> dict:
        return {
            "id": invite.id,
            "code": invite.code,
            "inviter_id": str(invite.inviter.id),
            "uses": invite.uses,
            "max_uses": invite.max_uses,
            "max_age": invite.max_age,
            "temporary": invite.temporary,
            "created_at": invite.created_at,
            "revoked": invite.revoked,
            "channel_id": str(invite.channel.id),
            "url": invite.url,
        }

    def find_invite_by_code(self, inviteList, code) -> typing.Optional[dict]:
        for invite in inviteList:
            if invite.code == code:
                return invite
        return None


async def setup(bot) -> None:
    await bot.add_cog(InviteTracker(bot))
