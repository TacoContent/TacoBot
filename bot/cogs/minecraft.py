# https://crafthead.net/armor/body/<uuid>
# https://playerdb.co/
# https://playerdb.co/api/player/minecraft/<name|uuid>

import inspect
import os
import traceback
import typing
import asyncio

import discord
import requests
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.helpers import ContextHelper, EntityHelper, MessageHelper, PromptHelper
from bot.lib.minecraft.whitelist import WhitelistManager
from bot.lib.mongodb.minecraft import MinecraftDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from bot.ui.MinecraftWhiteListConfirmView import MinecraftWhiteListConfirmView
from discord.ext import commands
from discord.ext.commands import Context
from discord import Interaction, app_commands


class MinecraftCog(TacobotCog):
    minecraft_ac = app_commands.Group(name="minecraft", description="Minecraft commands")
    # API endpoint constants for easier testing and configuration
    DEFAULT_MINECRAFT_API_BASE = "http://andeddu.bit13.local:10070"
    DEFAULT_PLAYER_DB_API = "https://playerdb.co/api/player/minecraft"
    DEFAULT_AVATAR_API = "https://crafthead.net/armor/body"

    def __init__(
        self,
        bot: TacoBot,
        whitelist_manager: WhitelistManager,
        # minecraft_db: MinecraftDatabase,
        tracking_db: TrackingDatabase,
        message_helper: MessageHelper,
        entity_helper: EntityHelper,
        context_helper: ContextHelper,
        prompt_helper: PromptHelper,
        settings: Settings,
        minecraft_api_base: str | None = None,
        player_db_api: str | None = None,
        avatar_api: str | None = None,
    ):
        super().__init__(bot, "minecraft", settings=settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]

        self.entity_helper = entity_helper
        self.context_helper = context_helper
        self.prompt_helper = prompt_helper

        self.message_helper = message_helper
        self.SELF_DESTRUCT_TIMEOUT = 30
        # self.minecraft_db = minecraft_db
        self.whitelist_manager = whitelist_manager
        self.tracking_db = tracking_db

        # API endpoints - configurable for testing
        self.minecraft_api_base = minecraft_api_base or self.DEFAULT_MINECRAFT_API_BASE
        self.player_db_api = player_db_api or self.DEFAULT_PLAYER_DB_API
        self.avatar_api = avatar_api or self.DEFAULT_AVATAR_API

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Initialized")

    # disable user from whitelist if they leave the discord
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        _method = inspect.stack()[0][3]
        try:
            guild_id = member.guild.id

            if not self.whitelist_manager.is_user_whitelisted(guild_id=guild_id, user_id=member.id):
                return
            mc_user = self.whitelist_manager.get_minecraft_user(guild_id=guild_id, user_id=member.id)
            if not mc_user:
                return

            self.log.debug(
                member.guild.id, f"{self._module}.{self._class}.{_method}", f"Member {member.name} has left the server"
            )
            self.whitelist_manager.set_user_whitelist_status(
                guild_id=guild_id, user_id=member.id, username=mc_user.username, uuid=mc_user.uuid, status=False
            )

        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())

    @commands.group(name="minecraft", invoke_without_command=True)
    @commands.guild_only()
    async def minecraft(self, ctx: Context):
        _method = inspect.stack()[0][3]
        if ctx.invoked_subcommand is not None:
            return
        guild_id = 0

        # Logging for visibility when invoked without a subcommand
        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", "Invoked top-level minecraft command")

        try:
            await self._minecraft_status(ctx)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="status",
                args=[{"type": "command"}],
            )
        except Exception as e:
            # Log once and notify user of the error (call notify without awaiting so tests that use AsyncMock register the call)
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            try:
                asyncio.create_task(self.message_helper.notify_of_error(ctx))
            except Exception:
                # Best-effort: swallow errors from notification to avoid cascading failures
                pass
    @minecraft_ac.command(name="status", description="Get the current Minecraft server status")
    async def minecraft_status_interaction(self, interaction: Interaction):
        _method = inspect.stack()[0][3]
        guild_id = interaction.guild.id if interaction.guild else 0
        try:
            await self._minecraft_status(interaction)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=interaction.channel_id if interaction.channel_id else None,
                userId=interaction.user.id,
                command="minecraft",
                subcommand="status",
                args=[{"type": "slash_command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            # notify via interaction
            await self._send_message(ctx=interaction, content=self.settings.get_string(guild_id, "error_occurred_message"), ephemeral=True)

    async def _minecraft_status(self, ctx: typing.Union[Interaction, Context, commands.Context]):
        _method = inspect.stack()[0][3]
        guild_id = 0
        user_id = 0
        deprecated_message = self._get_deprecated_message("status")
        content = None

        # Use duck-typing so tests using MagicMock contexts still behave correctly
        if hasattr(ctx, "response") and hasattr(ctx, "user"):
            # Interaction-like object
            if not ctx.response.is_done():  # type: ignore
                await ctx.response.defer(ephemeral=True)  # type: ignore
            user_id = ctx.user.id  # type: ignore
            guild_id = ctx.guild.id if ctx.guild else 0
        elif hasattr(ctx, "author"):
            # Context-like object
            if ctx.guild:
                await self.message_helper.safe_delete_context_message(ctx)  # type: ignore
            user_id = ctx.author.id  # type: ignore
            guild_id = ctx.guild.id if ctx.guild else 0
            content = deprecated_message
        else:
            context_type = type(ctx).__name__
            # Log invalid context and return
            self.log.error(
                0,
                f"{self._module}.{self._class}.{_method}",
                f"Invalid context type passed to _minecraft_status: {context_type}",
            )
            return

        if self.bot.user is None:
            return

        cog_settings = self.get_cog_settings(guild_id)
        if not cog_settings:
            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", "No minecraft settings found for guild"
            )
            return

        output_channel = None
        AUTO_DELETE_TIMEOUT = 30

        if isinstance(ctx, Context):
            output_channel, AUTO_DELETE_TIMEOUT = await self._determine_output_channel(ctx, cog_settings)

        if not cog_settings.get("enabled", False):
            return

        if not self.whitelist_manager.is_user_whitelisted(guild_id, user_id):
                # For text contexts use message_helper.send_embed to keep behavior consistent with tests
                if hasattr(ctx, "author"):
                    await self.message_helper.send_embed(
                        channel=output_channel,  # type: ignore
                        title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                        message=self.settings.get_string(guild_id, "minecraft_not_whitelisted_message"),
                        delete_after=30,
                    )
                else:
                    await self._send_message(
                        ctx=ctx,
                        target_channel=output_channel,
                        content=self.settings.get_string(guild_id, "minecraft_not_whitelisted_message"),
                        ephemeral=True,
                    )

        status = self.whitelist_manager.get_minecraft_status(guild_id=guild_id, minecraft_api_base=self.minecraft_api_base)
        fields = self._build_status_fields(guild_id, status, cog_settings)

        embed = await self._build_embed(
            ctx=ctx,
            title=self.settings.get_string(guild_id, "minecraft_status_server_status"),
            description=self.settings.get_string(
                guild_id, "minecraft_status_message", title=status['title'], help=cog_settings['help']
            ),
            color=0x00FF00 if status['online'] else 0xFF0000,
            fields=fields,
        )

        # For text-based contexts, use the MessageHelper to send embeds (consistent with existing tests)
        if hasattr(ctx, "author"):
            # Use MessageHelper for text contexts
            await self.message_helper.send_embed(
                channel=output_channel,  # type: ignore
                title=self.settings.get_string(guild_id, "minecraft_status_server_status"),
                message=self.settings.get_string(
                    guild_id, "minecraft_status_message", title=status['title'], help=cog_settings['help']
                ),
                fields=fields,
                content=content,
                delete_after=AUTO_DELETE_TIMEOUT,
            )
        else:
            await self._send_message(
                ctx=ctx,
                content=content,
                target_channel=output_channel,
                embed=embed,
                ephemeral=AUTO_DELETE_TIMEOUT > 0 if AUTO_DELETE_TIMEOUT else False,
            )

    @minecraft.command(name="status")
    @commands.guild_only()
    async def status_command(self, ctx: Context):
        # Decorated subcommand entry point for text-based `/minecraft status` invocation
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id if ctx.guild else 0
        try:
            if ctx.guild:
                await self.message_helper.safe_delete_context_message(ctx)

            await self._minecraft_status(ctx)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="status",
                args=[{"type": "command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            try:
                asyncio.create_task(self.message_helper.notify_of_error(ctx))
            except Exception:
                pass

    # Backwards-compatible coroutine method for tests and direct calls
    async def status(self, ctx: Context):
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Invoked legacy status wrapper")
        # call underlying command callback to keep behavior consistent
        return await self.status_command.callback(self, ctx)  # type: ignore
    @minecraft.command(name="start")
    @commands.guild_only()
    async def start_server(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                await self.message_helper.safe_delete_context_message(ctx)
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            # get the output channel from settings:
            output_channel, AUTO_DELETE_TIMEOUT = await self._determine_output_channel(ctx, cog_settings)

            if not self.whitelist_manager.is_user_whitelisted(guild_id=guild_id, user_id=ctx.author.id):
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(guild_id, "minecraft_control_no_start"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            status = self.whitelist_manager.get_minecraft_status(guild_id=guild_id, minecraft_api_base=self.minecraft_api_base)

            if status['online']:
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(guild_id, "minecraft_control_running"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} Started the Minecraft Server."
            )

            # send message to start the server
            resp = self._call_minecraft_start_api()
            if resp.status_code != 200:
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_start_failure_code", status_code=resp.status_code, action="start"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return
            data = resp.json()
            if data['status'] != "success":
                self.log.error(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Failed to start the server: {data['message']}",
                )
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_failure", error=data['message'], action="start"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            # notify the user that the server was started, and it will take a few minutes for it to be ready
            await self.message_helper.send_embed(
                channel=output_channel,
                title=self.settings.get_string(guild_id, "minecraft_control_title"),
                message=self.settings.get_string(guild_id, "minecraft_control_start_success"),
                delete_after=AUTO_DELETE_TIMEOUT,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="start",
                args=[{"type": "command"}],
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.message_helper.notify_of_error(ctx)

    @minecraft.command(name="stop")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def stop_server(self, ctx):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if ctx.guild:
                await self.message_helper.safe_delete_context_message(ctx)
                guild_id = ctx.guild.id

            cog_settings = self.get_cog_settings(guild_id)

            # get the output channel from settings:
            output_channel, AUTO_DELETE_TIMEOUT = await self._determine_output_channel(ctx, cog_settings)

            status = self.whitelist_manager.get_minecraft_status(guild_id=guild_id, minecraft_api_base=self.minecraft_api_base)

            if not status['online']:
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(guild_id, "minecraft_control_stopped"),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} Stopped the Minecraft Server."
            )

            # send message to stop the server
            resp = self._call_minecraft_stop_api()
            if resp.status_code != 200:
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_start_failure_code", status_code=resp.status_code, action="stop"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return
            data = resp.json()
            if data['status'] != "success":
                self.log.error(
                    guild_id, f"{self._module}.{self._class}.{_method}", f"Failed to stop the server: {data['message']}"
                )
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(guild_id, "minecraft_control_title"),
                    message=self.settings.get_string(
                        guild_id, "minecraft_control_failure", error=data['message'], action="stop"
                    ),
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
                return

            # notify the user that the server was started, and it will take a few minutes for it to be ready
            await self.message_helper.send_embed(
                channel=output_channel,
                title=self.settings.get_string(guild_id, "minecraft_control_title"),
                message=self.settings.get_string(guild_id, "minecraft_control_stop_success"),
                delete_after=AUTO_DELETE_TIMEOUT,
            )

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="stop",
                args=[{"type": "command"}],
            )

        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            await self.message_helper.notify_of_error(ctx)

    @minecraft.command(name="whitelist")
    @commands.guild_only()
    async def whitelist_command(self, ctx: Context):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id if ctx.guild else 0
        try:
            if ctx.guild:
                await self.message_helper.safe_delete_context_message(ctx)

            unsupported_message = self._get_unsupported_message("whitelist")
            output_channel, AUTO_DELETE_TIMEOUT = await self._determine_output_channel(ctx, self.get_cog_settings(ctx.guild.id if ctx.guild else 0))

            # Use MessageHelper for text contexts to be consistent with status handling
            if hasattr(ctx, "author"):
                await self.message_helper.send_embed(
                    channel=output_channel,
                    title=self.settings.get_string(ctx.guild.id if ctx.guild else 0, "minecraft_whitelist_title"),
                    message=unsupported_message,
                    delete_after=AUTO_DELETE_TIMEOUT,
                )
            else:
                await self._send_message(ctx, content=unsupported_message, target_channel=output_channel, ephemeral=True if AUTO_DELETE_TIMEOUT else False)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=ctx.channel.id if ctx.channel else None,
                userId=ctx.author.id,
                command="minecraft",
                subcommand="whitelist",
                args=[{"type": "command"}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc())
            try:
                asyncio.create_task(self.message_helper.notify_of_error(ctx))
            except Exception:
                pass

    # Backwards-compatible attribute for legacy code/tests that expect `cog.whitelist`
    whitelist = whitelist_command

    @minecraft_ac.command(name="whitelist", description="Join the Minecraft server whitelist")
    @app_commands.describe(username="Your Minecraft username")
    async def whitelist_interaction(self, interaction: Interaction, username: str):
        _METHOD = inspect.stack()[0][3]
        guild_id = 0
        try:
            if interaction.guild:
                guild_id = interaction.guild.id

            if self.whitelist_manager.is_user_whitelisted(guild_id=guild_id, user_id=interaction.user.id):
                await self._send_message(
                    ctx=interaction,
                    content=self.settings.get_string(guild_id, "minecraft_whitelist_already_whitelisted_message"),
                    ephemeral=True,
                )
                return

            # continue with the whitelist process
            await self._minecraft_whitelist(interaction, username)

            self.tracking_db.track_command_usage(
                guildId=guild_id,
                channelId=None,
                userId=interaction.user.id,
                command="minecraft",
                subcommand="whitelist",
                args=[{"type": "slash_command"}, {"username": username}],
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_METHOD}", str(e), traceback.format_exc())
            await self._send_message(
                ctx=interaction,
                content=self.settings.get_string(guild_id, "error_occurred_message"),
                ephemeral=True,
            )

    async def _minecraft_whitelist(self, ctx: Interaction, username: str):
        # primary flow for slash command whitelist remains unchanged

        _method = inspect.stack()[0][3]
        if not username:
            self.log.error(
                ctx.guild.id if ctx.guild else 0,
                f"{self._module}.{self._class}.{_method}",
                "No username provided for whitelist",
            )
            return

        # lookup username to get uuid
        result = self._call_player_db_api(username=username)
        if result.status_code != 200:
            # Need to notify of an error
            guild_id = ctx.guild.id if ctx.guild else 0
            self.log.warn(
                guild_id,
                f"{self._module}.{self._class}._minecraft_whitelist",
                f"Failed to find player {username}. (status_code: {result.status_code}) {result.text})",
            )
            await self._send_message(
                ctx=ctx,
                content=self.settings.get_string(
                    guild_id, "minecraft_whitelist_unable_to_verify", mc_username=username
                ),
                ephemeral=True,
            )
            return
        # get image for user from uuid
        data = result.json()

        # Process player data from API response
        player_info = self._process_player_data(data)
        if not player_info:
            guild_id = ctx.guild.id if ctx.guild else 0
            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", f"Failed to find player {username}"
            )
            await self._send_message(
                ctx=ctx,
                title=self.settings.get_string(guild_id, "minecraft_whitelist_title"),
                content=self.settings.get_string(
                    guild_id, "minecraft_whitelist_unable_to_verify", mc_username=username
                ),
                ephemeral=True,
            )
            return
        # confirm with user
        mc_uuid = player_info["uuid"]
        avatar_url = player_info["avatar_url"]

        # Build name history fields
        fields = []
        for n in player_info["name_history"]:
            fields.append({"name": "Name", "value": n["name"]})

        embed = await self._build_embed(
            ctx=ctx,
            title=self.settings.get_string(ctx.guild.id if ctx.guild else 0, "minecraft_whitelist_title"),
            description=self.settings.get_string(
                ctx.guild.id if ctx.guild else 0, "minecraft_whitelist_account_verify", mc_username=username
            ),
            image=avatar_url,
            fields=fields,
        )

        await self._send_message(
            ctx=ctx,
            embed=embed,
            view=MinecraftWhiteListConfirmView(
                cog=self,
                uuid=mc_uuid,
                username=username
            ),
            ephemeral=True,
        )
        # self.settings.get_string(
        #             guild_id, "minecraft_whitelist_account_verify", mc_username=mc_username
        #         ),
        #         fields=fields,
        #         image=avatar_url,
        #         result_callback=yes_no_callback,
        # add user to whitelist once confirmed
        pass

    async def _handle_whitelist_user_confirmation(self, ctx: Interaction, username: str, uuid: str):
        guild_id = ctx.guild.id if ctx.guild else 0
        self.whitelist_manager.set_user_whitelist_status(
            guild_id=guild_id, user_id=ctx.user.id, username=username, uuid=uuid, status=True
        )
        pass

    def _clean_username(self, username: str) -> str:
        return username.strip().lower()

    def _process_player_data(self, api_response_data: dict) -> dict | None:
        """Process the PlayerDB API response and extract player information.

        Args:
            api_response_data: JSON data from PlayerDB API response

        Returns:
            Dictionary containing player info (uuid, raw_id, username, name_history, avatar_url)
            or None if player data is invalid
        """
        if not api_response_data.get("success") or api_response_data.get("code") != "player.found":
            return None

        player_data = api_response_data.get("data", {}).get("player", {})
        if not player_data:
            return None

        mc_uuid = player_data.get("id")
        mc_raw_id = player_data.get("raw_id")
        mc_username = player_data.get("username")
        name_history = player_data.get("meta", {}).get("name_history", [])

        if not mc_uuid or not mc_raw_id:
            return None

        avatar_url = f"{self.avatar_api}/{mc_raw_id}"

        return {
            "uuid": mc_uuid,
            "raw_id": mc_raw_id,
            "username": mc_username,
            "name_history": name_history,
            "avatar_url": avatar_url,
        }

    def _call_minecraft_start_api(self) -> requests.Response:
        """Call the Minecraft server start API endpoint.

        Returns:
            Response object from the API call
        """
        start_url = f"{self.minecraft_api_base}/taco/minecraft/server/start"
        return requests.post(start_url)

    def _call_minecraft_stop_api(self) -> requests.Response:
        """Call the Minecraft server stop API endpoint.

        Returns:
            Response object from the API call
        """
        stop_url = f"{self.minecraft_api_base}/taco/minecraft/server/stop"
        return requests.post(stop_url)

    def _call_player_db_api(self, username: str) -> requests.Response:
        """Look up a Minecraft player by username using the PlayerDB API.

        Args:
            username: Minecraft username to look up (will be cleaned)

        Returns:
            Response object from the API call
        """
        clean_username = self._clean_username(username)
        player_url = f"{self.player_db_api}/{clean_username}"
        return requests.get(player_url)

    def _call_minecraft_status_api(self) -> requests.Response:
        """Get the current Minecraft server status.

        Returns:
            Response object from the API call
        """
        status_url = f"{self.minecraft_api_base}/tacobot/minecraft/status"
        return requests.get(status_url)

    async def _determine_output_channel(self, ctx: Context, cog_settings: dict) -> tuple:
        """Determine the appropriate output channel and timeout for a command.

        Args:
            ctx: Discord command context
            cog_settings: Cog settings dictionary

        Returns:
            Tuple of (output_channel, auto_delete_timeout)
        """
        AUTO_DELETE_TIMEOUT = self.SELF_DESTRUCT_TIMEOUT
        output_channel = await self.entity_helper.get_or_fetch_channel(int(cog_settings.get("output_channel", 0)))

        if not output_channel or output_channel.id != ctx.channel.id:
            output_channel = ctx.author
            AUTO_DELETE_TIMEOUT = None

        return output_channel, AUTO_DELETE_TIMEOUT

    def _build_status_fields(self, guild_id: int, status: dict, cog_settings: dict) -> list[dict]:
        """Build the status embed fields for the Minecraft server status display.

        Args:
            guild_id: Discord guild ID for localized strings
            status: Server status data from the API
            cog_settings: Cog configuration settings

        Returns:
            List of embed field dictionaries
        """
        fields = [
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_host"),
                "value": f"`{cog_settings['server']}`",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_players_slots"),
                "value": f"{status['players']['online']}/{status['players']['max']}",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_version"),
                "value": f"{status['version']}",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_forge_version"),
                "value": f"{cog_settings['forge_version']}",
                "inline": False,
            },
            {
                "name": self.settings.get_string(guild_id, "minecraft_status_mods"),
                "value": "------------------",
                "inline": False,
            },
        ]

        if not status['online']:
            fields.append(
                {
                    "name": self.settings.get_string(guild_id, "minecraft_status_server_status"),
                    "value": "Server is offline. Run `.taco minecraft start` to start the server.",
                    "inline": False,
                }
            )

        for m in cog_settings["mods"]:
            fields.append({"name": f"{m['name']}", "value": f"{m['version']}", "inline": True})

        return fields

    async def _build_embed(self, ctx: typing.Union[Interaction, Context], **kwargs) -> discord.Embed:
        fields = kwargs.pop('fields', [])
        image = kwargs.pop('image', None)
        footer = kwargs.pop('footer', None)
        thumbnail = kwargs.pop('thumbnail', None)

        embed = discord.Embed(**kwargs)
        for field in fields:
            embed.add_field(**field)

        if image:
            embed.set_image(url=image)

        if footer:
            embed.set_footer(text=footer)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return embed


    async def _send_message(
        self,
        ctx: typing.Union[Interaction, Context],
        **kwargs,
    ):
        _method = inspect.stack()[0][3]
        try:
            if isinstance(ctx, Interaction):
                if 'target_channel' in kwargs:
                    kwargs.pop('target_channel')  # remove target_channel if present
                use_followup = kwargs.pop('followup', False) or ctx.response.is_done()
                if use_followup:
                    await ctx.followup.send(**kwargs)
                else:
                    await ctx.response.send_message(**kwargs)
            elif isinstance(ctx, Context):
                # remove ephemeral from kwargs if present, as Context.send does not support it
                if 'followup' in kwargs:
                    kwargs.pop('followup')

                # get "target_channel" from kwargs if exists
                target_channel = ctx.channel if ctx.channel else ctx.author
                if 'target_channel' in kwargs:
                    target_channel = kwargs.pop('target_channel', ctx.channel)
                ephemeral = False
                if 'ephemeral' in kwargs:
                    ephemeral = kwargs.pop('ephemeral', False)

                kwargs.pop('delete_after', None)  # remove any existing delete_after to avoid conflicts

                if target_channel is None:
                    self.log.warn(0, f"{self._class}.{self._module}.{_method}", "No target channel found to send message")
                    return

                await target_channel.send(**kwargs, delete_after=self.SELF_DESTRUCT_TIMEOUT if ephemeral else None)  # type: ignore

                # await self.message_helper.send_embed(
                #     channel=target_channel,
                #     title="",
                #     message=content,
                #     fields=fields,
                #     delete_after=self.SELF_DESTRUCT_TIMEOUT if ephemeral else None,
                # )
        except Exception as e:
            self.log.error(0, "MinecraftCog._send_message", str(e), traceback.format_exc())

    def _get_deprecated_message(self, command: str) -> str:
        return (
            "⚠️ **DEPRECATION NOTICE** ⚠️\n\n"
            f"The `.taco minecraft {command}` command has been deprecated and will be removed in a future update. "
            f"Please use the new slash commands `/minecraft {command}` instead."
        )

    def _get_unsupported_message(self, command: str) -> str:
        return (
            "❌ **UNSUPPORTED COMMAND** ❌\n\n"
            f"The `.taco minecraft {command}` command is no longer supported and has been disabled. "
            f"Please use the new slash commands `/minecraft {command}` instead."
        )

async def setup(bot):
    settings = Settings()
    minecraft_db = MinecraftDatabase()
    whitelist_manager = WhitelistManager(minecraft_db=minecraft_db)
    tracking_db = TrackingDatabase()
    message_helper = MessageHelper(bot, settings)
    entity_helper = EntityHelper(bot)
    context_helper = ContextHelper()
    prompt_helper = PromptHelper(bot, settings, message_helper)
    await bot.add_cog(
        MinecraftCog(
            bot=bot,
            settings=settings,
            whitelist_manager=whitelist_manager,
            tracking_db=tracking_db,
            message_helper=message_helper,
            entity_helper=entity_helper,
            context_helper=context_helper,
            prompt_helper=prompt_helper,
        )
    )
