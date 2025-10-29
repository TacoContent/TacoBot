import inspect
import os
import traceback
import typing

import discord
from discord import app_commands
from discord.ext import commands

from bot.lib import discordhelper, utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums.system_actions import SystemActions
from bot.lib.messaging import Messaging
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.mongodb.twitch import TwitchDatabase
from bot.tacobot import TacoBot


class AccountLink(TacobotCog):
    group = app_commands.Group(name="link", description="Link your Twitch account to your Discord account")

    def __init__(self, bot: TacoBot):
        super().__init__(bot, "account_link")
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.discord_helper = discordhelper.DiscordHelper(bot)
        self.messaging = Messaging(bot)
        self.twitch_db = TwitchDatabase()
        self.tracking_db = TrackingDatabase()

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
                await interaction.response.send_message(
                    content=self.settings.get_string(guild_id, key="account_link_success_message", code=code),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    content=self.settings.get_string(guild_id, key="account_link_unknown_code_message"), ephemeral=True
                )
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
                await interaction.response.send_message(
                    content=self.settings.get_string(guild_id, key="account_link_notice_message", code=code),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    content=self.settings.get_string(guild_id, key="account_link_save_error_message"), ephemeral=True
                )
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
                try:
                    result = self.twitch_db.link_twitch_to_discord_from_code(ctx.author.id, code)
                    self.tracking_db.track_system_action(
                        guild_id=guild_id,
                        action=SystemActions.LINK_TWITCH_TO_DISCORD,
                        data={"user_id": str(ctx.author.id), "code": code},
                    )
                    if result:
                        # try DM, if that fails, use the channel that it originated in
                        try:
                            await ctx.author.send(
                                self.settings.get_string(guild_id, "account_link_success_message", code=code)
                            )
                        except discord.Forbidden:
                            await ctx.channel.send(
                                f'{ctx.author.mention}, {self.settings.get_string(guildId=guild_id, key="account_link_success_message", code=code)}',  # pylint: disable=line-too-long
                                delete_after=10,
                            )
                    else:
                        try:
                            await ctx.author.send(
                                self.settings.get_string(guild_id, key="account_link_unknown_code_message")
                            )
                        except discord.Forbidden:
                            await ctx.channel.send(
                                f'{ctx.author.mention}, {self.settings.get_string(guildId=guild_id, key="account_link_unknown_code_message")}',  # pylint: disable=line-too-long
                                delete_after=10,
                            )
                except ValueError as ve:
                    try:
                        await ctx.author.send(f"{ve}")
                    except discord.Forbidden:
                        await ctx.channel.send(f"{ctx.author.mention}, {ve}", delete_after=10)
                except Exception as e:
                    self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
                    await self.messaging.notify_of_error(ctx)
            else:
                try:
                    # generate code
                    code = utils.get_random_string(length=6)
                    # save code to db
                    result = self.twitch_db.set_twitch_discord_link_code(ctx.author.id, code)
                    notice_message = self.settings.get_string(guild_id, "account_link_notice_message", code=code)
                    if result:
                        try:
                            await ctx.author.send(notice_message)
                        except discord.Forbidden:
                            await ctx.channel.send(f"{ctx.author.mention}, {notice_message}", delete_after=10)
                    else:
                        try:
                            await ctx.author.send(self.settings.get_string(guild_id, "account_link_save_error_message"))
                        except discord.Forbidden:
                            await ctx.channel.send(
                                f'{ctx.author.mention}, {self.settings.get_string(guildId=guild_id, key="account_link_save_error_message")}',  # pylint: disable=line-too-long
                                delete_after=10,
                            )
                except ValueError as ver:
                    try:
                        await ctx.author.send(f"{ver}")
                    except discord.Forbidden:
                        await ctx.channel.send(f"{ctx.author.mention}, {ver}", delete_after=10)
                except Exception as e:
                    self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
                    await self.messaging.notify_of_error(ctx)

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


async def setup(bot):
    await bot.add_cog(AccountLink(bot))
