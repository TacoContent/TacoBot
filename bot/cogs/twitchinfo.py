# this cog will DM the user if they have not yet told the bot what their twitch name is if they interact with the bot.
import collections
import inspect
import os
import traceback
import typing

import discord
import requests
from bot.lib import discordhelper, utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums import tacotypes
from bot.lib.enums.system_actions import SystemActions
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.twitch import TwitchDatabase
from bot.tacobot import TacoBot
from discord.ext import commands


class TwitchInfoCog(TacobotCog):
    def __init__(self, bot: TacoBot) -> None:
        super().__init__(bot, "twitchinfo")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)

        self.twitch_db = TwitchDatabase()
        self.tracking_db = TrackingDatabase()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        pass

    @commands.group()
    async def twitch(self, ctx) -> None:
        pass

    @twitch.command(aliases=["invite-bot"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def invite_bot(
        self, ctx, *, user: typing.Optional[typing.Union[discord.Member, discord.User]] = None
    ) -> None:
        guild_id = 0
        channel = None
        if ctx.guild:
            guild_id = ctx.guild.id
            channel = ctx.channel
            await ctx.message.delete()

        if channel is None:
            return

        if user is None or user == "":
            # specify channel
            return
        twitch_info = self.twitch_db.get_user_twitch_info(user.id)
        twitch_name = None
        if twitch_info:
            twitch_name = twitch_info["twitch_name"]
        else:
            # user does not have twitch info must call twitch.set_user first
            twitch_name = await self.set_user(ctx, user)

        if twitch_name:
            # add the twitch name to the twitch_channels collection
            # send http request to nodered tacobot api to add the channel to the bot
            # TODO: store this url in the settings database
            url = f"https://nodered.bit13.local/tacobot/guild/{guild_id}/invite/{twitch_name}"
            result = requests.post(url, headers={"X-AUTH-TOKEN": str(self.bot.id)})
            if result.status_code == 200:
                await self.messaging.send_embed(
                    channel=channel,
                    title="Invite Bot",
                    message=f"Invited @OurTacoBot to {twitch_name}",
                    footer=self.settings.get_string(guild_id, "embed_delete_footer", seconds=30),
                    color=0xFF0000,
                    delete_after=30,
                )

                self.tracking_db.track_command_usage(
                    guildId=guild_id,
                    channelId=ctx.channel.id if ctx.channel.id else None,
                    userId=ctx.author.id,
                    command="twitch",
                    subcommand="invite-bot",
                    args=[{"type": "command"}, {"user_id": str(user.id)}],
                )

    @twitch.command()
    async def get(self, ctx, member: typing.Optional[typing.Union[discord.Member, discord.User]] = None) -> None:
        if member is None or member.bot or member.system:
            return

        check_member = member

        if check_member is None:
            member = ctx.author
            who = "you"
        else:
            who = utils.get_user_display_name(member)

        guild_id = 0
        # channel = ctx.author
        if ctx.guild:
            # channel = ctx.channel
            guild_id = ctx.guild.id
            await ctx.message.delete()

        ctx_dict = {"bot": self.bot, "author": ctx.author, "guild": None, "channel": None}
        alt_ctx = collections.namedtuple("Context", ctx_dict.keys())(*ctx_dict.values())

        twitch_name = None
        twitch_info = self.twitch_db.get_user_twitch_info(member.id)
        # if ctx.author is administrator, then we can get the twitch name from the database
        if twitch_info is None:
            if ctx.author.guild_permissions.administrator or check_member is None:
                twitch_name = await self.discord_helper.ask_text(
                    alt_ctx,
                    ctx.author,
                    "Twitch Name",
                    f"I do not have a twitch name set for {who}, please respond with the twitch name.",
                    60,
                )
                if twitch_name is not None:
                    self.twitch_db.set_user_twitch_info(ctx.author.id, twitch_name.lower().strip())
                    self.tracking_db.track_system_action(
                        guild_id=guild_id,
                        action=SystemActions.LINK_TWITCH_TO_DISCORD,
                        data={"user_id": str(ctx.author.id), "twitch_name": twitch_name.lower()},
                    )
        else:
            twitch_name = twitch_info["twitch_name"]
        if twitch_name is not None:
            await self.messaging.send_embed(
                channel=ctx.author,
                title="Twitch Name",
                message=f"The Twitch name for {who} has been set to `{twitch_name}`.\n\nhttps://twitch.tv/{twitch_name}\n\nIf your twitch name changes in the future, you can use `.taco twitch set` in a discord channel, or `.twitch set` in the DM with me to set it.",
                color=0x00FF00,
            )

        self.tracking_db.track_command_usage(
            guildId=guild_id,
            channelId=ctx.channel.id if ctx.channel.id else None,
            userId=ctx.author.id,
            command="twitch",
            subcommand="get",
            args=[{"type": "command"}, {"member_id": str(member.id if member else "")}],
        )

    @twitch.command(aliases=["set-user"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def set_user(
        self, ctx, user: discord.Member, twitch_name: typing.Optional[str] = None
    ) -> typing.Optional[str]:
        guild_id = 0
        _method = inspect.stack()[0][3]
        try:
            channel = ctx.author
            if ctx.guild:
                guild_id = ctx.guild.id
                channel = ctx.channel
                await ctx.message.delete()

            # if user is None:
            #     user = await self.discord_helper.ask_member(ctx, "User", "Please respond with the user you want to set the twitch name for.")

            if twitch_name is None:
                twitch_name = await self.discord_helper.ask_text(
                    ctx, ctx.author, "Twitch Name", "Please respond with the twitch name you want to set for the user."
                )

            if twitch_name is not None and user is not None:
                twitch_name = utils.get_last_section_in_url(twitch_name.lower().strip())
                self.twitch_db.set_user_twitch_info(user.id, twitch_name)
                self.tracking_db.track_system_action(
                    guild_id=guild_id,
                    action=SystemActions.LINK_TWITCH_TO_DISCORD,
                    data={"user_id": str(user.id), "twitch_name": twitch_name.lower()},
                )
                await self.messaging.send_embed(
                    channel=channel,
                    title="Success",
                    message=f"{ctx.author.mention}, The Twitch name has been set to {twitch_name} for {utils.get_user_display_name(user)}.",
                    color=0x00FF00,
                    delete_after=30,
                )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel.id else None,
                userId=ctx.author.id,
                command="twitch",
                subcommand="set-user",
                args=[{"type": "command"}, {"user_id": str(user.id if user else "")}, {"twitch_name": twitch_name}],
            )
            return twitch_name
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)
            return None

    @twitch.command()
    async def set(self, ctx, twitch_name: typing.Optional[str] = None) -> None:
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            resp_channel = ctx.author
            if ctx.guild:
                guild_id = ctx.guild.id
                resp_channel = ctx.channel
                await ctx.message.delete()

            if twitch_name is None:
                # try DM. if that doesnt work, use channel that they used...
                try:
                    resp_channel = ctx.author
                    twitch_name = await self.discord_helper.ask_text(
                        ctx,
                        ctx.author,
                        self.settings.get_string(guild_id, "twitch_ask_title"),
                        self.settings.get_string(guild_id, "twitch_ask_message", user=ctx.author.mention),
                        timeout=60,
                    )
                except discord.errors.Forbidden:
                    resp_channel = ctx.channel
                    twitch_name = await self.discord_helper.ask_text(
                        ctx,
                        ctx.channel,
                        self.settings.get_string(guild_id, "twitch_ask_title"),
                        self.settings.get_string(guild_id, "twitch_ask_message", user=ctx.author.mention),
                        timeout=60,
                    )

            self.log.debug(0, f"tqotd.{_method}", f"{ctx.author} requested to set twitch name {twitch_name}")
            if twitch_name is not None:
                twitch_name = utils.get_last_section_in_url(twitch_name.lower().strip())
                found_twitch = self.twitch_db.get_user_twitch_info(ctx.author.id)
                if found_twitch is None:
                    # only set if we haven't set it already.
                    taco_settings = self.get_tacos_settings(guild_id)
                    taco_amount = taco_settings.get("twitch_count", 25)
                    reason_msg = self.settings.get_string(guild_id, "taco_reason_twitch")
                    await self.discord_helper.taco_give_user(
                        guild_id,
                        self.bot.user,
                        ctx.author,
                        reason_msg,
                        tacotypes.TacoTypes.TWITCH_LINK,
                        taco_amount=taco_amount,
                    )

                self.twitch_db.set_user_twitch_info(ctx.author.id, twitch_name)
                self.tracking_db.track_system_action(
                    guild_id=guild_id,
                    action=SystemActions.LINK_TWITCH_TO_DISCORD,
                    data={"user_id": str(ctx.author.id), "twitch_name": twitch_name.lower()},
                )

                await self.messaging.send_embed(
                    channel=resp_channel,
                    title=self.settings.get_string(guild_id, "twitch_set_title"),
                    message=self.settings.get_string(
                        guild_id, "twitch_set_message", user=ctx.author.mention, twitch_name=twitch_name
                    ),
                    color=0x00FF00,
                    delete_after=30,
                )

                self.tracking_db.track_command_usage(
                    guildId=guild_id,
                    channelId=ctx.channel.id if ctx.channel.id else None,
                    userId=ctx.author.id,
                    command="twitch",
                    subcommand="set",
                    args=[
                        {"type": "command"},
                        {"user_id": str(ctx.author.id if ctx.author else "")},
                        {"twitch_name": twitch_name},
                    ],
                )
        except Exception as ex:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)


async def setup(bot):
    await bot.add_cog(TwitchInfoCog(bot))
