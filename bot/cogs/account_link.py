import inspect
import os
import traceback
import typing

import discord
from bot.lib import utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums.system_actions import SystemActions
from bot.lib.helpers import MessageHelper
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.twitch import TwitchDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from discord import app_commands
from discord.ext import commands


class AccountLinkCog(TacobotCog):
    group = app_commands.Group(name="link", description="Link your Twitch account to your Discord account")

    def __init__(
        self,
        bot: TacoBot,
        messaging: MessageHelper,
        twitch_db: TwitchDatabase,
        tracking_db: TrackingDatabase,
        settings: Settings,
    ):
        super().__init__(bot, "account_link", settings=settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.messaging = messaging
        self.twitch_db = twitch_db
        self.tracking_db = tracking_db

        self.invites = {}

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    @group.command(name="verify", description="Verify your Twitch account by entering the code you received.")
    @app_commands.guild_only()
    @app_commands.describe(code="The code you received to verify your Twitch account.")
    async def verify(self, interaction: discord.Interaction, code: str) -> None:
        _method = inspect.stack()[0][3]
        if interaction.guild:
            guild_id = interaction.guild.id
        else:
            return
        try:
            result = self.twitch_db.link_twitch_to_discord_from_code(interaction.user.id, code)
            self.tracking_db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.LINK_TWITCH_TO_DISCORD,
                data={"user_id": str(interaction.user.id), "code": code},
            )
            if result:
                msg = self.settings.get_string(guild_id, key="account_link_success_message", code=code)
                await self._send_from_context(interaction, msg)
            else:
                msg = self.settings.get_string(guild_id, key="account_link_unknown_code_message")
                await self._send_from_context(interaction, msg)
            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=interaction.channel.id if interaction.channel else None,
                userId=interaction.user.id,
                command="link",
                subcommand="verify",
                args=[{"type": "slash_command"}, {"code": code}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @group.command(
        name="request", description="Request a code to use to link your Twitch account to your Discord account"
    )
    @app_commands.guild_only()
    async def request(self, interaction: discord.Interaction) -> None:
        _method = inspect.stack()[0][3]
        if interaction.guild:
            guild_id = interaction.guild.id
        else:
            return
        try:
            code = utils.get_random_string(length=6)
            result = self.twitch_db.set_twitch_discord_link_code(interaction.user.id, code)
            if result:
                msg = self.settings.get_string(guild_id, key="account_link_notice_message", code=code)
                await self._send_from_context(interaction, msg)
            else:
                msg = self.settings.get_string(guild_id, key="account_link_save_error_message")
                await self._send_from_context(interaction, msg)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=interaction.channel.id if interaction.channel else None,
                userId=interaction.user.id,
                command="link",
                subcommand="request",
                args=[{"type": "slash_command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.command()
    @commands.guild_only()
    async def link(self, ctx, *, code: typing.Union[str, None] = None):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                guild_id = ctx.guild.id
                await ctx.message.delete()

            if code:
                await self._link_from_code(ctx, code, guild_id)
            else:
                await self._generate_code(ctx, guild_id)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="link",
                subcommand=None,
                args=[{"type": "command"}, {"code": code}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _send_from_context(self, ctx, message: str):
        try:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message(content=message, ephemeral=True)
            else:

                if not ctx.guild:
                    return
                if not ctx.author:
                    return
                if not ctx.channel:
                    return

                try:
                    await ctx.author.send(message)
                except discord.Forbidden:
                    await ctx.channel.send(f"{ctx.author.mention}, {message}", delete_after=10)

        except discord.Forbidden:
            pass

    async def _link_from_code(self, ctx, code: str, guild_id: int):
        _method = inspect.stack()[0][3]
        try:
            result = self.twitch_db.link_twitch_to_discord_from_code(ctx.author.id, code)
            self.tracking_db.track_system_action(
                guild_id=guild_id,
                action=SystemActions.LINK_TWITCH_TO_DISCORD,
                data={"user_id": str(ctx.author.id), "code": code},
            )
            if result:
                await self._send_from_context(
                    ctx, self.settings.get_string(guild_id, key="account_link_success_message", code=code)
                )
            else:
                await self._send_from_context(
                    ctx, self.settings.get_string(guild_id, key="account_link_unknown_code_message")
                )
        except ValueError as ve:
            await self._send_from_context(ctx, str(ve))
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    async def _generate_code(self, ctx, guild_id: int):
        _method = inspect.stack()[0][3]
        try:
            # generate code
            code = utils.get_random_string(length=6)
            # save code to db
            result = self.twitch_db.set_twitch_discord_link_code(ctx.author.id, code)
            notice_message = self.settings.get_string(guild_id, "account_link_notice_message", code=code)
            if result:
                await self._send_from_context(ctx, notice_message)
            else:
                await self._send_from_context(
                    ctx, self.settings.get_string(guild_id, "account_link_save_error_message")
                )

        except ValueError as ver:
            await self._send_from_context(ctx, str(ver))
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.messaging.notify_of_error(ctx)


async def setup(bot):
    settings = Settings()
    messaging = MessageHelper(bot, settings)
    twitch_db = TwitchDatabase()
    tracking_db = TrackingDatabase()
    await bot.add_cog(
        AccountLinkCog(bot=bot, messaging=messaging, twitch_db=twitch_db, tracking_db=tracking_db, settings=settings)
    )
