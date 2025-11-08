import datetime
import inspect
import os
import traceback
import typing

import discord
from bot.lib import utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums import tacotypes
from bot.lib.enums.system_actions import SystemActions
from bot.lib.helpers import EntityHelper, TacoHelper
from bot.lib.models.InvitePayload import InvitePayload, InvitePayloadFactory
from bot.lib.models.UserInviteSystemActionData import UserInviteSystemActionData
from bot.lib.mongodb.invites import InvitesDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from discord.ext import commands


class InviteTracker(TacobotCog):
    def __init__(
        self,
        bot: TacoBot,
        invites_db: InvitesDatabase,
        tracking_db: TrackingDatabase,
        entity_helper: EntityHelper,
        taco_helper: TacoHelper,
        settings: Settings,
    ) -> None:
        super().__init__(bot, "tacobot", settings=settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.invites_db = invites_db
        self.tracking_db = tracking_db

        self.entity_helper = entity_helper
        self.taco_helper = taco_helper

        self.invites: typing.Dict[int, typing.List[discord.Invite]] = {}
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        _method = inspect.stack()[0][3]
        for guild in self.bot.guilds:
            guild_id = guild.id
            self.invites[guild_id] = await guild.invites()

            for invite in self.invites[guild_id]:
                invite_payload = self.get_payload_for_invite(invite)
                self.invites_db.track_invite_code(guild_id, invite.code, invite_payload, None)

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "InviteTracker ready")

    @commands.Cog.listener()
    async def on_invite_create(self, invite) -> None:
        _method = inspect.stack()[0][3]
        guild_id = invite.guild.id
        self.invites[invite.guild.id] = await invite.guild.invites()

        for invite in self.invites[guild_id]:
            self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"adding invite: {invite.code}")
            invite_payload = self.get_payload_for_invite(invite)
            self.invites_db.track_invite_code(guild_id, invite.code, invite_payload, None)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite) -> None:
        self.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        guild_id = member.guild.id
        _method = inspect.stack()[0][3]
        try:
            invites_before_join: typing.List[discord.Invite] = self.invites[member.guild.id]
            invites_after_join: typing.List[discord.Invite] = await member.guild.invites()
            for invite in invites_before_join:
                found_code = self.find_invite_by_code(invites_after_join, invite.code)
                if found_code is not None and invite.uses < found_code.uses:
                    self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Invite used: " + invite.code)
                    self.invites[member.guild.id] = invites_after_join

                    inviter = invite.inviter
                    if inviter is not None and not inviter.bot:
                        timestamp = utils.to_timestamp(datetime.datetime.now(tz=datetime.timezone.utc))

                        # track the invite. add the invite to the database if it doesn't exist. add the new user to the invite
                        invite_payload = self.get_payload_for_invite(invite)

                        invite_use_payload = {"user_id": str(member.id), "timestamp": timestamp}

                        self.invites_db.track_invite_code(guild_id, invite.code, invite_payload, invite_use_payload)
                        await self.taco_helper.give_tacos(
                            guild_id,
                            self.bot.user,
                            inviter,
                            self.settings.get_string(guild_id, "taco_reason_invite", user=member.name),
                            tacotypes.TacoTypes.USER_INVITE,
                        )
                        self.tracking_db.track_system_action(
                            guild_id=guild_id,
                            action=SystemActions.USER_INVITE,
                            data=UserInviteSystemActionData(
                                {
                                    "inviter_id": str(inviter.id),
                                    "inviter_name": inviter.name,
                                    "invited_id": str(member.id),
                                    "invited_name": member.name,
                                    "invite_code": invite.code,
                                }
                            ).to_dict(),
                        )
                    return
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    def get_payload_for_invite(self, invite) -> InvitePayload:
        factory = InvitePayloadFactory()
        return factory.create_from_invite(invite)

    def find_invite_by_code(self, inviteList: typing.List[discord.Invite], code: str) -> typing.Optional[InvitePayload]:
        factory = InvitePayloadFactory()
        for invite in inviteList:
            if invite.code == code:
                return factory.create_from_invite(invite)
        return None


async def setup(bot) -> None:
    invites_db = InvitesDatabase()
    tracking_db = TrackingDatabase()
    entity_helper = EntityHelper(bot)
    taco_helper = TacoHelper(bot, entity_helper=entity_helper)
    settings = Settings()
    await bot.add_cog(
        InviteTracker(
            bot=bot,
            invites_db=invites_db,
            tracking_db=tracking_db,
            entity_helper=entity_helper,
            taco_helper=taco_helper,
            settings=settings,
        )
    )
