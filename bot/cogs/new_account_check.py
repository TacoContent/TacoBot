import datetime
import inspect
import math
import os
import traceback

from bot.lib import discordhelper, utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums.system_actions import SystemActions
from bot.lib.messaging import Messaging
from bot.lib.mongodb.settings import SettingsDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.whitelist import WhitelistDatabase
from bot.tacobot import TacoBot
from discord.ext import commands


class NewAccountCheckCog(TacobotCog):
    def __init__(self, bot: TacoBot) -> None:
        super().__init__(bot, "account_age_check")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(self.bot)
        self.messaging = Messaging(self.bot)

        self.MINIMUM_ACCOUNT_AGE = 30  # days
        self.settings_db = SettingsDatabase()
        self.tracking_db = TrackingDatabase()
        self.whitelist_db = WhitelistDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.group(name="new-account", aliases=["new-account-check", "nac"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def new_account_check(self, ctx, *args) -> None:
        pass

    @new_account_check.command(name="set-minimum-age", aliases=["set-min-age", "set-min", "sma"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_minimum_account_age(self, ctx, minimum_age: int) -> None:
        """Set the minimum account age in days"""
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            self.settings_db.set_setting(
                guildId=guild_id, name=self.SETTINGS_SECTION, key="minimum_account_age", value=minimum_age
            )
            self.tracking_db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.MINIMUM_ACCOUNT_AGE_SET,
                data={"minimum_account_age": str(minimum_age), "set_by": str(ctx.author.id)},
            )
            await self.messaging.send_embed(
                channel=ctx.channel,
                title="Minimum account age set",
                message=f"Minimum account age: {minimum_age} days\nSet by: {ctx.author.mention}",
                delete_after=15,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())

    @new_account_check.command(name="whitelist-add", aliases=["wl-add", "wla", "trust", "add"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def whitelist_add(self, ctx, user_id: int) -> None:
        """Add a user to the whitelist to allow them to join if their account is newer than the minimum account age"""
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            self.whitelist_db.add_user_to_join_whitelist(guild_id=guild_id, user_id=user_id, added_by=ctx.author.id)
            self.tracking_db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.JOIN_WHITELIST_ADD,
                data={"user_id": str(user_id), "added_by": str(ctx.author.id)},
            )
            await self.messaging.send_embed(
                channel=ctx.channel,
                title="User added to join whitelist",
                message=f"User ID: {user_id}\nAdded by: {ctx.author.mention}",
                delete_after=15,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())

    @new_account_check.command(
        name="whitelist-remove",
        aliases=["whitelist-delete", "wlr", "wl-remove", "wl-delete", "wld", "untrust", "remove"],
    )
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def whitelist_remove(self, ctx, user_id: int) -> None:
        """Remove a user from the join whitelist"""
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            await ctx.message.delete()

            self.whitelist_db.remove_user_from_join_whitelist(guild_id=guild_id, user_id=user_id)
            self.tracking_db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.JOIN_WHITELIST_REMOVE,
                data={"user_id": str(user_id), "removed_by": str(ctx.author.id)},
            )
            await self.messaging.send_embed(
                channel=ctx.channel,
                title="User removed from join whitelist",
                message=f"User ID: {user_id}\nRemoved by: {ctx.author.mention}",
                delete_after=15,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{str(e)}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        pass
        # self.MINIMUM_ACCOUNT_AGE = self.settings.get_setting(self.SETTINGS_SECTION, "minimum_account_age", 30)

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

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        guild_id = member.guild.id
        _method = inspect.stack()[0][3]
        try:
            # check if the member is in the white list
            whitelist = self.whitelist_db.get_user_join_whitelist(guild_id=guild_id)

            # if they are in the whitelist, let them in
            if member.id in [x["user_id"] for x in whitelist]:
                return

            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Member {utils.get_user_display_name(member)} joined {member.guild.name}",
            )
            # check if the member has an account that is newer than the threshold
            member_created = member.created_at.timestamp()
            now = datetime.datetime.now().timestamp()
            age = now - member_created
            age_days = math.floor(age / 86400)
            cog_settings = self.get_cog_settings(guildId=guild_id)
            minimum_account_age = cog_settings.get("minimum_account_age", self.MINIMUM_ACCOUNT_AGE)
            notify_channel_id = cog_settings.get("notify_channel_id", None)
            notify_channel = None
            if age_days < minimum_account_age:
                self.log.warn(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Member {utils.get_user_display_name(member)} (ID: {member.id}) account age ({age_days} days) is less than {minimum_account_age} days.",
                )
                message = f"⚠️New Account⚠️: {member.name} account age ({age_days} days) is less than required minimum of {minimum_account_age} days."
                self.tracking_db.track_system_action(
                    guild_id=guild_id,
                    action=SystemActions.NEW_ACCOUNT_KICK,
                    data={"user_id": str(member.id), "reason": message, "account_age": age_days},
                )
                if member.guild:
                    try:
                        # find messages by the user and delete them
                        system_channel = member.guild.system_channel
                        if system_channel:
                            for message in system_channel.history(limit=100):
                                if message.author.id == member.id:
                                    await message.delete()
                    except Exception as e:
                        self.log.error(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc()
                        )
                else:
                    self.log.warn(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Member {utils.get_user_display_name(member)} (ID: {member.id}) has no guild.",
                    )
                # kick the member
                await member.kick(reason=message)
                if notify_channel_id:
                    notify_channel = await self.discord_helper.get_or_fetch_channel(notify_channel_id)
                    if notify_channel:
                        await notify_channel.send(message)

            return
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())


async def setup(bot):
    await bot.add_cog(NewAccountCheckCog(bot))
